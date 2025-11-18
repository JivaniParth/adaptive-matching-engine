"""
Unit tests for NSE Matching Engine
"""

import unittest
import time
from src.core.nse_matching_engine import NSEMatchingEngine
from src.core.order_types import (
    Order,
    OrderSide,
    OrderType,
    OrderValidity,
    TradingPhase,
)


class TestNSEMatchingEngine(unittest.TestCase):
    """Test cases for NSE matching engine."""

    def setUp(self):
        """Set up test engine."""
        self.engine = NSEMatchingEngine(
            symbol="TEST", tick_size=0.05, circuit_breaker_pct=10.0, price_band_pct=20.0
        )
        self.engine.set_reference_price(100.0)
        self.engine.set_trading_phase(TradingPhase.CONTINUOUS)

    def test_basic_matching(self):
        """Test basic buy-sell matching."""
        sell = Order("S1", OrderSide.SELL, 100.0, 50, time.time())
        self.engine.process_order(sell)

        buy = Order("B1", OrderSide.BUY, 100.0, 30, time.time())
        trades = self.engine.process_order(buy)

        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0].quantity, 30)
        self.assertEqual(trades[0].price, 100.0)

    def test_tick_size_validation(self):
        """Test tick size rounding."""
        order = Order("O1", OrderSide.BUY, 100.123, 10, time.time())
        self.engine.process_order(order)

        # Should be rounded to nearest 0.05
        self.assertAlmostEqual(order.price, 100.10, places=2)

    def test_price_band_rejection(self):
        """Test price band limits."""
        # Try to place order outside price bands
        # Upper band = 100 * 1.20 = 120
        # Lower band = 100 * 0.80 = 80

        order_high = Order("O1", OrderSide.BUY, 125.0, 10, time.time())
        trades = self.engine.process_order(order_high)

        # Should be rejected (no trades)
        self.assertEqual(len(trades), 0)

        order_low = Order("O2", OrderSide.SELL, 75.0, 10, time.time())
        trades = self.engine.process_order(order_low)

        # Should be rejected
        self.assertEqual(len(trades), 0)

    def test_circuit_breaker(self):
        """Test circuit breaker triggering."""
        # Set up orders that will trigger circuit breaker
        sell = Order("S1", OrderSide.SELL, 89.0, 100, time.time())
        self.engine.process_order(sell)

        buy = Order("B1", OrderSide.BUY, 89.0, 100, time.time())
        trades = self.engine.process_order(buy)

        # Trade should execute
        self.assertGreater(len(trades), 0)

        # Circuit breaker should be triggered (>10% move)
        self.assertTrue(self.engine.is_halted)
        self.assertEqual(self.engine.trading_phase, TradingPhase.HALTED)

    def test_call_auction(self):
        """Test call auction equilibrium price calculation."""
        self.engine.set_trading_phase(TradingPhase.PRE_OPEN)

        # Add buy orders
        buy1 = Order("B1", OrderSide.BUY, 102.0, 100, time.time())
        buy2 = Order("B2", OrderSide.BUY, 101.0, 150, time.time())
        buy3 = Order("B3", OrderSide.BUY, 100.0, 200, time.time())

        # Add sell orders
        sell1 = Order("S1", OrderSide.SELL, 100.0, 120, time.time())
        sell2 = Order("S2", OrderSide.SELL, 101.0, 180, time.time())
        sell3 = Order("S3", OrderSide.SELL, 102.0, 150, time.time())

        for order in [buy1, buy2, buy3, sell1, sell2, sell3]:
            self.engine.process_order(order)

        # Execute auction
        trades = self.engine.execute_call_auction()

        # Should have trades
        self.assertGreater(len(trades), 0)

        # All trades should be at same price (equilibrium)
        prices = set(t.price for t in trades)
        self.assertEqual(len(prices), 1)

        # Opening price should be set
        self.assertIsNotNone(self.engine.opening_price)

    def test_stop_loss_order(self):
        """Test stop-loss order triggering."""
        # Add resting sell order
        sell = Order("S1", OrderSide.SELL, 95.0, 100, time.time())
        self.engine.process_order(sell)

        # Add stop-loss sell order
        stop = Order(
            "SL1",
            OrderSide.SELL,
            95.0,
            50,
            time.time(),
            order_type=OrderType.STOP_LOSS,
            stop_price=98.0,
        )

        self.engine.process_order(stop)

        # Should be in pending stop orders
        self.assertEqual(len(self.engine.pending_stop_orders), 1)

        # Trigger the stop loss
        self.engine.last_traded_price = 97.0
        buy = Order("B1", OrderSide.BUY, 95.0, 10, time.time())
        self.engine.process_order(buy)

        # Stop order should be triggered and removed from pending
        self.assertEqual(len(self.engine.pending_stop_orders), 0)

    def test_fok_order_fill(self):
        """Test FOK order that can be filled."""
        # Add liquidity
        sell1 = Order("S1", OrderSide.SELL, 100.0, 50, time.time())
        sell2 = Order("S2", OrderSide.SELL, 101.0, 50, time.time())
        self.engine.process_order(sell1)
        self.engine.process_order(sell2)

        # FOK that can be filled
        fok = Order(
            "FOK1", OrderSide.BUY, 101.0, 80, time.time(), order_type=OrderType.FOK
        )
        trades = self.engine.process_order(fok)

        # Should execute
        self.assertGreater(len(trades), 0)
        self.assertEqual(sum(t.quantity for t in trades), 80)

    def test_fok_order_reject(self):
        """Test FOK order that cannot be filled."""
        # Add insufficient liquidity
        sell = Order("S1", OrderSide.SELL, 100.0, 50, time.time())
        self.engine.process_order(sell)

        # FOK that cannot be filled
        fok = Order(
            "FOK1", OrderSide.BUY, 100.0, 100, time.time(), order_type=OrderType.FOK
        )
        trades = self.engine.process_order(fok)

        # Should be rejected (no trades)
        self.assertEqual(len(trades), 0)

    def test_iceberg_order(self):
        """Test iceberg order visible quantity."""
        # Add iceberg buy
        iceberg = Order(
            "ICE1",
            OrderSide.BUY,
            100.0,
            500,
            time.time(),
            order_type=OrderType.ICEBERG,
            disclosed_quantity=100,
        )

        self.engine.process_order(iceberg)

        # Visible quantity should be 100
        self.assertEqual(iceberg.visible_quantity, 100)

        # Match against it
        sell = Order("S1", OrderSide.SELL, 100.0, 150, time.time())
        trades = self.engine.process_order(sell)

        # Should match visible quantity
        self.assertGreater(len(trades), 0)

        # Iceberg should still have remaining quantity
        self.assertGreater(iceberg.remaining_quantity, 0)

    def test_order_cancellation(self):
        """Test order cancellation."""
        order = Order("O1", OrderSide.BUY, 100.0, 50, time.time())
        self.engine.process_order(order)

        # Cancel order
        result = self.engine.cancel_order("O1")

        self.assertTrue(result)

        # Order should not be in book
        self.assertNotIn("O1", self.engine.bids.order_map)

    def test_order_book_snapshot(self):
        """Test order book snapshot."""
        # Add some orders
        for i in range(5):
            buy = Order(f"B{i}", OrderSide.BUY, 100.0 - i, 100, time.time())
            sell = Order(f"S{i}", OrderSide.SELL, 100.0 + i, 100, time.time())
            self.engine.process_order(buy)
            self.engine.process_order(sell)

        snapshot = self.engine.get_order_book_snapshot(levels=5)

        self.assertIsNotNone(snapshot)
        self.assertGreater(len(snapshot.bids), 0)
        self.assertGreater(len(snapshot.asks), 0)
        self.assertGreater(snapshot.spread, 0)

    def test_statistics(self):
        """Test engine statistics."""
        # Generate some activity
        for i in range(10):
            order = Order(f"O{i}", OrderSide.BUY, 100.0, 10, time.time())
            self.engine.process_order(order)

        stats = self.engine.get_statistics()

        self.assertEqual(stats["total_orders"], 10)
        self.assertIn("trading_phase", stats)
        self.assertIn("last_traded_price", stats)


