from typing import List, Optional, Dict, Tuple
import time
from .order_book import OrderBookSide, AdaptiveOrderBookSide, PriceLevel
from .order_types import Order, OrderSide, Trade, OrderType, MarketRegime
from ..adaptive.regime_detector import RegimeDetector


class BaseMatchingEngine:
    """Base matching engine with Price-Time priority"""

    def __init__(self):
        self.bids = OrderBookSide(OrderSide.BUY)
        self.asks = OrderBookSide(OrderSide.SELL)
        self.trade_history: List[Trade] = []
        self.order_history: List[Order] = []

    def process_order(self, order: Order) -> List[Trade]:
        """
        Process order - for BaseMatchingEngine, this is the same as add_order
        This method exists for compatibility with AdaptiveMatchingEngine interface
        """

        self.order_count += 1

        # FAST PATH - add this!
        if self.current_regime == MarketRegime.NORMAL and self.order_count % 100 != 0:
            return self.add_order(order)

    def add_order(self, order: Order) -> List[Trade]:
        """Add order and return list of generated trades"""
        self.order_history.append(order)
        trades = []

        if order.side == OrderSide.BUY:
            trades = self._match_buy_order(order)
        else:
            trades = self._match_sell_order(order)

        # If order still has quantity, add to order book
        if order.remaining_quantity > 0 and order.order_type == OrderType.LIMIT:
            self._add_to_order_book(order)

        self.trade_history.extend(trades)
        return trades

    def _match_buy_order(self, buy_order: Order) -> List[Trade]:
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

            price_level = self.asks.get_price_level(best_ask_price)
            if not price_level:
                break

            sell_order = price_level.get_top_order()
            if not sell_order:
                self.asks.get_best_price()  # Trigger cleanup
                continue

            trade_quantity = min(
                buy_order.remaining_quantity, sell_order.remaining_quantity
            )

            # FIX: Always use the limit order's price for trades
            trade_price = sell_order.price  # Use ask price for buy market orders

            trade = Trade.create_trade(buy_order, sell_order, trade_quantity)
            trades.append(trade)

            buy_order.filled_quantity += trade_quantity
            sell_order.filled_quantity += trade_quantity

            if sell_order.remaining_quantity == 0:
                self.asks.remove_order(sell_order.order_id)

        return trades

    def _match_sell_order(self, sell_order: Order) -> List[Trade]:
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

            price_level = self.bids.get_price_level(best_bid_price)
            if not price_level:
                break

            buy_order = price_level.get_top_order()
            if not buy_order:
                self.bids.get_best_price()  # Trigger cleanup
                continue

            trade_quantity = min(
                sell_order.remaining_quantity, buy_order.remaining_quantity
            )

            # FIX: Always use the limit order's price for trades
            trade_price = buy_order.price  # Use bid price for sell market orders

            trade = Trade.create_trade(buy_order, sell_order, trade_quantity)
            trades.append(trade)

            sell_order.filled_quantity += trade_quantity
            buy_order.filled_quantity += trade_quantity

            if buy_order.remaining_quantity == 0:
                self.bids.remove_order(buy_order.order_id)

        return trades

    def _add_to_order_book(self, order: Order):
        """Add remaining order quantity to order book"""
        if order.side == OrderSide.BUY:
            self.bids.add_order(order)
        else:
            self.asks.add_order(order)

    def cancel_order(self, order_id: str) -> bool:
        """Cancel order by ID"""
        # Check if order is in bids
        if order_id in self.bids.order_map:
            return self.bids.remove_order(order_id)

        # Check if order is in asks
        if order_id in self.asks.order_map:
            return self.asks.remove_order(order_id)

        # Order not found - might already be filled or cancelled
        return False

    def get_order_book_snapshot(self, levels: int = 10):
        """Get current order book snapshot"""
        from .order_types import OrderBookSnapshot

        bid_depth = self.bids.get_depth(levels)
        ask_depth = self.asks.get_depth(levels)

        spread = 0.0
        if bid_depth and ask_depth:
            spread = ask_depth[0][0] - bid_depth[0][0]

        return OrderBookSnapshot(
            timestamp=time.time(), bids=bid_depth, asks=ask_depth, spread=spread
        )


class AdaptiveMatchingEngine(BaseMatchingEngine):
    """Adaptive matching engine with regime detection"""

    def __init__(self, config: Optional[Dict] = None):
        super().__init__()

        # Replace with adaptive order books
        self.bids = AdaptiveOrderBookSide(OrderSide.BUY)
        self.asks = AdaptiveOrderBookSide(OrderSide.SELL)

        self.regime_detector = RegimeDetector(config)
        self.current_regime = MarketRegime.NORMAL
        self.regime_change_count = 0
        self.last_regime_change = time.time()

        # Statistics
        self.metrics_history = []
        self.regime_history = []

    def process_order(self, order: Order) -> List[Trade]:
        """Process order with adaptive logic"""
        # Update market metrics with new order
        self._update_market_metrics(order)

        # Detect regime change
        new_regime = self.regime_detector.detect_regime(
            self._get_best_bid(),
            self._get_best_ask(),
            self._get_buy_volume(),
            self._get_sell_volume(),
        )

        # Handle regime transition
        if new_regime != self.current_regime:
            self._transition_regime(new_regime)

        # Process order with current regime logic
        trades = self.add_order(order)

        # Record metrics
        self._record_metrics(order, trades)

        return trades

    def _transition_regime(self, new_regime: MarketRegime):
        """Smooth transition between regimes"""
        # print(f"Regime transition: {self.current_regime.value} -> {new_regime.value}")

        # Update order books to new regime
        self.bids.set_regime(new_regime)
        self.asks.set_regime(new_regime)

        # Update state
        self.current_regime = new_regime
        self.regime_change_count += 1
        self.last_regime_change = time.time()

        # Record regime history
        self.regime_history.append(
            {
                "timestamp": time.time(),
                "from_regime": self.current_regime.value,
                "to_regime": new_regime.value,
            }
        )

    def _update_market_metrics(self, order: Order):
        """Update internal market metrics for regime detection"""
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
        if bid and ask:
            return (bid + ask) / 2
        return 0.0

    def _get_spread(self) -> float:
        bid = self._get_best_bid()
        ask = self._get_best_ask()
        if bid and ask:
            return ask - bid
        return 0.0

    def _get_buy_volume(self) -> int:
        # Calculate total buy volume at best bid
        best_bid = self._get_best_bid()
        if best_bid:
            level = self.bids.get_price_level(best_bid)
            return level.total_volume if level else 0
        return 0

    def _get_sell_volume(self) -> int:
        # Calculate total sell volume at best ask
        best_ask = self._get_best_ask()
        if best_ask:
            level = self.asks.get_price_level(best_ask)
            return level.total_volume if level else 0
        return 0

    def _record_metrics(self, order: Order, trades: List[Trade]):
        """Record performance and market metrics"""
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
