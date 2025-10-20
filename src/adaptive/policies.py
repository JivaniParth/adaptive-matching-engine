"""
Policy definitions for different market regimes
"""

from dataclasses import dataclass
from typing import Callable, Dict, Any
from enum import Enum

from ..core.order_types import MarketRegime, Order, OrderSide
from .adaptive_priority import (
    BasePriorityQueue,
    PriceTimePriorityQueue,
    PriceSizeTimePriorityQueue,
)


class MatchingAlgorithm(Enum):
    FIFO = "FIFO"
    SIZE_PRIORITY = "SIZE_PRIORITY"
    PRO_RATA = "PRO_RATA"
    HYBRID = "HYBRID"


@dataclass
class RegimePolicy:
    """Policy configuration for a market regime"""

    regime: MarketRegime
    priority_rule: str
    matching_algorithm: MatchingAlgorithm
    description: str
    liquidity_incentive: bool
    parameters: Dict[str, Any]

    # Custom matching function (if needed)
    matching_function: Callable = None


class PolicyManager:
    """Manages and applies regime-specific policies"""

    def __init__(self):
        self.policies = self._initialize_policies()
        self.current_policy = self.policies[MarketRegime.NORMAL]

    def _initialize_policies(self) -> Dict[MarketRegime, RegimePolicy]:
        """Initialize all regime policies"""
        return {
            MarketRegime.NORMAL: RegimePolicy(
                regime=MarketRegime.NORMAL,
                priority_rule="PRICE_TIME",
                matching_algorithm=MatchingAlgorithm.FIFO,
                description="Standard Price-Time priority for normal market conditions",
                liquidity_incentive=False,
                parameters={
                    "max_spread": 0.02,
                    "min_liquidity": 1000,
                },
            ),
            MarketRegime.HIGH_VOLATILITY: RegimePolicy(
                regime=MarketRegime.HIGH_VOLATILITY,
                priority_rule="PRICE_SIZE_TIME",
                matching_algorithm=MatchingAlgorithm.SIZE_PRIORITY,
                description="Price-Size-Time priority to encourage liquidity during volatility",
                liquidity_incentive=True,
                parameters={
                    "large_order_threshold": 100,
                    "size_weight": 0.7,
                    "time_weight": 0.3,
                },
            ),
            MarketRegime.ILLIQUID: RegimePolicy(
                regime=MarketRegime.ILLIQUID,
                priority_rule="PRICE_SIZE_TIME",
                matching_algorithm=MatchingAlgorithm.SIZE_PRIORITY,
                description="Price-Size-Time priority to improve liquidity in thin markets",
                liquidity_incentive=True,
                parameters={
                    "large_order_threshold": 50,
                    "size_weight": 0.8,
                    "time_weight": 0.2,
                },
            ),
            MarketRegime.DIRECTIONAL: RegimePolicy(
                regime=MarketRegime.DIRECTIONAL,
                priority_rule="PRICE_TIME_VOLUME",
                matching_algorithm=MatchingAlgorithm.HYBRID,
                description="Hybrid priority considering both time and volume",
                liquidity_incentive=True,
                parameters={
                    "volume_threshold": 0.7,
                    "time_decay_factor": 0.1,
                },
            ),
            MarketRegime.HIGH_FREQUENCY: RegimePolicy(
                regime=MarketRegime.HIGH_FREQUENCY,
                priority_rule="PRICE_TIME",
                matching_algorithm=MatchingAlgorithm.PRO_RATA,
                description="Price-Time with pro-rata matching for large orders",
                liquidity_incentive=False,
                parameters={
                    "pro_rata_threshold": 200,
                    "small_order_preference": 0.1,
                },
            ),
        }

    def get_policy(self, regime: MarketRegime) -> RegimePolicy:
        """Get policy for specific regime"""
        return self.policies.get(regime, self.policies[MarketRegime.NORMAL])

    def set_current_policy(self, regime: MarketRegime):
        """Set current active policy"""
        self.current_policy = self.get_policy(regime)

    def apply_matching_policy(self, orders: list, incoming_order: Order) -> list:
        """Apply current policy's matching algorithm to orders"""
        if self.current_policy.matching_algorithm == MatchingAlgorithm.FIFO:
            return self._fifo_matching(orders, incoming_order)
        elif self.current_policy.matching_algorithm == MatchingAlgorithm.SIZE_PRIORITY:
            return self._size_priority_matching(orders, incoming_order)
        elif self.current_policy.matching_algorithm == MatchingAlgorithm.PRO_RATA:
            return self._pro_rata_matching(orders, incoming_order)
        else:
            return self._fifo_matching(orders, incoming_order)  # Default

    def _fifo_matching(self, orders: list, incoming_order: Order) -> list:
        """First-In-First-Out matching (Price-Time)"""
        # Simple FIFO - return orders in their current sequence
        return orders

    def _size_priority_matching(self, orders: list, incoming_order: Order) -> list:
        """Size-priority matching (largest orders first)"""
        return sorted(orders, key=lambda o: (-o.quantity, o.timestamp))

    def _pro_rata_matching(self, orders: list, incoming_order: Order) -> list:
        """Pro-rata matching for large incoming orders"""
        if incoming_order.quantity < self.current_policy.parameters.get(
            "pro_rata_threshold", 200
        ):
            return self._fifo_matching(orders, incoming_order)

        # For large orders, use pro-rata allocation
        total_volume = sum(order.remaining_quantity for order in orders)
        if total_volume == 0:
            return orders

        # Sort by allocation percentage (simplified)
        weighted_orders = []
        for order in orders:
            allocation = order.remaining_quantity / total_volume
            weighted_orders.append((allocation, order.timestamp, order))

        weighted_orders.sort(key=lambda x: (-x[0], x[1]))  # Allocation desc, time asc
        return [order for _, _, order in weighted_orders]

    def should_encourage_liquidity(self) -> bool:
        """Check if current policy encourages liquidity provision"""
        return self.current_policy.liquidity_incentive

    def get_priority_queue_class(self):
        """Get appropriate priority queue class for current policy"""
        if self.current_policy.priority_rule == "PRICE_SIZE_TIME":
            return PriceSizeTimePriorityQueue
        else:
            return PriceTimePriorityQueue  # Default

    def validate_order_against_policy(self, order: Order) -> bool:
        """Validate order against current policy rules"""
        # Example validations based on policy
        if (
            self.current_policy.regime == MarketRegime.HIGH_VOLATILITY
            and order.quantity
            > self.current_policy.parameters.get("large_order_threshold", 100)
        ):
            # In high volatility, very large orders might be restricted
            return order.quantity <= 1000  # Example limit

        return True


# Global policy manager instance
policy_manager = PolicyManager()


def get_policy_manager() -> PolicyManager:
    """Get the global policy manager instance"""
    return policy_manager