class TestCallAuctionEquilibrium(unittest.TestCase):
    """Specific tests for call auction equilibrium price calculation."""

    def test_single_equilibrium(self):
        """Test auction with clear equilibrium."""
        engine = NSEMatchingEngine()
        engine.set_trading_phase(TradingPhase.PRE_OPEN)

        # Orders that overlap at 100
        buys = [
            Order("B1", OrderSide.BUY, 102, 100, time.time()),
            Order("B2", OrderSide.BUY, 101, 100, time.time()),
            Order("B3", OrderSide.BUY, 100, 100, time.time()),
        ]
        sells = [
            Order("S1", OrderSide.SELL, 100, 100, time.time()),
            Order("S2", OrderSide.SELL, 101, 100, time.time()),
            Order("S3", OrderSide.SELL, 102, 100, time.time()),
        ]

        for order in buys + sells:
            engine.process_order(order)

        trades = engine.execute_call_auction()

        # Should maximize volume
        self.assertGreater(len(trades), 0)
        equilibrium = trades[0].price
        # Equilibrium should be at one of the overlapping prices (100 or 101)
        self.assertIn(equilibrium, [100.0, 101.0])

    def test_no_overlap(self):
        """Test auction with no price overlap."""
        engine = NSEMatchingEngine()
        engine.set_trading_phase(TradingPhase.PRE_OPEN)

        # No overlap
        buy = Order("B1", OrderSide.BUY, 90, 100, time.time())
        sell = Order("S1", OrderSide.SELL, 110, 100, time.time())

        engine.process_order(buy)
        engine.process_order(sell)

        trades = engine.execute_call_auction()

        # No trades should occur
        self.assertEqual(len(trades), 0)


if __name__ == "__main__":
    unittest.main()
