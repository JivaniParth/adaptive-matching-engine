"""
Tests for regime detection functionality
"""

import unittest
import time
import numpy as np

from src.adaptive.regime_detector import RegimeDetector, MarketMetrics
from src.core.order_types import MarketRegime, OrderSide


class TestRegimeDetector(unittest.TestCase):
    """Test cases for RegimeDetector"""

    def setUp(self):
        self.detector = RegimeDetector()

    def test_initialization(self):
        """Test detector initialization"""
        self.assertEqual(self.detector.window_size, 100)
        self.assertIsNotNone(self.detector.config)
        self.assertEqual(len(self.detector.price_history), 0)

    def test_metrics_update(self):
        """Test metrics update functionality"""
        # Update with sample data
        self.detector.update_metrics(100.0, 1000, OrderSide.BUY, 0.01)
        self.detector.update_metrics(101.0, 1500, OrderSide.SELL, 0.012)

        self.assertEqual(len(self.detector.price_history), 2)
        self.assertEqual(len(self.detector.volume_history), 2)
        self.assertEqual(len(self.detector.spread_history), 2)

        # Check volume tracking
        self.assertEqual(self.detector.buy_volume, 1000)
        self.assertEqual(self.detector.sell_volume, 1500)

    def test_volatility_calculation(self):
        """Test volatility calculation"""
        # Create price series with known volatility
        prices = [100.0, 101.0, 99.0, 102.0, 98.0]  # Volatile series
        spreads = [0.01] * 5

        for i, price in enumerate(prices):
            self.detector.update_metrics(price, 100, OrderSide.BUY, spreads[i])

        volatility = self.detector.calculate_volatility()

        # Should have positive volatility
        self.assertGreater(volatility, 0)
        self.assertLess(volatility, 1.0)  # Should be reasonable

    def test_volume_imbalance_calculation(self):
        """Test volume imbalance calculation"""
        # Add balanced volume
        self.detector.buy_volume = 1000
        self.detector.sell_volume = 1000
        imbalance = self.detector.calculate_volume_imbalance()

        self.assertEqual(imbalance, 0.0)  # Perfect balance

        # Add imbalanced volume
        self.detector.buy_volume = 1500
        self.detector.sell_volume = 500
        imbalance = self.detector.calculate_volume_imbalance()

        self.assertEqual(imbalance, 0.5)  # (1500-500)/2000 = 0.5

    def test_cancellation_rate_calculation(self):
        """Test cancellation rate calculation"""
        # Add some orders and cancellations
        for _ in range(10):
            self.detector.update_metrics(100.0, 100, OrderSide.BUY, 0.01)

        for _ in range(5):
            self.detector.record_cancellation()

        cancellation_rate = self.detector.calculate_cancellation_rate()

        # 5 cancellations / 15 total orders = 0.333...
        self.assertAlmostEqual(cancellation_rate, 5 / 15, places=2)

    def test_normal_regime_detection(self):
        """Test detection of normal market regime"""
        # Create normal market conditions
        base_price = 100.0
        for i in range(200):
            # Small price movements, tight spread
            price = base_price + np.random.normal(0, 0.001)
            volume = np.random.randint(100, 500)
            spread = 0.005
            side = OrderSide.BUY if np.random.random() < 0.5 else OrderSide.SELL

            self.detector.update_metrics(price, volume, side, spread)

        regime = self.detector.detect_regime(99.995, 100.005, 1000, 1000)

        self.assertEqual(regime, MarketRegime.NORMAL)

    def test_high_volatility_detection(self):
        """Test detection of high volatility regime"""
        # Create volatile conditions
        base_price = 100.0
        for i in range(200):
            # Large price movements
            price = base_price + np.random.normal(0, 0.05)  # 5% volatility
            volume = np.random.randint(100, 500)
            spread = 0.01
            side = OrderSide.BUY if np.random.random() < 0.5 else OrderSide.SELL

            self.detector.update_metrics(price, volume, side, spread)

        regime = self.detector.detect_regime(95.0, 105.0, 1000, 1000)

        self.assertEqual(regime, MarketRegime.HIGH_VOLATILITY)

    def test_illiquid_regime_detection(self):
        """Test detection of illiquid regime"""
        # Create illiquid conditions (wide spreads)
        base_price = 100.0
        for i in range(200):
            price = base_price + np.random.normal(0, 0.001)
            volume = np.random.randint(10, 50)  # Low volume
            spread = 0.05  # Wide spread
            side = OrderSide.BUY if np.random.random() < 0.5 else OrderSide.SELL

            self.detector.update_metrics(price, volume, side, spread)

        regime = self.detector.detect_regime(97.5, 102.5, 100, 100)

        self.assertEqual(regime, MarketRegime.ILLIQUID)

    def test_directional_regime_detection(self):
        """Test detection of directional regime"""
        # Create imbalanced conditions
        base_price = 100.0
        for i in range(200):
            price = base_price + np.random.normal(0, 0.001)
            # Heavy buy volume imbalance
            volume = np.random.randint(100, 500)
            spread = 0.01
            # Mostly buy orders
            side = OrderSide.BUY if np.random.random() < 0.8 else OrderSide.SELL

            self.detector.update_metrics(price, volume, side, spread)

        regime = self.detector.detect_regime(99.995, 100.005, 8000, 2000)

        self.assertEqual(regime, MarketRegime.DIRECTIONAL)

    def test_high_frequency_regime_detection(self):
        """Test detection of high frequency regime"""
        # Create high cancellation conditions
        base_price = 100.0
        for i in range(100):
            price = base_price + np.random.normal(0, 0.001)
            volume = np.random.randint(100, 500)
            spread = 0.01
            side = OrderSide.BUY if np.random.random() < 0.5 else OrderSide.SELL

            self.detector.update_metrics(price, volume, side, spread)

            # High cancellation rate
            if i % 3 == 0:  # 33% cancellation rate
                self.detector.record_cancellation()

        regime = self.detector.detect_regime(99.995, 100.005, 1000, 1000)

        self.assertEqual(regime, MarketRegime.HIGH_FREQUENCY)

    def test_metrics_summary(self):
        """Test metrics summary generation"""
        # Add some data
        for i in range(50):
            price = 100.0 + np.random.normal(0, 0.01)
            volume = np.random.randint(100, 500)
            spread = 0.01
            side = OrderSide.BUY if np.random.random() < 0.5 else OrderSide.SELL

            self.detector.update_metrics(price, volume, side, spread)

        summary = self.detector.get_metrics_summary()

        # Check that summary contains expected keys
        expected_keys = [
            "volatility",
            "spread",
            "volume_imbalance",
            "cancellation_rate",
        ]
        for key in expected_keys:
            self.assertIn(key, summary)
            self.assertIsInstance(summary[key], (int, float))

    def test_configuration_validation(self):
        """Test configuration validation"""
        from src.utils.validators import regime_validator

        valid_config = {
            "window_size": 100,
            "volatility_threshold": 0.02,
            "spread_threshold": 0.01,
            "imbalance_threshold": 0.7,
            "cancellation_threshold": 0.3,
        }

        is_valid, errors = regime_validator.validate_config(valid_config)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

        # Test invalid config
        invalid_config = {
            "window_size": -1,  # Invalid
            "volatility_threshold": 1.5,  # Invalid
        }

        is_valid, errors = regime_validator.validate_config(invalid_config)
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)


if __name__ == "__main__":
    unittest.main()
