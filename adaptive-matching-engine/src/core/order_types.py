from dataclasses import dataclass
from enum import Enum
from typing import Optional
import time
import uuid


class OrderType(Enum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"
    IOC = "IOC"  # Immediate-or-Cancel
    STOP_LOSS = "STOP_LOSS"  # Stop-Loss Limit
    STOP_LOSS_MARKET = "STOP_LOSS_MARKET"  # Stop-Loss Market (SL-M)
    FOK = "FOK"  # Fill-or-Kill
    ICEBERG = "ICEBERG"  # Hidden/Iceberg order


class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderValidity(Enum):
    """Order validity/time-in-force"""

    DAY = "DAY"  # Valid for the trading day
    IOC = "IOC"  # Immediate-or-Cancel (already in OrderType, kept for compatibility)
    GTC = "GTC"  # Good-Till-Cancelled
    GTD = "GTD"  # Good-Till-Date


class TradingPhase(Enum):
    """NSE trading phases"""

    PRE_OPEN = "PRE_OPEN"  # Call auction (9:00-9:08 AM)
    OPENING = "OPENING"  # Opening auction match (9:08-9:15 AM)
    CONTINUOUS = "CONTINUOUS"  # Normal trading (9:15 AM - 3:20 PM)
    CLOSING = "CLOSING"  # Closing auction (3:20-3:30 PM)
    POST_CLOSE = "POST_CLOSE"  # After market close
    HALTED = "HALTED"  # Trading halted (circuit breaker)


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
    # NSE-specific fields
    stop_price: Optional[float] = None  # For stop-loss orders
    disclosed_quantity: Optional[int] = None  # For iceberg orders
    validity: OrderValidity = OrderValidity.DAY
    expiry_time: Optional[float] = None  # For GTD orders
    is_triggered: bool = False  # For stop-loss orders

    def __post_init__(self):
        if self.quantity <= 0:
            raise ValueError("Order quantity must be positive")
        if self.price <= 0 and self.order_type in [
            OrderType.LIMIT,
            OrderType.STOP_LOSS,
        ]:
            raise ValueError("Limit/Stop-Loss order price must be positive")
        if self.order_type in [OrderType.STOP_LOSS, OrderType.STOP_LOSS_MARKET]:
            if self.stop_price is None or self.stop_price <= 0:
                raise ValueError("Stop-Loss orders require valid stop_price")
        if self.order_type == OrderType.ICEBERG:
            if self.disclosed_quantity is None or self.disclosed_quantity <= 0:
                raise ValueError("Iceberg orders require disclosed_quantity")

    @property
    def remaining_quantity(self) -> int:
        return self.quantity - self.filled_quantity

    @property
    def visible_quantity(self) -> int:
        """Returns the quantity visible in order book (for iceberg orders)"""
        if self.order_type == OrderType.ICEBERG and self.disclosed_quantity:
            return min(self.disclosed_quantity, self.remaining_quantity)
        return self.remaining_quantity

    def is_expired(self, current_time: float) -> bool:
        """Check if order has expired"""
        if self.validity == OrderValidity.DAY:
            # Simple day check - in production would check market hours
            return False
        if self.validity == OrderValidity.GTD and self.expiry_time:
            return current_time > self.expiry_time
        return False

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
