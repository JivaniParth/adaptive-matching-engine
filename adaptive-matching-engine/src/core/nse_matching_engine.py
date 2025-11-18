"""
NSE-Style Traditional Matching Engine

This module implements a matching engine that closely mimics the National Stock Exchange (NSE)
of India's order matching logic, including:
- Call auctions (opening/closing) with equilibrium price calculation
- Price-time priority in continuous trading
- Circuit breakers and price bands
- Multiple order types (Stop-Loss, Iceberg, FOK, etc.)
- Tick size validation
- Order validity handling

This serves as a realistic baseline for comparison with the adaptive matching engine.
"""

from typing import List, Optional, Dict, Tuple
import time
from collections import defaultdict
import threading
import queue
from .order_book import OrderBookSide, PriceLevel
from .order_types import Order, OrderSide, Trade, OrderType, OrderValidity, TradingPhase


class NSEMatchingEngine:
    """
    NSE-style matching engine with comprehensive market microstructure features.

    Features:
    - Call auctions (pre-open, closing) with equilibrium price calculation
    - Continuous trading with strict price-time priority
    - Circuit breakers with configurable thresholds
    - Dynamic price bands
    - Tick size validation
    - Stop-loss order triggering
    - Iceberg order handling
    - FOK (Fill-or-Kill) orders
    """

    def __init__(
        self,
        symbol: str = "NIFTY",
        tick_size: float = 0.05,
        circuit_breaker_pct: float = 10.0,
        price_band_pct: float = 20.0,
        async_cancel: bool = False,
    ):
        """
        Initialize NSE matching engine.

        Args:
            symbol: Trading symbol
            tick_size: Minimum price movement (NSE uses 0.05 for NIFTY)
            circuit_breaker_pct: Circuit breaker threshold (%)
            price_band_pct: Price band threshold (%)
        """
        self.symbol = symbol
        self.tick_size = tick_size
        self.circuit_breaker_pct = circuit_breaker_pct
        self.price_band_pct = price_band_pct

        # Order books
        self.bids = OrderBookSide(OrderSide.BUY)
        self.asks = OrderBookSide(OrderSide.SELL)

        # Trading state
        self.trading_phase = TradingPhase.CONTINUOUS
        self.is_halted = False

        # Reference prices for circuit breakers
        self.reference_price: Optional[float] = None  # Previous day close
        self.last_traded_price: Optional[float] = None
        self.opening_price: Optional[float] = None

        # Price bands (dynamic)
        self.upper_band: Optional[float] = None
        self.lower_band: Optional[float] = None

        # Auction state
        self.auction_orders: List[Order] = []  # Orders accumulated during auction

        # History
        self.trade_history: List[Trade] = []
        self.order_history: List[Order] = []

        # Stop-loss orders waiting to be triggered
        self.pending_stop_orders: Dict[str, Order] = {}

        # Statistics
        self.total_orders_processed = 0
        self.total_trades = 0
        self.circuit_breaker_hits = 0

        # Async cancellation support
        self.async_cancel = bool(async_cancel)
        self._cancel_queue: Optional[queue.Queue] = None
        self._cancel_worker_thread: Optional[threading.Thread] = None
        self._cancel_worker_running = False
        if self.async_cancel:
            self._cancel_queue = queue.Queue()
            self._cancel_worker_running = True
            self._cancel_worker_thread = threading.Thread(
                target=self._cancel_worker, daemon=True
            )
            self._cancel_worker_thread.start()

    def set_reference_price(self, price: float):
        """Set reference price (previous close) for circuit breaker calculations."""
        self.reference_price = price
        self._update_price_bands()

    def _update_price_bands(self):
        """Update upper and lower price bands based on reference price."""
        if self.reference_price:
            self.upper_band = self.reference_price * (1 + self.price_band_pct / 100)
            self.lower_band = self.reference_price * (1 - self.price_band_pct / 100)

    def _validate_tick_size(self, price: float) -> float:
        """Validate and round price to nearest tick size."""
        if self.tick_size > 0:
            return round(price / self.tick_size) * self.tick_size
        return price

    def _check_price_band(self, price: float) -> bool:
        """Check if price is within allowed bands."""
        if self.upper_band is None or self.lower_band is None:
            return True
        return self.lower_band <= price <= self.upper_band

    def _check_circuit_breaker(self, trade_price: float) -> bool:
        """
        Check if trade price triggers circuit breaker.
        Returns True if circuit breaker is hit.
        """
        if not self.reference_price:
            return False

        price_change_pct = (
            abs(trade_price - self.reference_price) / self.reference_price * 100
        )

        if price_change_pct >= self.circuit_breaker_pct:
            self.is_halted = True
            self.trading_phase = TradingPhase.HALTED
            self.circuit_breaker_hits += 1
            return True

        return False

    def resume_trading(self):
        """Resume trading after halt (manual intervention)."""
        self.is_halted = False
        self.trading_phase = TradingPhase.CONTINUOUS

    def set_trading_phase(self, phase: TradingPhase):
        """Change trading phase (e.g., from continuous to closing auction)."""
        self.trading_phase = phase
        if phase in [TradingPhase.PRE_OPEN, TradingPhase.CLOSING]:
            self.auction_orders = []

    def process_order(self, order: Order) -> List[Trade]:
        """
        Main entry point for order processing.
        Routes to appropriate handler based on trading phase and order type.
        """
        self.total_orders_processed += 1
        self.order_history.append(order)

        # Check if trading is halted
        if self.is_halted:
            return []

        # Check order expiry
        if order.is_expired(time.time()):
            return []

        # Validate tick size for limit orders
        if order.order_type in [OrderType.LIMIT, OrderType.STOP_LOSS]:
            order.price = self._validate_tick_size(order.price)

        # Check price bands
        if order.order_type in [OrderType.LIMIT, OrderType.STOP_LOSS]:
            if not self._check_price_band(order.price):
                return []  # Reject order outside price bands

        # Route based on trading phase
        if self.trading_phase in [TradingPhase.PRE_OPEN, TradingPhase.CLOSING]:
            return self._handle_auction_order(order)
        else:
            return self._handle_continuous_order(order)

    def _handle_auction_order(self, order: Order) -> List[Trade]:
        """Handle orders during call auction phase."""
        # In auction, just accumulate orders (no matching yet)
        self.auction_orders.append(order)
        return []

    def execute_call_auction(self) -> List[Trade]:
        """
        Execute call auction to determine equilibrium price.

        Algorithm:
        1. Find price that maximizes tradeable volume
        2. If tie, choose price closest to reference price
        3. Match all orders at equilibrium price
        4. Move to continuous trading
        """
        if not self.auction_orders:
            return []

        # Build cumulative order book for auction
        buy_orders_by_price = defaultdict(list)
        sell_orders_by_price = defaultdict(list)

        for order in self.auction_orders:
            if order.side == OrderSide.BUY:
                buy_orders_by_price[order.price].append(order)
            else:
                sell_orders_by_price[order.price].append(order)

        # Calculate equilibrium price
        equilibrium_price, max_volume = self._find_equilibrium_price(
            buy_orders_by_price, sell_orders_by_price
        )

        if equilibrium_price is None:
            # No overlap - add orders to book without matching
            for order in self.auction_orders:
                if order.order_type == OrderType.LIMIT:
                    self._add_to_order_book(order)
            self.auction_orders = []
            return []

        # Execute matches at equilibrium price
        trades = self._execute_auction_at_price(
            equilibrium_price, buy_orders_by_price, sell_orders_by_price
        )

        # Set opening price if this was pre-open auction
        if self.trading_phase == TradingPhase.PRE_OPEN:
            self.opening_price = equilibrium_price
            self.last_traded_price = equilibrium_price
            if self.reference_price is None:
                self.reference_price = equilibrium_price
                self._update_price_bands()

        # Add unmatched orders to book
        for order in self.auction_orders:
            if order.remaining_quantity > 0 and order.order_type == OrderType.LIMIT:
                self._add_to_order_book(order)

        self.auction_orders = []
        self.trading_phase = TradingPhase.CONTINUOUS

        return trades

    def _find_equilibrium_price(
        self, buy_orders, sell_orders
    ) -> Tuple[Optional[float], int]:
        """
        Find equilibrium price that maximizes volume.
        Returns (price, volume) or (None, 0) if no overlap.
        """
        # Get all unique prices
        all_prices = sorted(set(list(buy_orders.keys()) + list(sell_orders.keys())))

        if not all_prices:
            return None, 0

        best_price = None
        max_volume = 0

        for price in all_prices:
            # Calculate buy volume at this price (all buys >= price)
            buy_volume = sum(
                sum(o.quantity for o in orders)
                for p, orders in buy_orders.items()
                if p >= price
            )

            # Calculate sell volume at this price (all sells <= price)
            sell_volume = sum(
                sum(o.quantity for o in orders)
                for p, orders in sell_orders.items()
                if p <= price
            )

            # Tradeable volume is minimum of buy and sell
            tradeable_volume = min(buy_volume, sell_volume)

            if tradeable_volume > max_volume:
                max_volume = tradeable_volume
                best_price = price
            elif tradeable_volume == max_volume and best_price is not None:
                # Tie-breaker: choose price closer to reference
                if self.reference_price:
                    if abs(price - self.reference_price) < abs(
                        best_price - self.reference_price
                    ):
                        best_price = price

        return best_price, max_volume

    def _execute_auction_at_price(
        self, price: float, buy_orders, sell_orders
    ) -> List[Trade]:
        """Execute auction matches at equilibrium price."""
        trades = []

        # Get all buy orders that can match (price >= equilibrium)
        buyers = []
        for p, orders in buy_orders.items():
            if p >= price:
                buyers.extend(orders)

        # Get all sell orders that can match (price <= equilibrium)
        sellers = []
        for p, orders in sell_orders.items():
            if p <= price:
                sellers.extend(orders)

        # Sort by time priority (FIFO)
        buyers.sort(key=lambda o: o.timestamp)
        sellers.sort(key=lambda o: o.timestamp)

        # Match in time priority order
        buy_idx = 0
        sell_idx = 0

        while buy_idx < len(buyers) and sell_idx < len(sellers):
            buy_order = buyers[buy_idx]
            sell_order = sellers[sell_idx]

            if buy_order.remaining_quantity == 0:
                buy_idx += 1
                continue

            if sell_order.remaining_quantity == 0:
                sell_idx += 1
                continue

            # Create trade at equilibrium price
            trade_qty = min(buy_order.remaining_quantity, sell_order.remaining_quantity)

            trade = Trade(
                trade_id=f"T-{len(self.trade_history)}",
                buy_order_id=buy_order.order_id,
                sell_order_id=sell_order.order_id,
                price=price,
                quantity=trade_qty,
                timestamp=time.time(),
            )

            trades.append(trade)
            self.trade_history.append(trade)
            self.total_trades += 1

            buy_order.filled_quantity += trade_qty
            sell_order.filled_quantity += trade_qty

            if buy_order.remaining_quantity == 0:
                buy_idx += 1
            if sell_order.remaining_quantity == 0:
                sell_idx += 1

        return trades

    def _handle_continuous_order(self, order: Order) -> List[Trade]:
        """Handle orders during continuous trading phase."""

        # Handle stop-loss orders
        if order.order_type in [OrderType.STOP_LOSS, OrderType.STOP_LOSS_MARKET]:
            return self._handle_stop_loss_order(order)

        # Handle FOK orders
        if order.order_type == OrderType.FOK:
            return self._handle_fok_order(order)

        # Handle regular orders (LIMIT, MARKET, IOC, ICEBERG)
        trades = self._match_order(order)

        # Add remaining quantity to book (if limit order and not IOC)
        if order.remaining_quantity > 0:
            if order.order_type == OrderType.LIMIT:
                self._add_to_order_book(order)
            elif order.order_type == OrderType.ICEBERG:
                self._add_iceberg_to_book(order)

        return trades

    def _handle_stop_loss_order(self, order: Order) -> List[Trade]:
        """Handle stop-loss orders - wait for trigger."""
        # Check if stop price is already triggered
        if self._is_stop_triggered(order):
            order.is_triggered = True
            # Convert to market or limit order
            if order.order_type == OrderType.STOP_LOSS_MARKET:
                order.order_type = OrderType.MARKET
                order.price = 0.0
            else:
                order.order_type = OrderType.LIMIT
            return self._match_order(order)
        else:
            # Add to pending stop orders
            self.pending_stop_orders[order.order_id] = order
            return []

    def _is_stop_triggered(self, order: Order) -> bool:
        """Check if stop-loss order should be triggered."""
        if not self.last_traded_price or not order.stop_price:
            return False

        if order.side == OrderSide.BUY:
            # Buy stop: trigger when market price >= stop price
            return self.last_traded_price >= order.stop_price
        else:
            # Sell stop: trigger when market price <= stop price
            return self.last_traded_price <= order.stop_price

    def _check_pending_stop_orders(self):
        """Check all pending stop orders for triggering."""
        triggered = []
        for order_id, order in list(self.pending_stop_orders.items()):
            if self._is_stop_triggered(order):
                triggered.append(order)
                del self.pending_stop_orders[order_id]

        # Process triggered orders
        for order in triggered:
            order.is_triggered = True
            if order.order_type == OrderType.STOP_LOSS_MARKET:
                order.order_type = OrderType.MARKET
                order.price = 0.0
            else:
                order.order_type = OrderType.LIMIT
            self._match_order(order)

    def _handle_fok_order(self, order: Order) -> List[Trade]:
        """Handle Fill-or-Kill order - execute fully or reject."""
        # Check if full quantity can be filled
        if order.side == OrderSide.BUY:
            available = self._get_available_volume_at_price(
                self.asks,
                order.price if order.order_type == OrderType.LIMIT else float("inf"),
            )
        else:
            available = self._get_available_volume_at_price(
                self.bids, order.price if order.order_type == OrderType.LIMIT else 0
            )

        if available >= order.quantity:
            # Can fill - execute normally
            return self._match_order(order)
        else:
            # Cannot fill - reject
            return []

    def _get_available_volume_at_price(
        self, book_side: OrderBookSide, limit_price: float
    ) -> int:
        """Get total available volume up to limit price."""
        total = 0
        if book_side.side == OrderSide.SELL:
            # For asks, sum all volumes <= limit_price
            for price, level in book_side.price_levels.items():
                if price <= limit_price:
                    total += level.total_volume
        else:
            # For bids, sum all volumes >= limit_price
            for price, level in book_side.price_levels.items():
                if price >= limit_price:
                    total += level.total_volume
        return total

    def _match_order(self, order: Order) -> List[Trade]:
        """Match order using standard price-time priority."""
        trades = []

        if order.side == OrderSide.BUY:
            trades = self._match_buy_order(order)
        else:
            trades = self._match_sell_order(order)

        # Update last traded price and check circuit breaker
        if trades:
            self.last_traded_price = trades[-1].price
            if self._check_circuit_breaker(self.last_traded_price):
                # Circuit breaker hit - halt trading
                pass

            # Check pending stop orders
            self._check_pending_stop_orders()

        self.trade_history.extend(trades)
        self.total_trades += len(trades)

        return trades

    def _match_buy_order(self, buy_order: Order) -> List[Trade]:
        """Match buy order against sell side."""
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

            # For iceberg orders, only match visible quantity
            available_qty = sell_order.visible_quantity
            trade_quantity = min(buy_order.remaining_quantity, available_qty)

            trade_price = sell_order.price

            trade = Trade(
                trade_id=f"T-{len(self.trade_history)}",
                buy_order_id=buy_order.order_id,
                sell_order_id=sell_order.order_id,
                price=trade_price,
                quantity=trade_quantity,
                timestamp=time.time(),
            )

            trades.append(trade)

            buy_order.filled_quantity += trade_quantity
            sell_order.filled_quantity += trade_quantity

            # Update price level volume
            price_level.total_volume -= trade_quantity

            # Handle iceberg replenishment or removal
            if sell_order.remaining_quantity == 0:
                self.asks.remove_order(sell_order.order_id)
            elif sell_order.order_type == OrderType.ICEBERG:
                # Iceberg order - may need to refresh visible quantity
                # For simplicity, keep in place (real NSE may re-queue)
                pass

        return trades

    def _match_sell_order(self, sell_order: Order) -> List[Trade]:
        """Match sell order against buy side."""
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

            # For iceberg orders, only match visible quantity
            available_qty = buy_order.visible_quantity
            trade_quantity = min(sell_order.remaining_quantity, available_qty)

            trade_price = buy_order.price

            trade = Trade(
                trade_id=f"T-{len(self.trade_history)}",
                buy_order_id=buy_order.order_id,
                sell_order_id=sell_order.order_id,
                price=trade_price,
                quantity=trade_quantity,
                timestamp=time.time(),
            )

            trades.append(trade)

            sell_order.filled_quantity += trade_quantity
            buy_order.filled_quantity += trade_quantity

            # Update price level volume
            price_level.total_volume -= trade_quantity

            # Handle iceberg replenishment or removal
            if buy_order.remaining_quantity == 0:
                self.bids.remove_order(buy_order.order_id)
            elif buy_order.order_type == OrderType.ICEBERG:
                # Iceberg order - may need to refresh visible quantity
                pass

        return trades

    def _add_to_order_book(self, order: Order):
        """Add order to appropriate order book side."""
        if order.side == OrderSide.BUY:
            self.bids.add_order(order)
        else:
            self.asks.add_order(order)

    def _add_iceberg_to_book(self, order: Order):
        """Add iceberg order - only visible quantity shown."""
        # In real NSE, iceberg orders have special handling
        # For simplicity, treat like regular order with visible_quantity property
        self._add_to_order_book(order)

    def cancel_order(self, order_id: str) -> bool:
        """Cancel order by ID."""
        # If async cancellation enabled, enqueue request
        if self.async_cancel and self._cancel_queue is not None:
            try:
                self._cancel_queue.put_nowait(order_id)
                return True
            except queue.Full:
                return False

        # Synchronous cancellation (default)
        # Check regular order books
        if order_id in self.bids.order_map:
            return self.bids.remove_order(order_id)
        if order_id in self.asks.order_map:
            return self.asks.remove_order(order_id)

        # Check pending stop orders
        if order_id in self.pending_stop_orders:
            del self.pending_stop_orders[order_id]
            return True

        return False

    def _cancel_worker(self):
        """Background worker that processes cancellation requests from a queue."""
        q = self._cancel_queue
        while self._cancel_worker_running:
            try:
                order_id = q.get(timeout=0.5)
            except queue.Empty:
                continue

            # Attempt to cancel in both books and pending stops
            try:
                cancelled = False
                if order_id in self.bids.order_map:
                    cancelled = self.bids.remove_order(order_id)
                elif order_id in self.asks.order_map:
                    cancelled = self.asks.remove_order(order_id)
                elif order_id in self.pending_stop_orders:
                    del self.pending_stop_orders[order_id]
                    cancelled = True

                # Optionally: log or track cancellation outcome
            finally:
                q.task_done()

    def shutdown(self, wait: bool = True):
        """Shutdown background workers cleanly."""
        if self.async_cancel and self._cancel_queue is not None:
            self._cancel_worker_running = False
            if wait and self._cancel_worker_thread is not None:
                self._cancel_worker_thread.join(timeout=1.0)

    def get_order_book_snapshot(self, levels: int = 10):
        """Get current order book snapshot."""
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
        """Get engine statistics."""
        return {
            "total_orders": self.total_orders_processed,
            "total_trades": self.total_trades,
            "circuit_breaker_hits": self.circuit_breaker_hits,
            "pending_stop_orders": len(self.pending_stop_orders),
            "trading_phase": self.trading_phase.value,
            "is_halted": self.is_halted,
            "last_traded_price": self.last_traded_price,
            "reference_price": self.reference_price,
            "opening_price": self.opening_price,
        }
