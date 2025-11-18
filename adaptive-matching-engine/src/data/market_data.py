"""
Market data utilities and historical data processing
"""

import csv
import json
from typing import List, Dict, Optional, Iterator
from datetime import datetime, timedelta
import random
import time

from ..core.order_types import Order, OrderSide, OrderType


class MarketDataProcessor:
    """Processes and generates market data for testing"""

    def __init__(self, symbol: str = "TEST"):
        self.symbol = symbol
        self.price_history = []
        self.volume_history = []
        self.spread_history = []

    def load_from_csv(self, filepath: str) -> List[Dict]:
        """Load market data from CSV file"""
        data = []
        try:
            with open(filepath, "r") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    data.append(row)

            print(f"Loaded {len(data)} market data records from {filepath}")
        except FileNotFoundError:
            print(f"CSV file not found: {filepath}")
        except Exception as e:
            print(f"Error loading CSV: {e}")

        return data

    def generate_historical_data(
        self, days: int = 30, ticks_per_day: int = 1000
    ) -> List[Dict]:
        """Generate synthetic historical market data"""
        data = []
        base_price = 100.0
        current_time = datetime.now() - timedelta(days=days)

        for day in range(days):
            daily_high = base_price * (1 + random.uniform(0.01, 0.05))
            daily_low = base_price * (1 - random.uniform(0.01, 0.05))

            for tick in range(ticks_per_day):
                # Generate price with some trend and noise
                trend = random.uniform(-0.001, 0.001)
                noise = random.gauss(0, 0.002)
                price_move = trend + noise

                base_price = base_price * (1 + price_move)
                base_price = max(daily_low, min(daily_high, base_price))

                # Generate volume (higher during market hours)
                is_market_hour = 300 <= tick < 600  # Simulated market hours
                volume = random.randint(100, 1000) * (2 if is_market_hour else 1)

                # Generate spread
                spread = random.uniform(0.001, 0.01) * base_price

                data_point = {
                    "timestamp": current_time.timestamp(),
                    "datetime": current_time.isoformat(),
                    "symbol": self.symbol,
                    "price": round(base_price, 4),
                    "volume": volume,
                    "spread": round(spread, 4),
                    "bid": round(base_price - spread / 2, 4),
                    "ask": round(base_price + spread / 2, 4),
                }

                data.append(data_point)
                current_time += timedelta(seconds=1)  # 1 second per tick

            # Move to next day
            current_time = current_time.replace(hour=9, minute=0, second=0) + timedelta(
                days=1
            )

        return data

    def convert_to_orders(
        self, market_data: List[Dict], orders_per_tick: int = 5
    ) -> List[Order]:
        """Convert market data to order stream"""
        orders = []
        order_id = 0

        for data_point in market_data:
            # Generate multiple orders per data point
            for _ in range(orders_per_tick):
                # Determine order side with some bias based on price movement
                if len(self.price_history) > 1:
                    price_trend = data_point["price"] - self.price_history[-1]
                    buy_probability = 0.5 + (price_trend / data_point["price"]) * 10
                    buy_probability = max(0.3, min(0.7, buy_probability))
                else:
                    buy_probability = 0.5

                side = (
                    OrderSide.BUY
                    if random.random() < buy_probability
                    else OrderSide.SELL
                )

                # Determine order type
                order_type = (
                    OrderType.MARKET if random.random() < 0.2 else OrderType.LIMIT
                )

                # Generate price and quantity
                if order_type == OrderType.LIMIT:
                    # Limit order near current price
                    price_variation = random.gauss(0, 0.001)
                    price = data_point["price"] * (1 + price_variation)
                else:
                    price = 0.0  # Market order

                # Realistic quantity distribution (power law)
                rand = random.random()
                if rand < 0.7:  # 70% small orders
                    quantity = random.randint(1, 10)
                elif rand < 0.9:  # 20% medium orders
                    quantity = random.randint(10, 100)
                else:  # 10% large orders
                    quantity = random.randint(100, 1000)

                order = Order(
                    order_id=f"HIST_{order_id}",
                    side=side,
                    price=price,
                    quantity=quantity,
                    timestamp=data_point["timestamp"],
                    order_type=order_type,
                )

                orders.append(order)
                order_id += 1

            # Update history
            self.price_history.append(data_point["price"])
            self.volume_history.append(data_point["volume"])
            self.spread_history.append(data_point["spread"])

        return orders

    def calculate_volatility(self, window: int = 50) -> List[float]:
        """Calculate rolling volatility from price history"""
        if len(self.price_history) < 2:
            return []

        volatilities = []
        for i in range(window, len(self.price_history)):
            window_prices = self.price_history[i - window : i]
            returns = []

            for j in range(1, len(window_prices)):
                if window_prices[j - 1] > 0:
                    ret = (window_prices[j] - window_prices[j - 1]) / window_prices[
                        j - 1
                    ]
                    returns.append(abs(ret))

            if returns:
                volatility = sum(returns) / len(returns)
                volatilities.append(volatility)
            else:
                volatilities.append(0.0)

        return volatilities

    def detect_regimes_from_history(self) -> List[Dict]:
        """Detect market regimes from historical data"""
        if len(self.price_history) < 100:
            return []

        regimes = []
        volatilities = self.calculate_volatility()
        avg_spread = (
            sum(self.spread_history) / len(self.spread_history)
            if self.spread_history
            else 0
        )

        for i, volatility in enumerate(volatilities):
            timestamp = time.time() - (len(volatilities) - i)  # Approximate timestamp

            if volatility > 0.02:
                regime = "HIGH_VOLATILITY"
            elif self.spread_history[i] > avg_spread * 1.5:
                regime = "ILLIQUID"
            else:
                regime = "NORMAL"

            regimes.append(
                {
                    "timestamp": timestamp,
                    "regime": regime,
                    "volatility": volatility,
                    "spread": (
                        self.spread_history[i] if i < len(self.spread_history) else 0
                    ),
                }
            )

        return regimes

    def save_orders_to_file(self, orders: List[Order], filename: str):
        """Save generated orders to JSON file"""
        serializable_orders = []
        for order in orders:
            serializable_orders.append(
                {
                    "order_id": order.order_id,
                    "side": order.side.value,
                    "price": order.price,
                    "quantity": order.quantity,
                    "timestamp": order.timestamp,
                    "order_type": order.order_type.value,
                    "filled_quantity": order.filled_quantity,
                }
            )

        with open(filename, "w") as f:
            json.dump(serializable_orders, f, indent=2)

        print(f"Saved {len(orders)} orders to {filename}")

    def load_orders_from_file(self, filename: str) -> List[Order]:
        """Load orders from JSON file"""
        try:
            with open(filename, "r") as f:
                data = json.load(f)

            orders = []
            for item in data:
                order = Order(
                    order_id=item["order_id"],
                    side=OrderSide(item["side"]),
                    price=item["price"],
                    quantity=item["quantity"],
                    timestamp=item["timestamp"],
                    order_type=OrderType(item["order_type"]),
                    filled_quantity=item.get("filled_quantity", 0),
                )
                orders.append(order)

            print(f"Loaded {len(orders)} orders from {filename}")
            return orders

        except FileNotFoundError:
            print(f"Orders file not found: {filename}")
            return []
        except Exception as e:
            print(f"Error loading orders: {e}")
            return []
