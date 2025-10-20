from dataclasses import dataclass
from enum import Enum
from typing import Optional
import time
import uuid


class OrderType(Enum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"
    IOC = "IOC"  # Immediate-or-Cancel


class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"


class MarketRegime(Enum):
    NORMAL = "NORMAL"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    ILLIQUID = "ILLIQUID"
    DIRECTIONAL = "DIRECTIONAL"
    HIGH_FREQUENCY = "HIGH_FREQUENCY"


@dataclass
class Order:
    order_id: str
    side: OrderSide
    price: float
    quantity: int
    timestamp: float
    order_type: OrderType = OrderType.LIMIT
    filled_quantity: int = 0

    def __post_init__(self):
        if self.quantity <= 0:
            raise ValueError("Order quantity must be positive")
        if self.price <= 0 and self.order_type == OrderType.LIMIT:
            raise ValueError("Limit order price must be positive")

    @property
    def remaining_quantity(self) -> int:
        return self.quantity - self.filled_quantity

    @classmethod
    def create_limit_order(
        cls, side: OrderSide, price: float, quantity: int
    ) -> "Order":
        return cls(
            order_id=str(uuid.uuid4()),
            side=side,
            price=price,
            quantity=quantity,
            timestamp=time.time(),
            order_type=OrderType.LIMIT,
        )

    @classmethod
    def create_market_order(cls, side: OrderSide, quantity: int) -> "Order":
        return cls(
            order_id=str(uuid.uuid4()),
            side=side,
            price=0.0,  # Market orders don't have price
            quantity=quantity,
            timestamp=time.time(),
            order_type=OrderType.MARKET,
        )


@dataclass
class Trade:
    trade_id: str
    buy_order_id: str
    sell_order_id: str
    price: float
    quantity: int
    timestamp: float

    @classmethod
    def create_trade(
        cls, buy_order: Order, sell_order: Order, quantity: int
    ) -> "Trade":
        """Create trade with proper price determination"""
        # FIX: Use the limit order's price for market orders
        if buy_order.order_type == OrderType.MARKET:
            # Buy is market order, use sell order's limit price
            trade_price = sell_order.price
        elif sell_order.order_type == OrderType.MARKET:
            # Sell is market order, use buy order's limit price
            trade_price = buy_order.price
        else:
            # Both are limit orders, use the resting order's price (convention: use ask price)
            trade_price = sell_order.price

        return cls(
            trade_id=str(uuid.uuid4()),
            buy_order_id=buy_order.order_id,
            sell_order_id=sell_order.order_id,
            price=trade_price,
            quantity=quantity,
            timestamp=time.time(),
        )


@dataclass
class OrderBookSnapshot:
    timestamp: float
    bids: list[tuple[float, int]]  # (price, total_quantity)
    asks: list[tuple[float, int]]
    spread: float

    def get_mid_price(self) -> float:
        if not self.bids or not self.asks:
            return 0.0
        return (self.bids[0][0] + self.asks[0][0]) / 2
