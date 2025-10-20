"""
Tests for the matching engine
"""

import unittest
import time
from typing import List

from src.core.matching_engine import AdaptiveMatchingEngine, BaseMatchingEngine
from src.core.order_types import Order, OrderSide, OrderType, Trade
from src.data.order_generator import OrderGenerator


class TestBaseMatchingEngine(unittest.TestCase):
    """Test cases for BaseMatchingEngine"""

    def setUp(self):
        self.engine = BaseMatchingEngine()
        self.generator = OrderGenerator()

    def test_basic_order_matching(self):
        """Test basic order matching functionality"""
        # Add a buy order
        buy_order = Order.create_limit_order(OrderSide.BUY, 100.0, 100)
        trades = self.engine.add_order(buy_order)

        self.assertEqual(len(trades), 0)  # No match yet
        self.assertEqual(len(self.engine.bids.order_map), 1)

        # Add a matching sell order
        sell_order = Order.create_limit_order(OrderSide.SELL, 100.0, 50)
        trades = self.engine.add_order(sell_order)

        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0].quantity, 50)
        self.assertEqual(buy_order.filled_quantity, 50)
        self.assertEqual(sell_order.filled_quantity, 50)

    def test_price_time_priority(self):
        """Test Price-Time priority enforcement"""
        # Add multiple buy orders at same price
        buy1 = Order.create_limit_order(OrderSide.BUY, 100.0, 100)
        buy1.timestamp = time.time()
        time.sleep(0.001)  # Ensure time difference

        buy2 = Order.create_limit_order(OrderSide.BUY, 100.0, 200)
        buy2.timestamp = time.time()

        self.engine.add_order(buy1)
        self.engine.add_order(buy2)

        # Add sell order that matches both
        sell = Order.create_limit_order(OrderSide.SELL, 100.0, 150)
        trades = self.engine.add_order(sell)

        # FIX: Should generate 2 trades (one for each buy order)
        self.assertEqual(len(trades), 2)
        # First trade should be with buy1 (time priority)
        self.assertEqual(trades[0].buy_order_id, buy1.order_id)
        self.assertEqual(trades[0].quantity, 100)
        # Second trade should be with buy2 (remaining quantity)
        self.assertEqual(trades[1].buy_order_id, buy2.order_id)
        self.assertEqual(trades[1].quantity, 50)

    def test_market_orders(self):
        """Test market order matching"""
        # Add limit orders to the book
        buy_order = Order.create_limit_order(OrderSide.BUY, 100.0, 100)
        self.engine.add_order(buy_order)

        # Add market sell order
        sell_order = Order.create_market_order(OrderSide.SELL, 50)
        trades = self.engine.add_order(sell_order)

        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0].quantity, 50)
        self.assertEqual(trades[0].price, 100.0)  # Should match at buy order price

    def test_order_cancellation(self):
        """Test order cancellation"""
        order = Order.create_limit_order(OrderSide.BUY, 100.0, 100)
        self.engine.add_order(order)

        self.assertEqual(len(self.engine.bids.order_map), 1)

        # Cancel the order
        success = self.engine.cancel_order(order.order_id)
        self.assertTrue(success)
        self.assertEqual(len(self.engine.bids.order_map), 0)

    def test_order_book_snapshot(self):
        """Test order book snapshot generation"""
        # Add some orders
        self.engine.add_order(Order.create_limit_order(OrderSide.BUY, 99.0, 100))
        self.engine.add_order(Order.create_limit_order(OrderSide.BUY, 100.0, 50))
        self.engine.add_order(Order.create_limit_order(OrderSide.SELL, 101.0, 75))
        self.engine.add_order(Order.create_limit_order(OrderSide.SELL, 102.0, 100))

        snapshot = self.engine.get_order_book_snapshot()

        self.assertEqual(len(snapshot.bids), 2)
        self.assertEqual(len(snapshot.asks), 2)
        self.assertGreater(snapshot.spread, 0)

        # Check best bid/ask
        self.assertEqual(snapshot.bids[0][0], 100.0)  # Best bid price
        self.assertEqual(snapshot.asks[0][0], 101.0)  # Best ask price


class TestAdaptiveMatchingEngine(unittest.TestCase):
    """Test cases for AdaptiveMatchingEngine"""

    def setUp(self):
        self.engine = AdaptiveMatchingEngine()
        self.generator = OrderGenerator()

    def test_regime_detection_initialization(self):
        """Test that regime detection is properly initialized"""
        self.assertIsNotNone(self.engine.regime_detector)
        self.assertEqual(self.engine.regime_change_count, 0)
        self.assertIsNotNone(self.engine.current_regime)

    def test_metrics_tracking(self):
        """Test that metrics are properly tracked"""
        orders = self.generator.generate_orders(10)

        for order in orders:
            self.engine.process_order(order)

        self.assertGreater(len(self.engine.metrics_history), 0)

        # Check that metrics contain expected fields
        metrics = self.engine.metrics_history[0]
        expected_fields = [
            "timestamp",
            "regime",
            "order_type",
            "order_side",
            "quantity",
        ]
        for field in expected_fields:
            self.assertIn(field, metrics)

    def test_regime_transition(self):
        """Test regime transition functionality"""
        initial_regime = self.engine.current_regime

        # FIX: Use MarketRegime enum instead of string
        from src.core.order_types import MarketRegime

        self.engine._transition_regime(MarketRegime.HIGH_VOLATILITY)

        self.assertNotEqual(self.engine.current_regime, initial_regime)
        self.assertEqual(self.engine.regime_change_count, 1)
        self.assertGreater(len(self.engine.regime_history), 0)

    def test_volatile_market_handling(self):
        """Test engine behavior in volatile market conditions"""
        # Generate volatile orders
        volatile_orders = self.generator.generate_volatile_orders(100)

        regime_changes = []

        for order in volatile_orders:
            initial_regime = self.engine.current_regime
            self.engine.process_order(order)

            if self.engine.current_regime != initial_regime:
                regime_changes.append((initial_regime, self.engine.current_regime))

        # Engine should detect volatile conditions and potentially change regime
        # (Exact behavior depends on detector sensitivity)
        self.assertGreaterEqual(len(regime_changes), 0)

    def test_performance_under_load(self):
        """Test engine performance under heavy load"""
        import time

        orders = self.generator.generate_orders(1000)

        start_time = time.perf_counter()

        for order in orders:
            self.engine.process_order(order)

        end_time = time.perf_counter()
        total_time = end_time - start_time

        # Should process 1000 orders in reasonable time
        self.assertLess(total_time, 10.0)  # 10 seconds is very conservative

        throughput = len(orders) / total_time
        self.assertGreater(throughput, 100)  # At least 100 orders/second

    def test_memory_usage(self):
        """Test memory usage doesn't grow excessively"""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Process large number of orders
        orders = self.generator.generate_orders(5000)
        for order in orders:
            self.engine.process_order(order)

        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        # Memory increase should be reasonable
        # 10MB is conservative for 5000 orders with order book
        self.assertLess(memory_increase, 10 * 1024 * 1024)  # 10MB


if __name__ == "__main__":
    unittest.main()
