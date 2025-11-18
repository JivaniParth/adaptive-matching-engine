"""
Sharded Matching Engine

High-performance matching engine using sharded order books for parallel processing.
Supports both traditional NSE-style matching and adaptive matching with sharding.
"""

from typing import List, Optional, Dict
import time
from .sharded_order_book import ShardedOrderBookSide, ShardedAdaptiveOrderBookSide
from .order_types import Order, OrderSide, Trade, OrderType, MarketRegime
from .matching_engine import BaseMatchingEngine


class ShardedMatchingEngine(BaseMatchingEngine):
    """
    Matching engine using sharded order books for improved parallelism.

    Key features:
    - Parallel order cancellations across shards
    - Reduced lock contention for high-throughput scenarios
    - Compatible with existing matching logic
    - Configurable number of shards
    """

    def __init__(self, num_shards: int = 8):
        """
        Initialize sharded matching engine.

        Args:
            num_shards: Number of shards per side (default 8)
        """
        self.num_shards = num_shards

        # Use sharded order books instead of regular ones
        self.bids = ShardedOrderBookSide(OrderSide.BUY, num_shards=num_shards)
        self.asks = ShardedOrderBookSide(OrderSide.SELL, num_shards=num_shards)

        self.trade_history: List[Trade] = []
        self.order_history: List[Order] = []

    def process_order(self, order: Order) -> List[Trade]:
        """Process order with sharded matching."""
        return self.add_order(order)

    def add_order(self, order: Order) -> List[Trade]:
        """Add order and match using sharded order books."""
        self.order_history.append(order)
        trades = []

        if order.side == OrderSide.BUY:
            trades = self._match_buy_order(order)
        else:
            trades = self._match_sell_order(order)

        # Add remaining quantity to book
        if order.remaining_quantity > 0 and order.order_type == OrderType.LIMIT:
            self._add_to_order_book(order)

        self.trade_history.extend(trades)
        return trades

    def _match_buy_order(self, buy_order: Order) -> List[Trade]:
        """Match buy order against sharded ask side."""
        trades = []

        while (
            buy_order.remaining_quantity > 0
            and self.asks.get_best_price() is not None
            and (
                buy_order.order_type == OrderType.MARKET
                or self.asks.get_best_price() <= buy_order.price
            )
        ):
            best_ask_price = self.asks.get_best_price()
            if best_ask_price is None:
                break

            # Get all orders at best price across shards (sorted by time)
            sell_orders = self.asks.get_orders_at_best_price()
            if not sell_orders:
                # Price level became empty, invalidate cache and retry
                continue

            # Match against first order (FIFO)
            sell_order = sell_orders[0]

            trade_quantity = min(
                buy_order.remaining_quantity, sell_order.remaining_quantity
            )

            trade_price = sell_order.price

            trade = Trade.create_trade(buy_order, sell_order, trade_quantity)
            trades.append(trade)

            buy_order.filled_quantity += trade_quantity
            sell_order.filled_quantity += trade_quantity

            # Remove or update sell order
            if sell_order.remaining_quantity == 0:
                self.asks.remove_order(sell_order.order_id)

        return trades

    def _match_sell_order(self, sell_order: Order) -> List[Trade]:
        """Match sell order against sharded bid side."""
        trades = []

        while (
            sell_order.remaining_quantity > 0
            and self.bids.get_best_price() is not None
            and (
                sell_order.order_type == OrderType.MARKET
                or self.bids.get_best_price() >= sell_order.price
            )
        ):
            best_bid_price = self.bids.get_best_price()
            if best_bid_price is None:
                break

            # Get all orders at best price across shards (sorted by time)
            buy_orders = self.bids.get_orders_at_best_price()
            if not buy_orders:
                # Price level became empty, invalidate cache and retry
                continue

            # Match against first order (FIFO)
            buy_order = buy_orders[0]

            trade_quantity = min(
                sell_order.remaining_quantity, buy_order.remaining_quantity
            )

            trade_price = buy_order.price

            trade = Trade.create_trade(buy_order, sell_order, trade_quantity)
            trades.append(trade)

            sell_order.filled_quantity += trade_quantity
            buy_order.filled_quantity += trade_quantity

            # Remove or update buy order
            if buy_order.remaining_quantity == 0:
                self.bids.remove_order(buy_order.order_id)

        return trades

    def _add_to_order_book(self, order: Order):
        """Add order to appropriate sharded order book side."""
        if order.side == OrderSide.BUY:
            self.bids.add_order(order)
        else:
            self.asks.add_order(order)

    def cancel_order(self, order_id: str) -> bool:
        """Cancel order - automatically routed to correct shard."""
        # Try both sides (shard routing is automatic)
        if self.bids.remove_order(order_id):
            return True
        if self.asks.remove_order(order_id):
            return True
        return False

    def get_order_book_snapshot(self, levels: int = 10):
        """Get order book snapshot from sharded books."""
        from .order_types import OrderBookSnapshot

        bid_depth = self.bids.get_depth(levels)
        ask_depth = self.asks.get_depth(levels)

        spread = 0.0
        if bid_depth and ask_depth:
            spread = ask_depth[0][0] - bid_depth[0][0]

        return OrderBookSnapshot(
            timestamp=time.time(), bids=bid_depth, asks=ask_depth, spread=spread
        )

    def get_statistics(self) -> Dict:
        """Get engine statistics including sharding info."""
        return {
            "num_shards": self.num_shards,
            "total_orders": len(self.order_history),
            "total_trades": len(self.trade_history),
            "bid_stats": self.bids.get_statistics(),
            "ask_stats": self.asks.get_statistics(),
        }


