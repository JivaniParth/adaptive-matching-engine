from collections import deque
from dataclasses import dataclass
from typing import Deque, Optional
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


class RegimeDetector:
    """Detects market regimes based on real-time metrics"""

    def __init__(self, config: Optional[dict] = None):
        self.config = config or self._get_default_config()

        # Data windows
        self.window_size = self.config["window_size"]
        self.price_history: Deque[float] = deque(maxlen=self.window_size)
        self.volume_history: Deque[int] = deque(maxlen=self.window_size)
        self.spread_history: Deque[float] = deque(maxlen=self.window_size)

        # Counters for cancellation rate
        self.cancellation_count = 0
        self.total_orders = 0

        # Volume tracking
        self.buy_volume = 0
        self.sell_volume = 0

    def _get_default_config(self) -> dict:
        return {
            "window_size": 100,
            "volatility_threshold": 0.02,  # 2%
            "spread_threshold": 0.01,  # 1%
            "imbalance_threshold": 0.7,  # 70%
            "cancellation_threshold": 0.3,  # 30%
        }

    def update_metrics(
        self, current_price: float, volume: int, order_side: OrderSide, spread: float
    ):
        """Update market metrics with new data"""
        self.price_history.append(current_price)
        self.volume_history.append(volume)
        self.spread_history.append(spread)

        # Track volume by side
        if order_side == OrderSide.BUY:
            self.buy_volume += volume
        else:
            self.sell_volume += volume

        self.total_orders += 1

    def record_cancellation(self):
        """Record order cancellation"""
        self.cancellation_count += 1
        self.total_orders += 1

    def calculate_volatility(self) -> float:
        """Calculate price volatility over window"""
        if len(self.price_history) < 2:
            return 0.0

        prices = list(self.price_history)
        returns = []
        for i in range(1, len(prices)):
            if prices[i - 1] > 0:  # Avoid division by zero
                ret = (prices[i] - prices[i - 1]) / prices[i - 1]
                returns.append(abs(ret))

        return np.std(returns) if returns else 0.0

    def calculate_volume_imbalance(self) -> float:
        """Calculate buy/sell volume imbalance"""
        total_volume = self.buy_volume + self.sell_volume
        if total_volume == 0:
            return 0.0
        return abs(self.buy_volume - self.sell_volume) / total_volume

    def calculate_cancellation_rate(self) -> float:
        """Calculate order cancellation rate"""
        if self.total_orders == 0:
            return 0.0
        return self.cancellation_count / self.total_orders

    def calculate_spread(self) -> float:
        """Calculate average spread"""
        if not self.spread_history:
            return 0.0
        return np.mean(list(self.spread_history))

    def detect_regime(
        self, bid_price: float, ask_price: float, buy_volume: int, sell_volume: int
    ) -> MarketRegime:
        """Detect current market regime based on metrics"""
        metrics = self._calculate_all_metrics(
            bid_price, ask_price, buy_volume, sell_volume
        )

        # Regime detection logic
        if metrics.volatility > self.config["volatility_threshold"]:
            return MarketRegime.HIGH_VOLATILITY
        elif metrics.spread > self.config["spread_threshold"]:
            return MarketRegime.ILLIQUID
        elif metrics.volume_imbalance > self.config["imbalance_threshold"]:
            return MarketRegime.DIRECTIONAL
        elif metrics.cancellation_rate > self.config["cancellation_threshold"]:
            return MarketRegime.HIGH_FREQUENCY
        else:
            return MarketRegime.NORMAL

    def _calculate_all_metrics(
        self, bid_price: float, ask_price: float, buy_volume: int, sell_volume: int
    ) -> MarketMetrics:
        """Calculate all market metrics"""
        mid_price = (bid_price + ask_price) / 2 if bid_price and ask_price else 0.0

        return MarketMetrics(
            volatility=self.calculate_volatility(),
            spread=self.calculate_spread(),
            volume_imbalance=self.calculate_volume_imbalance(),
            order_book_imbalance=self._calculate_order_book_imbalance(
                buy_volume, sell_volume
            ),
            cancellation_rate=self.calculate_cancellation_rate(),
            mid_price=mid_price,
        )

    def _calculate_order_book_imbalance(
        self, buy_volume: int, sell_volume: int
    ) -> float:
        """Calculate order book imbalance at top levels"""
        total_volume = buy_volume + sell_volume
        if total_volume == 0:
            return 0.0
        return abs(buy_volume - sell_volume) / total_volume

    def get_metrics_summary(self) -> dict:
        """Get current metrics summary"""
        return {
            "volatility": self.calculate_volatility(),
            "spread": self.calculate_spread(),
            "volume_imbalance": self.calculate_volume_imbalance(),
            "cancellation_rate": self.calculate_cancellation_rate(),
        }
