import heapq
from collections import defaultdict, deque
from typing import Dict, List, Optional, Tuple
from .order_types import Order, OrderSide, Trade, MarketRegime
from threading import RLock
import bisect


class PriceLevel:
    """Represents all orders at a specific price level"""

    def __init__(self, price: float):
        self.price = price
        self.orders = deque()  # FIFO queue for orders
        self.total_volume = 0
        # Flag used by adaptive price levels to indicate a deferred sort
        self._needs_resort = False

    def add_order(self, order: Order):
        self.orders.append(order)
        self.total_volume += order.remaining_quantity

    def remove_order(self, order: Order) -> bool:
        """Remove specific order from price level"""
        try:
            self.orders.remove(order)
            # FIX: Subtract the remaining quantity, not filled quantity
            self.total_volume -= order.remaining_quantity
            return True
        except ValueError:
            return False

    def get_top_order(self) -> Optional[Order]:
        return self.orders[0] if self.orders else None

    def is_empty(self) -> bool:
        return len(self.orders) == 0

    def __lt__(self, other: "PriceLevel") -> bool:
        return self.price < other.price


class AdaptivePriceLevel(PriceLevel):
    """Price level that adapts its internal ordering based on market regime"""

    def __init__(self, price: float, regime: MarketRegime = MarketRegime.NORMAL):
        super().__init__(price)
        self.regime = regime
        self._maintain_sorted = False
        self._sorted = False

    def set_regime(self, new_regime: MarketRegime):
        """Change regime and re-sort orders if needed"""
        if self.regime != new_regime:
            self.regime = new_regime
            # Mark for re-sort; perform actual re-sort lazily when needed
            self._needs_resort = True
            self._sorted = False

    def _re_sort_orders(self):
        """Re-sort orders based on current regime"""
        if self.regime == MarketRegime.NORMAL:
            # Price-Time: Maintain FIFO (no sorting needed)
            self._maintain_sorted = False
            self._sorted = True
            self._needs_resort = False
        elif self.regime in [MarketRegime.HIGH_VOLATILITY, MarketRegime.ILLIQUID]:
            # Price-Size-Time: maintain an order list sorted by size desc then time asc
            # Instead of resorting entire collection every time, we'll create a sorted list
            # and convert back to deque for FIFO access of the prioritized order
            orders_list = list(self.orders)
            orders_list.sort(key=lambda o: (-o.remaining_quantity, o.timestamp))
            self.orders = deque(orders_list)
            self._maintain_sorted = True
            self._sorted = True
            self._needs_resort = False
        elif self.regime == MarketRegime.HIGH_FREQUENCY:
            # Pro-Rata: We'll handle this differently during matching
            self._maintain_sorted = False
            self._sorted = True
            self._needs_resort = False

    def add_order(self, order: Order):
        # When maintaining sorted order by size, insert in sorted position to
        # avoid repeatedly sorting the entire deque.
        if self._maintain_sorted:
            # Ensure orders is a list for bisect insertion
            orders_list = list(self.orders)
            # Key: (-size, timestamp) so largest sizes come first
            key = (-order.remaining_quantity, order.timestamp)
            # Build list of keys for bisect
            keys = [(-o.remaining_quantity, o.timestamp) for o in orders_list]
            idx = bisect.bisect_left(keys, key)
            orders_list.insert(idx, order)
            self.orders = deque(orders_list)
            self.total_volume += order.remaining_quantity
            self._sorted = True
            self._needs_resort = False
        else:
            super().add_order(order)

    def get_top_order(self) -> Optional[Order]:
        # Lazily re-sort if needed
        if self._needs_resort and self._maintain_sorted:
            self._re_sort_orders()
        return self.orders[0] if self.orders else None


