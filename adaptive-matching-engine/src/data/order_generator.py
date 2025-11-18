import random
from typing import List
import time
from ..core.order_types import Order, OrderSide, OrderType


class OrderGenerator:
    """Generates realistic market orders for testing"""

    def __init__(self, symbol: str = "NIFTY", price_range: tuple = (18000.0, 19000.0)):
        """
        Initialize order generator for Indian markets.

        Args:
            symbol: Trading symbol (default: NIFTY for NSE)
            price_range: Price range in INR (default: typical NIFTY range)
        """
        self.symbol = symbol
        self.price_range = price_range
        self.last_price = (price_range[0] + price_range[1]) / 2
        self.order_id_counter = 0

    def generate_orders(
        self, count: int, market_order_ratio: float = 0.1, volatility: float = 0.01
    ) -> List[Order]:
        """Generate a batch of test orders"""
        orders = []

        for _ in range(count):
            # Determine order side (slightly biased to maintain balance)
            side = random.choice([OrderSide.BUY, OrderSide.SELL])

            # Determine order type
            if random.random() < market_order_ratio:
                order_type = OrderType.MARKET
                price = 0.0
            else:
                order_type = OrderType.LIMIT
                # Generate price with some volatility
                price_variation = random.gauss(0, volatility)
                price = self.last_price * (1 + price_variation)
                price = max(self.price_range[0], min(self.price_range[1], price))
                self.last_price = price

            # Generate quantity (power law distribution for realism)
            quantity = self._generate_realistic_quantity()

            order = Order(
                order_id=f"TEST_{self.order_id_counter}",
                side=side,
                price=price,
                quantity=quantity,
                timestamp=time.time(),
                order_type=order_type,
            )

            orders.append(order)
            self.order_id_counter += 1

        return orders

    def _generate_realistic_quantity(self) -> int:
        """Generate realistic order quantities (power law)"""
        # Power law distribution: many small orders, few large ones
        if random.random() < 0.8:  # 80% small orders
            return random.randint(1, 10)
        elif random.random() < 0.15:  # 15% medium orders
            return random.randint(10, 100)
        else:  # 5% large orders
            return random.randint(100, 1000)

    def generate_volatile_orders(self, count: int) -> List[Order]:
        """Generate orders that create volatile market conditions"""
        orders = []

        # Create large price movements
        for i in range(count):
            if i % 10 == 0:  # Every 10th order creates volatility
                # Large market order
                order = Order(
                    order_id=f"VOLATILE_{self.order_id_counter}",
                    side=random.choice([OrderSide.BUY, OrderSide.SELL]),
                    price=0.0,  # Market order
                    quantity=random.randint(500, 2000),
                    timestamp=time.time(),
                    order_type=OrderType.MARKET,
                )
            else:
                # Normal limit order with wider spread
                side = random.choice([OrderSide.BUY, OrderSide.SELL])
                price_variation = random.gauss(0, 0.05)  # High volatility
                price = self.last_price * (1 + price_variation)
                price = max(self.price_range[0], min(self.price_range[1], price))

                order = Order(
                    order_id=f"VOLATILE_{self.order_id_counter}",
                    side=side,
                    price=price,
                    quantity=random.randint(1, 100),
                    timestamp=time.time(),
                    order_type=OrderType.LIMIT,
                )

            orders.append(order)
            self.order_id_counter += 1

        return orders
