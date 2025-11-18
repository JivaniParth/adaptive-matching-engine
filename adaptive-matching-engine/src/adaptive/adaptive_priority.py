"""
Adaptive priority queue implementations for different market regimes
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Deque
from collections import deque
import heapq

from ..core.order_types import Order, MarketRegime


class BasePriorityQueue(ABC):
    """Abstract base class for priority queues"""

    def __init__(self):
        self.orders = deque()

    @abstractmethod
    def push(self, order: Order):
        """Add order to queue"""
        pass

    @abstractmethod
    def pop(self) -> Optional[Order]:
        """Remove and return top order"""
        pass

    @abstractmethod
    def peek(self) -> Optional[Order]:
        """Return top order without removal"""
        pass

    def remove(self, order: Order) -> bool:
        """Remove specific order from queue"""
        try:
            self.orders.remove(order)
            return True
        except ValueError:
            return False

    def is_empty(self) -> bool:
        return len(self.orders) == 0

    def __len__(self) -> int:
        return len(self.orders)


class PriceTimePriorityQueue(BasePriorityQueue):
    """Standard Price-Time priority (FIFO at same price)"""

    def push(self, order: Order):
        """Add order maintaining FIFO at same price level"""
        self.orders.append(order)

    def pop(self) -> Optional[Order]:
        return self.orders.popleft() if self.orders else None

    def peek(self) -> Optional[Order]:
        return self.orders[0] if self.orders else None


class PriceSizeTimePriorityQueue(BasePriorityQueue):
    """Price-Size-Time priority (largest orders first at same price)"""

    def push(self, order: Order):
        """Add order and maintain size-based sorting"""
        self.orders.append(order)
        # Sort by size descending, then time ascending
        self.orders = deque(
            sorted(self.orders, key=lambda o: (-o.quantity, o.timestamp))
        )

    def pop(self) -> Optional[Order]:
        return self.orders.popleft() if self.orders else None

    def peek(self) -> Optional[Order]:
        return self.orders[0] if self.orders else None


class HybridPriorityQueue(BasePriorityQueue):
    """
    Hybrid priority queue that can switch between different priority schemes
    """

    def __init__(self, initial_regime: MarketRegime = MarketRegime.NORMAL):
        super().__init__()
        self.regime = initial_regime
        self._update_ordering()

    def set_regime(self, new_regime: MarketRegime):
        """Change regime and reorder queue"""
        if self.regime != new_regime:
            self.regime = new_regime
            self._update_ordering()

    def _update_ordering(self):
        """Reorder queue based on current regime"""
        if self.regime == MarketRegime.NORMAL:
            # Price-Time: FIFO (no sorting needed if maintained)
            pass
        elif self.regime in [MarketRegime.HIGH_VOLATILITY, MarketRegime.ILLIQUID]:
            # Price-Size-Time: Sort by size (desc), then time (asc)
            self.orders = deque(
                sorted(self.orders, key=lambda o: (-o.quantity, o.timestamp))
            )
        elif self.regime == MarketRegime.DIRECTIONAL:
            # Price-Time-Volume: Similar to PST but with different weights
            self.orders = deque(
                sorted(
                    self.orders,
                    key=lambda o: (-o.quantity * 0.7 - o.timestamp * 0.3, o.timestamp),
                )
            )
        else:
            # Default to Price-Time
            pass

    def push(self, order: Order):
        """Add order and maintain regime-appropriate ordering"""
        self.orders.append(order)
        self._update_ordering()

    def pop(self) -> Optional[Order]:
        return self.orders.popleft() if self.orders else None

    def peek(self) -> Optional[Order]:
        return self.orders[0] if self.orders else None


class AdaptivePriorityManager:
    """
    Manages adaptive priority queues for the matching engine
    """

    def __init__(self):
        self.queues = {}  # price -> HybridPriorityQueue
        self.current_regime = MarketRegime.NORMAL

    def get_queue(self, price: float) -> HybridPriorityQueue:
        """Get or create priority queue for price level"""
        if price not in self.queues:
            self.queues[price] = HybridPriorityQueue(self.current_regime)
        return self.queues[price]

    def set_regime(self, new_regime: MarketRegime):
        """Set new regime for all priority queues"""
        if self.current_regime != new_regime:
            self.current_regime = new_regime
            for queue in self.queues.values():
                queue.set_regime(new_regime)

    def add_order(self, order: Order) -> bool:
        """Add order to appropriate priority queue"""
        queue = self.get_queue(order.price)
        queue.push(order)
        return True

    def remove_order(self, order: Order) -> bool:
        """Remove order from its priority queue"""
        if order.price in self.queues:
            queue = self.queues[order.price]
            removed = queue.remove(order)

            # Clean up empty queues
            if queue.is_empty():
                del self.queues[order.price]

            return removed
        return False

    def get_top_order(self, price: float) -> Optional[Order]:
        """Get top order for price level"""
        if price in self.queues:
            return self.queues[price].peek()
        return None

    def get_all_prices(self) -> List[float]:
        """Get all prices with active orders"""
        return list(self.queues.keys())
