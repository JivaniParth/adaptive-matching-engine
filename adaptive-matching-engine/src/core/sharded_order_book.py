"""
Sharded Order Book Implementation

Partitions orders across multiple independent order books (shards) to reduce lock contention
and enable parallel processing of orders and cancellations.

Key benefits:
- Parallel cancellations: Each shard can be accessed independently
- Reduced lock contention: Multiple threads can work on different shards simultaneously
- Better cache locality: Each shard is smaller and fits better in CPU cache
- Scalable: Can add more shards as load increases

Sharding strategy:
- Orders are distributed by hash(order_id) % num_shards
- Matching still requires coordination across shards for best price discovery
- Each shard maintains its own heap and price levels
"""

from typing import List, Optional, Dict, Tuple
from threading import RLock
import hashlib
from .order_book import OrderBookSide, PriceLevel
from .order_types import Order, OrderSide


class ShardedOrderBookSide:
    """
    Order book side partitioned into multiple shards for parallel access.

    Each shard is an independent OrderBookSide with its own lock, allowing
    concurrent operations on different shards.
    """

    def __init__(self, side: OrderSide, num_shards: int = 8):
        """
        Initialize sharded order book side.

        Args:
            side: BUY or SELL
            num_shards: Number of shards (default 8, power of 2 recommended)
        """
        self.side = side
        self.num_shards = max(1, num_shards)

        # Create independent shards
        self.shards: List[OrderBookSide] = [
            OrderBookSide(side) for _ in range(self.num_shards)
        ]

        # Global best price cache with lock
        self._best_price_cache: Optional[float] = None
        self._cache_lock = RLock()
        self._cache_valid = False

        # Statistics
        self.total_orders = 0
        self.total_cancellations = 0

    def _get_shard_index(self, order_id: str) -> int:
        """
        Determine which shard an order belongs to based on its ID.
        Uses hash for uniform distribution.
        """
        # Fast hash using first few characters if order_id is string
        if isinstance(order_id, str):
            # Simple but effective: sum of character codes
            hash_val = sum(ord(c) for c in order_id[:8])
        else:
            hash_val = hash(order_id)

        return hash_val % self.num_shards

    def add_order(self, order: Order) -> bool:
        """Add order to appropriate shard."""
        shard_idx = self._get_shard_index(order.order_id)
        result = self.shards[shard_idx].add_order(order)

        if result:
            self.total_orders += 1
            # Invalidate best price cache
            with self._cache_lock:
                self._cache_valid = False

        return result

    def remove_order(self, order_id: str) -> bool:
        """Remove order from its shard."""
        shard_idx = self._get_shard_index(order_id)
        result = self.shards[shard_idx].remove_order(order_id)

        if result:
            self.total_cancellations += 1
            # Invalidate best price cache
            with self._cache_lock:
                self._cache_valid = False

        return result

    def get_best_price(self) -> Optional[float]:
        """
        Get best price across all shards.

        Uses cached value when valid, otherwise scans all shards.
        For BUY: returns maximum price
        For SELL: returns minimum price
        """
        with self._cache_lock:
            if self._cache_valid and self._best_price_cache is not None:
                return self._best_price_cache

            # Scan all shards for best price
            best_price = None

            for shard in self.shards:
                shard_best = shard.get_best_price()
                if shard_best is None:
                    continue

                if best_price is None:
                    best_price = shard_best
                elif self.side == OrderSide.BUY:
                    # For bids, want maximum
                    best_price = max(best_price, shard_best)
                else:
                    # For asks, want minimum
                    best_price = min(best_price, shard_best)

            # Cache the result
            self._best_price_cache = best_price
            self._cache_valid = True

            return best_price

    def get_price_level(self, price: float) -> Optional[PriceLevel]:
        """
        Get aggregate price level across all shards.

        Note: Returns a combined view, but orders are still distributed.
        For matching, we'll need to iterate shards.
        """
        # Find shards that have this price level
        combined_level = None

        for shard in self.shards:
            level = shard.get_price_level(price)
            if level and not level.is_empty():
                if combined_level is None:
                    # Create a virtual combined level
                    combined_level = PriceLevel(price)
                    combined_level.orders = level.orders.copy()
                    combined_level.total_volume = level.total_volume
                else:
                    # Merge orders from this shard
                    combined_level.orders.extend(level.orders)
                    combined_level.total_volume += level.total_volume

        return combined_level

    def get_orders_at_best_price(self) -> List[Order]:
        """
        Get all orders at the best price across all shards.
        Returns orders sorted by timestamp (FIFO).
        """
        best_price = self.get_best_price()
        if best_price is None:
            return []

        all_orders = []

        # Collect orders from all shards at this price
        for shard in self.shards:
            level = shard.get_price_level(best_price)
            if level and not level.is_empty():
                all_orders.extend(list(level.orders))

        # Sort by timestamp for FIFO matching
        all_orders.sort(key=lambda o: o.timestamp)

        return all_orders

    def get_depth(self, levels: int = 5) -> List[Tuple[float, int]]:
        """
        Get aggregated depth across all shards.

        Combines price levels from all shards and returns top N levels.
        """
        # Collect all price levels from all shards
        price_volume_map: Dict[float, int] = {}

        for shard in self.shards:
            shard_depth = shard.get_depth(
                levels * 2
            )  # Get more to ensure we have enough after aggregation
            for price, volume in shard_depth:
                price_volume_map[price] = price_volume_map.get(price, 0) + volume

        # Sort and return top N levels
        if self.side == OrderSide.BUY:
            # Bids: highest prices first
            sorted_levels = sorted(price_volume_map.items(), key=lambda x: -x[0])
        else:
            # Asks: lowest prices first
            sorted_levels = sorted(price_volume_map.items(), key=lambda x: x[0])

        return sorted_levels[:levels]

    def remove_order_from_price_level(self, order: Order, price: float) -> bool:
        """
        Remove a specific order from a price level.
        Used during matching when order is partially filled.
        """
        shard_idx = self._get_shard_index(order.order_id)
        result = self.shards[shard_idx].remove_order(order.order_id)

        if result:
            with self._cache_lock:
                self._cache_valid = False

        return result

    def get_statistics(self) -> Dict:
        """Get sharding statistics."""
        shard_stats = []

        for i, shard in enumerate(self.shards):
            shard_stats.append(
                {
                    "shard_id": i,
                    "num_orders": len(shard.order_map),
                    "num_price_levels": len(shard.price_levels),
                }
            )

        return {
            "num_shards": self.num_shards,
            "total_orders": self.total_orders,
            "total_cancellations": self.total_cancellations,
            "shard_details": shard_stats,
        }


class ShardedAdaptiveOrderBookSide(ShardedOrderBookSide):
    """
    Sharded order book side with adaptive price levels.

    Extends ShardedOrderBookSide to use AdaptiveOrderBookSide for each shard,
    enabling regime-based matching strategies with the benefits of sharding.
    """

    def __init__(self, side: OrderSide, num_shards: int = 8, regime=None):
        """Initialize sharded adaptive order book side."""
        from .order_book import AdaptiveOrderBookSide
        from .order_types import MarketRegime

        self.side = side
        self.num_shards = max(1, num_shards)
        self.regime = regime or MarketRegime.NORMAL

        # Create adaptive shards
        self.shards: List[AdaptiveOrderBookSide] = [
            AdaptiveOrderBookSide(side, self.regime) for _ in range(self.num_shards)
        ]

        # Initialize parent class attributes
        self._best_price_cache: Optional[float] = None
        self._cache_lock = RLock()
        self._cache_valid = False
        self.total_orders = 0
        self.total_cancellations = 0

    def set_regime(self, new_regime):
        """Set regime for all shards."""
        self.regime = new_regime
        for shard in self.shards:
            shard.set_regime(new_regime)