class ShardedAdaptiveMatchingEngine(BaseMatchingEngine):
    """
    Adaptive matching engine with sharded order books.

    Combines the benefits of:
    - Sharding: Parallel cancellations and reduced contention
    - Adaptive matching: Regime-based strategies
    """

    def __init__(
        self,
        num_shards: int = 8,
        config: Optional[Dict] = None,
        benchmark_mode: bool = False,
    ):
        """
        Initialize sharded adaptive matching engine.

        Args:
            num_shards: Number of shards per side
            config: Adaptive engine configuration
            benchmark_mode: Disable adaptive features for benchmarking
        """
        from ..adaptive.regime_detector import OptimizedRegimeDetector

        self.num_shards = num_shards
        self.config = config or self._get_default_config()
        self.benchmark_mode = benchmark_mode

        # Use sharded adaptive order books
        self.bids = ShardedAdaptiveOrderBookSide(OrderSide.BUY, num_shards=num_shards)
        self.asks = ShardedAdaptiveOrderBookSide(OrderSide.SELL, num_shards=num_shards)

        # Regime detection
        self.regime_detector = OptimizedRegimeDetector(self.config)
        self.current_regime = MarketRegime.NORMAL
        self.regime_change_count = 0
        self.last_regime_change = time.time()

        # History
        self.trade_history: List[Trade] = []
        self.order_history: List[Order] = []
        self.metrics_history = []
        self.regime_history = []

        self.order_count = 0

    def _get_default_config(self) -> Dict:
        """Get default configuration."""
        return {
            "detection_interval": 100,
            "window_size": 100,
            "volatility_threshold": 0.05,
            "spread_threshold": 0.02,
            "imbalance_threshold": 0.5,
            "cancellation_threshold": 0.25,
            "enable_regime_detection": True,
            "enable_metrics_recording": True,
        }

    def process_order(self, order: Order) -> List[Trade]:
        """Process order with adaptive logic and sharding."""
        if self.benchmark_mode:
            return self.add_order(order)

        self.order_count += 1

        # Regime detection (same as non-sharded adaptive engine)
        interval = self.regime_detector.detection_interval

        if self.order_count % interval == 0:
            self._update_market_metrics(order)

            new_regime = self.regime_detector.detect_regime(
                self._get_best_bid(),
                self._get_best_ask(),
                self._get_buy_volume(),
                self._get_sell_volume(),
            )

            if new_regime != self.current_regime:
                self._transition_regime(new_regime)
        else:
            self.regime_detector.update_metrics(
                current_price=self._get_mid_price(),
                volume=order.quantity,
                order_side=order.side,
                spread=self._get_spread(),
            )

        # Process order
        trades = self.add_order(order)

        # Record metrics periodically
        record_interval = max(1, interval // 10)
        if self.order_count % record_interval == 0:
            self._record_metrics(order, trades)

        return trades

    def add_order(self, order: Order) -> List[Trade]:
        """Add and match order using sharded adaptive books."""
        self.order_history.append(order)
        trades = []

        if order.side == OrderSide.BUY:
            trades = self._match_buy_order(order)
        else:
            trades = self._match_sell_order(order)

        if order.remaining_quantity > 0 and order.order_type == OrderType.LIMIT:
            self._add_to_order_book(order)

        self.trade_history.extend(trades)
        return trades

    def _match_buy_order(self, buy_order: Order) -> List[Trade]:
        """Match buy order (same logic as sharded engine)."""
        trades = []

        while (
            buy_order.remaining_quantity > 0
            and self.asks.get_best_price() is not None
            and (
                buy_order.order_type == OrderType.MARKET
                or self.asks.get_best_price() <= buy_order.price
            )
        ):
            best_ask_price = self.asks.get_best_price()
            if best_ask_price is None:
                break

            sell_orders = self.asks.get_orders_at_best_price()
            if not sell_orders:
                continue

            sell_order = sell_orders[0]

            trade_quantity = min(
                buy_order.remaining_quantity, sell_order.remaining_quantity
            )

            trade = Trade.create_trade(buy_order, sell_order, trade_quantity)
            trades.append(trade)

            buy_order.filled_quantity += trade_quantity
            sell_order.filled_quantity += trade_quantity

            if sell_order.remaining_quantity == 0:
                self.asks.remove_order(sell_order.order_id)

        return trades

    def _match_sell_order(self, sell_order: Order) -> List[Trade]:
        """Match sell order (same logic as sharded engine)."""
        trades = []

        while (
            sell_order.remaining_quantity > 0
            and self.bids.get_best_price() is not None
            and (
                sell_order.order_type == OrderType.MARKET
                or self.bids.get_best_price() >= sell_order.price
            )
        ):
            best_bid_price = self.bids.get_best_price()
            if best_bid_price is None:
                break

            buy_orders = self.bids.get_orders_at_best_price()
            if not buy_orders:
                continue

            buy_order = buy_orders[0]

            trade_quantity = min(
                sell_order.remaining_quantity, buy_order.remaining_quantity
            )

            trade = Trade.create_trade(buy_order, sell_order, trade_quantity)
            trades.append(trade)

            sell_order.filled_quantity += trade_quantity
            buy_order.filled_quantity += trade_quantity

            if buy_order.remaining_quantity == 0:
                self.bids.remove_order(buy_order.order_id)

        return trades

    def _add_to_order_book(self, order: Order):
        """Add order to sharded book."""
        if order.side == OrderSide.BUY:
            self.bids.add_order(order)
        else:
            self.asks.add_order(order)

    def _transition_regime(self, new_regime: MarketRegime):
        """Transition to new regime across all shards."""
        self.bids.set_regime(new_regime)
        self.asks.set_regime(new_regime)

        old_regime = self.current_regime
        self.current_regime = new_regime
        self.regime_change_count += 1
        self.last_regime_change = time.time()

        self.regime_history.append(
            {
                "timestamp": time.time(),
                "from_regime": old_regime.value,
                "to_regime": new_regime.value,
            }
        )

    def _update_market_metrics(self, order: Order):
        """Update market metrics."""
        self.regime_detector.update_metrics(
            current_price=self._get_mid_price(),
            volume=order.quantity,
            order_side=order.side,
            spread=self._get_spread(),
        )

    def _get_best_bid(self) -> Optional[float]:
        return self.bids.get_best_price()

    def _get_best_ask(self) -> Optional[float]:
        return self.asks.get_best_price()

    def _get_mid_price(self) -> float:
        bid = self._get_best_bid()
        ask = self._get_best_ask()
        if bid is not None and ask is not None:
            return (bid + ask) / 2
        return 0.0

    def _get_spread(self) -> float:
        bid = self._get_best_bid()
        ask = self._get_best_ask()
        if bid is not None and ask is not None:
            return ask - bid
        return 0.0

    def _get_buy_volume(self) -> int:
        best_bid = self._get_best_bid()
        if best_bid is not None:
            depth = self.bids.get_depth(1)
            return depth[0][1] if depth else 0
        return 0

    def _get_sell_volume(self) -> int:
        best_ask = self._get_best_ask()
        if best_ask is not None:
            depth = self.asks.get_depth(1)
            return depth[0][1] if depth else 0
        return 0

    def _record_metrics(self, order: Order, trades: List[Trade]):
        """Record metrics."""
        self.metrics_history.append(
            {
                "timestamp": time.time(),
                "regime": self.current_regime.value,
                "order_type": order.order_type.value,
                "order_side": order.side.value,
                "quantity": order.quantity,
                "trades_generated": len(trades),
                "volume_executed": sum(t.quantity for t in trades),
                "spread": self._get_spread(),
            }
        )

    def cancel_order(self, order_id: str) -> bool:
        """Cancel order across shards."""
        if self.bids.remove_order(order_id):
            return True
        if self.asks.remove_order(order_id):
            return True
        return False

    def get_order_book_snapshot(self, levels: int = 10):
        """Get order book snapshot."""
        from .order_types import OrderBookSnapshot

        bid_depth = self.bids.get_depth(levels)
        ask_depth = self.asks.get_depth(levels)

        spread = 0.0
        if bid_depth and ask_depth:
            spread = ask_depth[0][0] - bid_depth[0][0]

        return OrderBookSnapshot(
            timestamp=time.time(), bids=bid_depth, asks=ask_depth, spread=spread
        )

    def update_config(self, new_config: Dict):
        """Update engine configuration."""
        self.config.update(new_config)
        self.regime_detector = OptimizedRegimeDetector(self.config)

    def get_config(self) -> Dict:
        """Get current configuration."""
        return self.config.copy()

    def set_regime_threshold(self, threshold_type: str, value: float):
        """Set a specific regime threshold."""
        threshold_key = f"{threshold_type}_threshold"
        if threshold_key in self.config:
            self.config[threshold_key] = value
            setattr(self.regime_detector, threshold_key, value)
        else:
            raise ValueError(f"Unknown threshold type: {threshold_type}")

    def get_regime_statistics(self) -> Dict:
        """Get regime statistics."""
        regime_counts = {}
        for entry in self.regime_history:
            regime = entry["to_regime"]
            regime_counts[regime] = regime_counts.get(regime, 0) + 1

        return {
            "total_changes": self.regime_change_count,
            "current_regime": self.current_regime.value,
            "regime_distribution": regime_counts,
            "regime_history": self.regime_history,
            "time_since_last_change": (
                time.time() - self.last_regime_change if self.last_regime_change else 0
            ),
        }

    def reset_statistics(self):
        """Reset statistics."""
        self.metrics_history.clear()
        self.regime_history.clear()
        self.regime_change_count = 0
        self.order_count = 0

    def get_statistics(self) -> Dict:
        """Get comprehensive statistics including sharding."""
        return {
            "num_shards": self.num_shards,
            "total_orders": len(self.order_history),
            "total_trades": len(self.trade_history),
            "regime_changes": self.regime_change_count,
            "current_regime": self.current_regime.value,
            "bid_stats": self.bids.get_statistics(),
            "ask_stats": self.asks.get_statistics(),
        }
