from collections import deque
from dataclasses import dataclass
from typing import Optional
import numpy as np
from ..core.order_types import MarketRegime, OrderSide


@dataclass
class MarketMetrics:
    volatility: float = 0.0
    spread: float = 0.0
    volume_imbalance: float = 0.0
    order_book_imbalance: float = 0.0
    cancellation_rate: float = 0.0
    mid_price: float = 0.0


class OptimizedRegimeDetector:
    """
    PERFORMANCE OPTIMIZED Regime Detector
    - Only detects every N orders (configurable interval)
    - Caches calculations aggressively
    - Uses incremental updates instead of full recalculation
    """

    def __init__(self, config: Optional[dict] = None):
        self.config = config or self._get_default_config()

        # Detection control
        self.detection_interval = self.config.get(
            "detection_interval", 100
        )  # Check every 100 orders
        self.order_count = 0
        self.last_regime = MarketRegime.NORMAL

        # Window size for calculations (default matches tests)
        self.window_size = self.config.get("window_size", 100)

        # Data windows - SMALLER for performance
        self.price_history: deque = deque(maxlen=self.window_size)
        self.volume_history: deque = deque(maxlen=self.window_size)
        self.spread_history: deque = deque(maxlen=self.window_size)

        # Cached metrics with dirty flag
        self._cached_metrics: Optional[MarketMetrics] = None
        self._metrics_dirty = True

        # Running sums for incremental calculation
        self._price_sum = 0.0
        self._price_sq_sum = 0.0
        self._spread_sum = 0.0

        # Counters
        self.cancellation_count = 0
        self.total_orders = 0
        self.buy_volume = 0
        self.sell_volume = 0

        # Thresholds - RELAXED for fewer regime changes
        self.volatility_threshold = self.config.get("volatility_threshold", 0.05)  # 5%
        self.spread_threshold = self.config.get("spread_threshold", 0.02)  # 2%
        self.imbalance_threshold = self.config.get("imbalance_threshold", 0.8)  # 80%
        self.cancellation_threshold = self.config.get(
            "cancellation_threshold", 0.4
        )  # 40%

    def _get_default_config(self) -> dict:
        return {
            "window_size": 100,
            "volatility_threshold": 0.05,  # Less sensitive
            "spread_threshold": 0.02,
            # More permissive thresholds to detect directional and HF regimes
            "imbalance_threshold": 0.5,
            "cancellation_threshold": 0.25,
            "detection_interval": 100,  # Check less frequently
        }

    def update_metrics(
        self, current_price: float, volume: int, order_side: OrderSide, spread: float
    ):
        """Lightweight metrics update with incremental calculation"""
        self.order_count += 1
        self.total_orders += 1

        # Track volume by side
        if order_side == OrderSide.BUY:
            self.buy_volume += volume
        else:
            self.sell_volume += volume

        # Only update histories if near detection interval
        if self.order_count % self.detection_interval < 10:  # Only last 10 orders
            # Incremental updates for mean calculation
            if len(self.price_history) == self.window_size:
                old_price = self.price_history[0]
                self._price_sum -= old_price
                self._price_sq_sum -= old_price * old_price
                old_spread = self.spread_history[0]
                self._spread_sum -= old_spread

            self.price_history.append(current_price)
            self.volume_history.append(volume)
            self.spread_history.append(spread)

            self._price_sum += current_price
            self._price_sq_sum += current_price * current_price
            self._spread_sum += spread
            self._metrics_dirty = True

    def record_cancellation(self):
        """Record order cancellation"""
        self.cancellation_count += 1
        # Treat cancellations as events that contribute to the total order count
        # (tests expect cancellations to be part of the denominator)
        self.total_orders += 1
        self._metrics_dirty = True

    def should_detect_regime(self) -> bool:
        """Check if we should run regime detection (performance gating)"""
        return self.order_count % self.detection_interval == 0

    def detect_regime(
        self, bid_price: float, ask_price: float, buy_volume: int, sell_volume: int
    ) -> MarketRegime:
        """
        FAST regime detection with early exits
        Only runs full detection every N orders
        """
        # FAST PATH: Skip detection if not at interval
        if not self.should_detect_regime():
            return self.last_regime

        # FAST PATH: Not enough data yet
        if len(self.price_history) < 10:
            return MarketRegime.NORMAL

        # Calculate metrics ONLY when needed
        metrics = self._calculate_fast_metrics(
            bid_price, ask_price, buy_volume, sell_volume
        )

        # Additional volatility proxy: large bid-ask range relative to mid-price
        mid_price = (
            (bid_price + ask_price) / 2
            if (bid_price is not None and ask_price is not None)
            else 0.0
        )
        mid_range_vol = abs(ask_price - bid_price) / mid_price if mid_price > 0 else 0.0

        # Prioritized regime detection
        if (
            metrics.volatility > self.volatility_threshold
            or mid_range_vol > self.volatility_threshold
        ):
            self.last_regime = MarketRegime.HIGH_VOLATILITY
        elif metrics.volume_imbalance > self.imbalance_threshold:
            self.last_regime = MarketRegime.DIRECTIONAL
        elif metrics.spread > self.spread_threshold:
            self.last_regime = MarketRegime.ILLIQUID
        elif metrics.cancellation_rate > self.cancellation_threshold:
            self.last_regime = MarketRegime.HIGH_FREQUENCY
        else:
            self.last_regime = MarketRegime.NORMAL

        return self.last_regime

    def _calculate_fast_metrics(
        self, bid_price: float, ask_price: float, buy_volume: int, sell_volume: int
    ) -> MarketMetrics:
        """
        OPTIMIZED metrics calculation using cached values
        """
        if not self._metrics_dirty and self._cached_metrics:
            return self._cached_metrics

        # Fast volatility using incremental calculation
        n = len(self.price_history)
        if n < 2:
            volatility = 0.0
        else:
            mean = self._price_sum / n
            variance = (self._price_sq_sum / n) - (mean * mean)
            volatility = np.sqrt(max(variance, 0)) / mean if mean > 0 else 0.0

        # Fast spread calculation
        avg_spread = self._spread_sum / n if n > 0 else 0.0

        # Volume imbalance
        total_vol = self.buy_volume + self.sell_volume
        volume_imbalance = (
            abs(self.buy_volume - self.sell_volume) / total_vol
            if total_vol > 0
            else 0.0
        )

        # Order book imbalance
        ob_total = buy_volume + sell_volume
        ob_imbalance = abs(buy_volume - sell_volume) / ob_total if ob_total > 0 else 0.0

        # Cancellation rate
        cancel_rate = (
            self.cancellation_count / self.total_orders
            if self.total_orders > 0
            else 0.0
        )

        mid_price = (
            (bid_price + ask_price) / 2
            if (bid_price is not None and ask_price is not None)
            else 0.0
        )

        self._cached_metrics = MarketMetrics(
            volatility=volatility,
            spread=avg_spread,
            volume_imbalance=volume_imbalance,
            order_book_imbalance=ob_imbalance,
            cancellation_rate=cancel_rate,
            mid_price=mid_price,
        )

        self._metrics_dirty = False
        return self._cached_metrics

    def get_metrics_summary(self) -> dict:
        """Get current metrics summary (cached when possible)"""
        if not self._metrics_dirty and self._cached_metrics:
            metrics = self._cached_metrics
        else:
            metrics = self._calculate_fast_metrics(0, 0, 0, 0)

        return {
            "volatility": metrics.volatility,
            "spread": metrics.spread,
            "volume_imbalance": metrics.volume_imbalance,
            "cancellation_rate": metrics.cancellation_rate,
        }

    # Convenience / compatibility methods expected by older API/tests
    def calculate_volatility(self) -> float:
        metrics = self._calculate_fast_metrics(0, 0, 0, 0)
        return metrics.volatility

    def calculate_volume_imbalance(self) -> float:
        total = self.buy_volume + self.sell_volume
        return abs(self.buy_volume - self.sell_volume) / total if total > 0 else 0.0

    def calculate_cancellation_rate(self) -> float:
        return (
            self.cancellation_count / self.total_orders
            if self.total_orders > 0
            else 0.0
        )


# Backwards-compatible alias for older tests / external APIs that expect
# a `RegimeDetector` class name. Keep both names pointing to the same
# implementation to avoid breaking imports.
RegimeDetector = OptimizedRegimeDetector
