"""
Tests for order book implementation
"""

import unittest
import time

from src.core.order_book import (
    OrderBookSide,
    AdaptiveOrderBookSide,
    PriceLevel,
    AdaptivePriceLevel,
)
from src.core.order_types import Order, OrderSide, OrderType, MarketRegime


class TestPriceLevel(unittest.TestCase):
    """Test cases for PriceLevel"""

    def setUp(self):
        self.price_level = PriceLevel(100.0)

    def test_add_order(self):
        """Test adding orders to price level"""
        order = Order.create_limit_order(OrderSide.BUY, 100.0, 100)
        self.price_level.add_order(order)

        self.assertEqual(len(self.price_level.orders), 1)
        self.assertEqual(self.price_level.total_volume, 100)
        self.assertEqual(self.price_level.get_top_order(), order)

    def test_remove_order(self):
        """Test removing orders from price level"""
        order1 = Order.create_limit_order(OrderSide.BUY, 100.0, 100)
        order2 = Order.create_limit_order(OrderSide.BUY, 100.0, 200)

        self.price_level.add_order(order1)
        self.price_level.add_order(order2)

        self.assertEqual(self.price_level.total_volume, 300)

        # Remove first order
        success = self.price_level.remove_order(order1)
        self.assertTrue(success)
        self.assertEqual(len(self.price_level.orders), 1)
        self.assertEqual(self.price_level.total_volume, 200)
        self.assertEqual(self.price_level.get_top_order(), order2)

    def test_empty_checks(self):
        """Test empty checks"""
        self.assertTrue(self.price_level.is_empty())

        order = Order.create_limit_order(OrderSide.BUY, 100.0, 100)
        self.price_level.add_order(order)

        self.assertFalse(self.price_level.is_empty())


class TestOrderBookSide(unittest.TestCase):
    """Test cases for OrderBookSide"""

    def setUp(self):
        self.bid_side = OrderBookSide(OrderSide.BUY)
        self.ask_side = OrderBookSide(OrderSide.SELL)

    def test_add_orders_different_prices(self):
        """Test adding orders at different prices"""
        orders = [
            Order.create_limit_order(OrderSide.BUY, 100.0, 100),
            Order.create_limit_order(OrderSide.BUY, 101.0, 50),
            Order.create_limit_order(OrderSide.BUY, 99.0, 200),
        ]

        for order in orders:
            self.bid_side.add_order(order)

        self.assertEqual(len(self.bid_side.order_map), 3)
        self.assertEqual(len(self.bid_side.price_levels), 3)

        # Best bid should be highest price (101.0)
        best_bid = self.bid_side.get_best_price()
        self.assertEqual(best_bid, 101.0)

    def test_add_orders_same_price(self):
        """Test adding multiple orders at same price"""
        orders = [
            Order.create_limit_order(OrderSide.BUY, 100.0, 100),
            Order.create_limit_order(OrderSide.BUY, 100.0, 50),
            Order.create_limit_order(OrderSide.BUY, 100.0, 200),
        ]

        for order in orders:
            self.bid_side.add_order(order)

        # Should have one price level with multiple orders
        self.assertEqual(len(self.bid_side.price_levels), 1)
        price_level = self.bid_side.get_price_level(100.0)
        self.assertIsNotNone(price_level)
        self.assertEqual(len(price_level.orders), 3)
        self.assertEqual(price_level.total_volume, 350)

    def test_order_removal(self):
        """Test order removal functionality"""
        order = Order.create_limit_order(OrderSide.BUY, 100.0, 100)
        self.bid_side.add_order(order)

        self.assertEqual(len(self.bid_side.order_map), 1)

        # Remove the order
        success = self.bid_side.remove_order(order.order_id)
        self.assertTrue(success)
        self.assertEqual(len(self.bid_side.order_map), 0)
        self.assertEqual(len(self.bid_side.price_levels), 0)

    def test_best_price_cleanup(self):
        """Test that empty price levels are cleaned up"""
        order1 = Order.create_limit_order(OrderSide.BUY, 100.0, 100)
        order2 = Order.create_limit_order(OrderSide.BUY, 101.0, 50)

        self.bid_side.add_order(order1)
        self.bid_side.add_order(order2)

        self.assertEqual(self.bid_side.get_best_price(), 101.0)

        # Remove best order
        self.bid_side.remove_order(order2.order_id)

        # Best price should now be 100.0
        self.assertEqual(self.bid_side.get_best_price(), 100.0)

    def test_order_book_depth(self):
        """Test order book depth calculation"""
        orders = [
            Order.create_limit_order(OrderSide.BUY, 100.0, 100),
            Order.create_limit_order(OrderSide.BUY, 99.0, 50),
            Order.create_limit_order(OrderSide.BUY, 98.0, 200),
            Order.create_limit_order(OrderSide.BUY, 97.0, 75),
        ]

        for order in orders:
            self.bid_side.add_order(order)

        # Get top 3 levels
        depth = self.bid_side.get_depth(3)

        self.assertEqual(len(depth), 3)
        self.assertEqual(depth[0][0], 100.0)  # Best price first
        self.assertEqual(depth[0][1], 100)  # Total volume at that price

        # Check prices are in descending order
        prices = [level[0] for level in depth]
        self.assertEqual(prices, sorted(prices, reverse=True))