class OrderBookSide:
    """Base class for Bid/Ask sides of the order book"""

    def __init__(self, side: OrderSide):
        self.side = side
        self.heap = []  # Min-heap for asks, Max-heap for bids (using negative prices)
        self.price_levels: Dict[float, PriceLevel] = {}
        self.order_map: Dict[str, Order] = {}
        self.order_to_price_level: Dict[str, PriceLevel] = {}
        # Lock to protect concurrent access (add/remove/reads)
        self.lock = RLock()

    def _heap_push(self, price: float):
        """Push price to heap with proper comparison"""
        if self.side == OrderSide.SELL:
            heapq.heappush(self.heap, price)  # Min-heap for asks
        else:
            heapq.heappush(self.heap, -price)  # Max-heap for bids (using negatives)

    def _heap_pop(self) -> Optional[float]:
        """Pop best price from heap"""
        if not self.heap:
            return None
        if self.side == OrderSide.SELL:
            return heapq.heappop(self.heap)  # Min price for asks
        else:
            return -heapq.heappop(self.heap)  # Max price for bids

    def _heap_peek(self) -> Optional[float]:
        """Get best price without popping"""
        if not self.heap:
            return None
        if self.side == OrderSide.SELL:
            return self.heap[0]  # Min price for asks
        else:
            return -self.heap[0]  # Max price for bids

    def add_order(self, order: Order) -> bool:
        """Add order to order book side"""
        price = order.price
        with self.lock:
            if price not in self.price_levels:
                # Create new price level
                price_level = PriceLevel(price)
                self.price_levels[price] = price_level
                self._heap_push(price)
            else:
                price_level = self.price_levels[price]

            # Add order to price level
            price_level.add_order(order)

            # Update mappings for O(1) cancellation
            self.order_map[order.order_id] = order
            self.order_to_price_level[order.order_id] = price_level
            return True

    def remove_order(self, order_id: str) -> bool:
        """Remove order by ID in O(1) average time"""
        with self.lock:
            if order_id not in self.order_to_price_level:
                return False

            price_level = self.order_to_price_level[order_id]
            order = self.order_map[order_id]

            # Remove from price level
            removed = price_level.remove_order(order)
            if not removed:
                return False

            # Remove from mappings
            del self.order_map[order_id]
            del self.order_to_price_level[order_id]

            # Clean up empty price levels immediately
            if price_level.is_empty():
                # Remove from price_levels dict
                if price_level.price in self.price_levels:
                    del self.price_levels[price_level.price]

                # Rebuild heap without this price
                new_heap = []
                for price in self.price_levels.keys():
                    if self.side == OrderSide.SELL:
                        heapq.heappush(new_heap, price)
                    else:
                        heapq.heappush(new_heap, -price)
                self.heap = new_heap
                heapq.heapify(self.heap)

            return True

    def _remove_price_level(self, price: float):
        """Remove empty price level from all data structures"""
        if price in self.price_levels:
            del self.price_levels[price]

        # Rebuild heap without the removed price
        new_heap = []
        for price_val in self.price_levels.keys():
            self._heap_push_to_custom(new_heap, price_val)

        self.heap = new_heap
        heapq.heapify(self.heap)

    def _heap_push_to_custom(self, heap: list, price: float):
        """Push price to a custom heap"""
        if self.side == OrderSide.SELL:
            heapq.heappush(heap, price)  # Min-heap for asks
        else:
            heapq.heappush(heap, -price)  # Max-heap for bids

    def _schedule_price_level_cleanup(self, price: float):
        """Schedule empty price level for cleanup (lazy deletion)"""
        # In production, you might want immediate cleanup
        # For now, we'll use lazy cleanup during get_best_price
        pass

    def get_best_price(self) -> Optional[float]:
        """Get best price with lazy cleanup of empty levels"""
        with self.lock:
            while self.heap:
                best_price = self._heap_peek()
                if best_price is None:
                    return None

                # Check if price level still exists and has orders
                if (
                    best_price in self.price_levels
                    and not self.price_levels[best_price].is_empty()
                ):
                    return best_price
                else:
                    # Remove empty price level
                    self._heap_pop()
                    if best_price in self.price_levels:
                        del self.price_levels[best_price]

            return None

    def get_price_level(self, price: float) -> Optional[PriceLevel]:
        with self.lock:
            return self.price_levels.get(price)

    def get_depth(self, levels: int = 5) -> List[Tuple[float, int]]:
        """Get top N price levels with total volume"""
        with self.lock:
            depth = []
            temp_heap = self.heap.copy()

            for _ in range(min(levels, len(temp_heap))):
                if not temp_heap:
                    break

                price = self._heap_peek_from_custom(temp_heap)
                if price is None:
                    break

                heapq.heappop(temp_heap)  # Remove from temp heap
                price_level = self.price_levels.get(price)
                if price_level and not price_level.is_empty():
                    depth.append((price, price_level.total_volume))

            return depth

    def _heap_peek_from_custom(self, custom_heap: list) -> Optional[float]:
        """Peek from a custom heap"""
        if not custom_heap:
            return None
        if self.side == OrderSide.SELL:
            return custom_heap[0]
        else:
            return -custom_heap[0]


class AdaptiveOrderBookSide(OrderBookSide):
    """Order book side with adaptive price levels"""

    def __init__(self, side: OrderSide, regime: MarketRegime = MarketRegime.NORMAL):
        super().__init__(side)
        self.regime = regime

    def set_regime(self, new_regime: MarketRegime):
        """Set new regime for all price levels"""
        if self.regime != new_regime:
            self.regime = new_regime
            for price_level in self.price_levels.values():
                if isinstance(price_level, AdaptivePriceLevel):
                    price_level.set_regime(new_regime)

    def add_order(self, order: Order) -> bool:
        price = order.price

        if price not in self.price_levels:
            # Create new adaptive price level
            price_level = AdaptivePriceLevel(price, self.regime)
            self.price_levels[price] = price_level
            self._heap_push(price)

        return super().add_order(order)
