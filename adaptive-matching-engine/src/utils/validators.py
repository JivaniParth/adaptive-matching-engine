"""
Validation utilities for orders and market data
"""

from typing import Tuple, Optional, List
from ..core.order_types import Order, OrderType, OrderSide


class OrderValidator:
    """Validates orders before processing"""

    def __init__(self, config: Optional[dict] = None):
        self.config = config or self._get_default_config()

    def _get_default_config(self) -> dict:
        return {
            "min_price": 0.01,
            "max_price": 1000000.0,
            "min_quantity": 1,
            "max_quantity": 1000000,
            "allowed_order_types": [OrderType.LIMIT, OrderType.MARKET, OrderType.IOC],
            "price_precision": 4,
            "quantity_precision": 0,  # Integer quantities only
        }

    def validate_order(self, order: Order) -> Tuple[bool, Optional[str]]:
        """Validate an order, return (is_valid, error_message)"""

        # Check order type
        if not self._validate_order_type(order):
            return False, f"Invalid order type: {order.order_type}"

        # Check quantity
        if not self._validate_quantity(order):
            return False, f"Invalid quantity: {order.quantity}"

        # Check price for limit orders
        if order.order_type == OrderType.LIMIT:
            if not self._validate_price(order):
                return False, f"Invalid price: {order.price}"

        # Check timestamp
        if not self._validate_timestamp(order):
            return False, f"Invalid timestamp: {order.timestamp}"

        return True, None

    def _validate_order_type(self, order: Order) -> bool:
        """Validate order type"""
        return order.order_type in self.config["allowed_order_types"]

    def _validate_quantity(self, order: Order) -> bool:
        """Validate order quantity"""
        if order.quantity < self.config["min_quantity"]:
            return False
        if order.quantity > self.config["max_quantity"]:
            return False

        # Check precision
        if self.config["quantity_precision"] == 0:
            if not isinstance(order.quantity, int) or order.quantity != int(
                order.quantity
            ):
                return False

        return True

    def _validate_price(self, order: Order) -> bool:
        """Validate order price for limit orders"""
        if order.price < self.config["min_price"]:
            return False
        if order.price > self.config["max_price"]:
            return False

        # Check precision
        precision = self.config["price_precision"]
        rounded = round(order.price, precision)
        if abs(order.price - rounded) > 1e-10:
            return False

        return True

    def _validate_timestamp(self, order: Order) -> bool:
        """Validate order timestamp"""
        # Basic timestamp validation
        if order.timestamp <= 0:
            return False

        # Check if timestamp is not too far in the future (allow some tolerance)
        import time

        current_time = time.time()
        if order.timestamp > current_time + 3600:  # 1 hour in future
            return False

        return True

    def validate_batch_orders(
        self, orders: List[Order]
    ) -> List[Tuple[Order, bool, Optional[str]]]:
        """Validate a batch of orders"""
        results = []
        for order in orders:
            is_valid, error = self.validate_order(order)
            results.append((order, is_valid, error))
        return results


class MarketDataValidator:
    """Validates market data"""

    @staticmethod
    def validate_price(price: float) -> bool:
        """Validate price data"""
        return price > 0 and price < 1e9  # Reasonable bounds

    @staticmethod
    def validate_volume(volume: int) -> bool:
        """Validate volume data"""
        return volume >= 0 and volume < 1e9  # Reasonable bounds

    @staticmethod
    def validate_spread(spread: float) -> bool:
        """Validate spread data"""
        return spread >= 0 and spread < 1e6  # Reasonable bounds

    @staticmethod
    def validate_bid_ask(bid: float, ask: float) -> bool:
        """Validate bid-ask relationship"""
        if bid <= 0 or ask <= 0:
            return False
        return ask >= bid  # Ask should be >= bid


class RegimeValidator:
    """Validates regime detection parameters"""

    @staticmethod
    def validate_volatility_threshold(threshold: float) -> bool:
        """Validate volatility threshold"""
        return 0 <= threshold <= 1.0  # 0% to 100%

    @staticmethod
    def validate_imbalance_threshold(threshold: float) -> bool:
        """Validate imbalance threshold"""
        return 0 <= threshold <= 1.0  # 0% to 100%

    @staticmethod
    def validate_window_size(window: int) -> bool:
        """Validate detection window size"""
        return 1 <= window <= 10000  # Reasonable bounds

    @staticmethod
    def validate_config(config: dict) -> Tuple[bool, List[str]]:
        """Validate complete regime detection configuration"""
        errors = []

        # Check required fields
        required_fields = ["window_size", "volatility_threshold", "spread_threshold"]
        for field in required_fields:
            if field not in config:
                errors.append(f"Missing required field: {field}")

        # Validate values
        if "window_size" in config:
            if not RegimeValidator.validate_window_size(config["window_size"]):
                errors.append(f"Invalid window_size: {config['window_size']}")

        if "volatility_threshold" in config:
            if not RegimeValidator.validate_volatility_threshold(
                config["volatility_threshold"]
            ):
                errors.append(
                    f"Invalid volatility_threshold: {config['volatility_threshold']}"
                )

        if "imbalance_threshold" in config:
            if not RegimeValidator.validate_imbalance_threshold(
                config["imbalance_threshold"]
            ):
                errors.append(
                    f"Invalid imbalance_threshold: {config['imbalance_threshold']}"
                )

        return len(errors) == 0, errors


# Global validator instances
order_validator = OrderValidator()
market_data_validator = MarketDataValidator()
regime_validator = RegimeValidator()