class TestAdaptiveOrderBookSide(unittest.TestCase):
    """Test cases for AdaptiveOrderBookSide"""

    def setUp(self):
        self.adaptive_bids = AdaptiveOrderBookSide(OrderSide.BUY)

    def test_regime_management(self):
        """Test regime management in adaptive order book"""
        initial_regime = self.adaptive_bids.regime

        # Change regime
        self.adaptive_bids.set_regime(MarketRegime.HIGH_VOLATILITY)

        self.assertNotEqual(self.adaptive_bids.regime, initial_regime)
        self.assertEqual(self.adaptive_bids.regime, MarketRegime.HIGH_VOLATILITY)

    def test_adaptive_price_level_creation(self):
        """Test that adaptive price levels are created"""
        order = Order.create_limit_order(OrderSide.BUY, 100.0, 100)
        self.adaptive_bids.add_order(order)

        price_level = self.adaptive_bids.get_price_level(100.0)
        self.assertIsNotNone(price_level)
        self.assertIsInstance(price_level, AdaptivePriceLevel)

    def test_regime_propagation(self):
        """Test that regime changes propagate to price levels"""
        # Add orders at different prices
        orders = [
            Order.create_limit_order(OrderSide.BUY, 100.0, 100),
            Order.create_limit_order(OrderSide.BUY, 101.0, 50),
        ]

        for order in orders:
            self.adaptive_bids.add_order(order)

        # Change regime
        self.adaptive_bids.set_regime(MarketRegime.HIGH_VOLATILITY)

        # Verify all price levels have the new regime
        for price_level in self.adaptive_bids.price_levels.values():
            self.assertEqual(price_level.regime, MarketRegime.HIGH_VOLATILITY)


class TestAdaptivePriceLevel(unittest.TestCase):
    """Test cases for AdaptivePriceLevel"""

    def setUp(self):
        self.adaptive_level = AdaptivePriceLevel(100.0, MarketRegime.NORMAL)

    def test_regime_transition(self):
        """Test regime transition in adaptive price level"""
        self.assertEqual(self.adaptive_level.regime, MarketRegime.NORMAL)

        # Change to high volatility regime
        self.adaptive_level.set_regime(MarketRegime.HIGH_VOLATILITY)

        self.assertEqual(self.adaptive_level.regime, MarketRegime.HIGH_VOLATILITY)

    def test_size_priority_ordering(self):
        """Test size-based ordering in high volatility regime"""
        # Add orders with different sizes
        orders = [
            Order.create_limit_order(OrderSide.BUY, 100.0, 50),  # Small
            Order.create_limit_order(OrderSide.BUY, 100.0, 200),  # Large
            Order.create_limit_order(OrderSide.BUY, 100.0, 100),  # Medium
        ]

        # Set different timestamps to test time priority
        for i, order in enumerate(orders):
            order.timestamp = time.time() + i * 0.001

        for order in orders:
            self.adaptive_level.add_order(order)

        # Set to size-priority regime
        self.adaptive_level.set_regime(MarketRegime.HIGH_VOLATILITY)

        # Top order should be largest (200)
        top_order = self.adaptive_level.get_top_order()
        self.assertEqual(top_order.quantity, 200)

        # Verify order: largest first, then by time for same size
        order_quantities = [order.quantity for order in self.adaptive_level.orders]
        self.assertEqual(order_quantities, [200, 100, 50])


if __name__ == "__main__":
    unittest.main()
