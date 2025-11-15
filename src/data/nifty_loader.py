"""
Nifty and Bank Nifty data loader for the adaptive matching engine
"""

import pandas as pd
import numpy as np
from typing import List, Optional, Dict
import os
from datetime import datetime, timedelta
from ..core.order_types import Order, OrderSide, OrderType


class NiftyDataLoader:
    """Loads and processes Nifty/Bank Nifty intraday data"""

    def __init__(self, data_directory: str = "data"):
        self.data_directory = data_directory
        self.supported_symbols = ["NIFTY", "BANKNIFTY"]

    def load_intraday_data(
        self, symbol: str, year: int, file_format: str = "csv"
    ) -> Optional[pd.DataFrame]:
        """Load intraday data for specific symbol and year"""
        filename = f"{symbol}_{year}_intraday.{file_format}"
        filepath = os.path.join(self.data_directory, filename)

        try:
            if file_format == "csv":
                df = pd.read_csv(filepath)
            elif file_format == "parquet":
                df = pd.read_parquet(filepath)
            else:
                raise ValueError(f"Unsupported file format: {file_format}")

            return self._preprocess_data(df, symbol)

        except FileNotFoundError:
            print(f"Data file not found: {filepath}")
            return None
        except Exception as e:
            print(f"Error loading data: {e}")
            return None

    def _preprocess_data(self, df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """Preprocess the raw Nifty data with flexible column mapping"""
        # Make a copy to avoid modifying the original
        df = df.copy()

        # Convert all column names to lowercase for consistency
        df.columns = [col.lower().strip() for col in df.columns]

        # Flexible column mapping for different Nifty data formats
        column_mapping = {
            # Timestamp columns
            "timestamp": "timestamp",
            "time": "timestamp",
            "datetime": "timestamp",
            "date": "timestamp",
            "datetimeindex": "timestamp",
            # Price columns
            "price": "price",
            "close": "price",
            "last": "price",
            "lastprice": "price",
            "ltp": "price",
            "tradeprice": "price",
            # Volume columns
            "volume": "volume",
            "quantity": "volume",
            "tradedquantity": "volume",
            "qty": "volume",
            "size": "volume",
            # Bid/Ask columns
            "bid": "bid",
            "bidprice": "bid",
            "bid_price": "bid",
            "ask": "ask",
            "askprice": "ask",
            "ask_price": "ask",
            "offer": "ask",
            "bidqty": "bid_qty",
            "bid_quantity": "bid_qty",
            "bidsize": "bid_qty",
            "askqty": "ask_qty",
            "ask_quantity": "ask_qty",
            "asksize": "ask_qty",
        }

        # Apply column mapping
        for old_col, new_col in column_mapping.items():
            if old_col in df.columns and new_col not in df.columns:
                df[new_col] = df[old_col]
                if old_col != new_col:
                    df = df.drop(columns=[old_col])

        # Ensure we have essential columns
        if "timestamp" not in df.columns:
            # Prefer combining separate date + time columns when both exist
            if "date" in df.columns and "time" in df.columns:
                try:
                    df["timestamp"] = pd.to_datetime(
                        df["date"].astype(str).str.strip()
                        + " "
                        + df["time"].astype(str).str.strip(),
                        errors="coerce",
                        infer_datetime_format=True,
                    )
                    print("  Using 'date' + 'time' as timestamp column")
                except Exception:
                    df["timestamp"] = pd.NaT

            # Fallback: look for any datetime-like column
            if "timestamp" not in df.columns or df["timestamp"].isna().all():
                datetime_cols = [
                    col
                    for col in df.columns
                    if any(x in col for x in ["time", "date", "datetime"])
                ]
                if datetime_cols:
                    df["timestamp"] = df[datetime_cols[0]]
                    print(f"  Using '{datetime_cols[0]}' as timestamp column")
                else:
                    # Create a synthetic timestamp if none exists
                    df["timestamp"] = pd.date_range(
                        start="2000-01-01", periods=len(df), freq="1min"
                    )
                    print("  ⚠️ No timestamp column found, using synthetic timestamps")

        if "price" not in df.columns:
            # Try to find price columns
            price_cols = [
                col
                for col in df.columns
                if any(x in col for x in ["price", "close", "last", "ltp"])
            ]
            if price_cols:
                df["price"] = df[price_cols[0]]
                print(f"  Using '{price_cols[0]}' as price column")
            else:
                raise ValueError("No price column found in data")

        # Convert timestamp to datetime safely; fill unparsable rows with sequential timestamps
        df["timestamp"] = pd.to_datetime(
            df["timestamp"], errors="coerce", infer_datetime_format=True
        )
        if df["timestamp"].isna().any():
            # Replace NaT values with a sequential range anchored at the first valid timestamp or a default
            valid_ts = df["timestamp"].dropna()
            if len(valid_ts) > 0:
                start = valid_ts.iloc[0]
            else:
                start = pd.Timestamp("2000-01-01")

            na_mask = df["timestamp"].isna()
            replacement = pd.date_range(start=start, periods=na_mask.sum(), freq="1min")
            df.loc[na_mask, "timestamp"] = replacement.values

        df = df.sort_values("timestamp").reset_index(drop=True)

        # Add symbol
        df["symbol"] = symbol

        # Calculate mid price and spread
        if "bid" in df.columns and "ask" in df.columns:
            df["mid_price"] = (df["bid"] + df["ask"]) / 2
            df["spread"] = df["ask"] - df["bid"]
        else:
            df["mid_price"] = df["price"]
            # Estimate spread (typical Nifty spread is 0.05-0.1%)
            df["spread"] = df["mid_price"] * 0.0005

        # Ensure volume column exists
        if "volume" not in df.columns:
            # Create a realistic synthetic volume when none exists:
            # - Use absolute pct change of price as proxy for activity
            # - Scale to an integer and ensure a sensible minimum
            try:
                pct = df["price"].pct_change().abs().fillna(0)
                scaled = (pct * 1_000_000).astype(int)
                # Ensure a minimum volume to avoid zeros
                df["volume"] = scaled.clip(lower=100)
            except Exception:
                # Fallback to random volumes if price-based method fails
                df["volume"] = np.random.randint(100, 10000, size=len(df))

            print(
                "  ⚠️ No volume column found, created synthetic volume from price changes"
            )

        print(f"  Final columns: {list(df.columns)}")
        return df

    def load_multiple_years(
        self, symbol: str, start_year: int, end_year: int
    ) -> pd.DataFrame:
        """Load data for multiple years and concatenate"""
        all_data = []

        for year in range(start_year, end_year + 1):
            print(f"  Loading {symbol} {year}...")
            data = self.load_intraday_data(symbol, year)
            if data is not None and len(data) > 0:
                all_data.append(data)

        if all_data:
            combined_data = pd.concat(all_data, ignore_index=True)
            print(
                f"✅ Combined {len(all_data)} years of {symbol} data, total {len(combined_data)} records"
            )
            return combined_data
        else:
            print(f"❌ No data found for {symbol} from {start_year} to {end_year}")
            return pd.DataFrame()

    def analyze_market_regimes(
        self, df: pd.DataFrame, window: int = 100
    ) -> pd.DataFrame:
        """Analyze market regimes in the historical data"""
        if len(df) < window:
            return pd.DataFrame()

        results = []

        for i in range(window, len(df)):
            window_data = df.iloc[i - window : i]

            # Calculate metrics for regime detection
            volatility = window_data["mid_price"].pct_change().std() * np.sqrt(
                252
            )  # Annualized
            avg_spread = (
                window_data["spread"].mean()
                if "spread" in window_data
                else window_data["mid_price"].mean() * 0.0005
            )

            # Volume analysis (if available)
            if "volume" in window_data.columns:
                volume_imbalance = self._calculate_volume_imbalance(window_data)
            else:
                volume_imbalance = 0

            # Determine regime based on metrics
            if volatility > 0.25:  # 25% annualized volatility threshold
                regime = "HIGH_VOLATILITY"
            elif (
                avg_spread > window_data["mid_price"].mean() * 0.001
            ):  # 0.1% spread threshold
                regime = "ILLIQUID"
            elif abs(volume_imbalance) > 0.6:  # 60% imbalance threshold
                regime = "DIRECTIONAL"
            else:
                regime = "NORMAL"

            results.append(
                {
                    "timestamp": window_data.iloc[-1]["timestamp"],
                    "volatility": volatility,
                    "spread": avg_spread,
                    "volume_imbalance": volume_imbalance,
                    "detected_regime": regime,
                    "price": window_data.iloc[-1]["mid_price"],
                }
            )

        return pd.DataFrame(results)

    def _calculate_volume_imbalance(self, df: pd.DataFrame) -> float:
        """Calculate volume imbalance (simplified)"""
        # This is a simplified approach - real implementation would need bid/ask volumes
        if "volume" not in df.columns:
            return 0

        # Use price movements as proxy for buy/sell pressure
        price_changes = df["mid_price"].pct_change().dropna()
        buy_pressure = (
            (price_changes > 0).sum() / len(price_changes)
            if len(price_changes) > 0
            else 0.5
        )

        return abs(buy_pressure - 0.5) * 2  # Normalize to 0-1 range

    def convert_to_orders(
        self,
        df: pd.DataFrame,
        orders_per_record: int = 3,
        market_order_ratio: float = 0.1,
    ) -> List[Order]:
        """Convert market data to order stream for simulation"""
        orders = []

        if len(df) == 0:
            return orders

        # Use mid price as reference
        price_column = "mid_price" if "mid_price" in df.columns else "price"

        print(f"Converting {len(df)} records to orders...")

        for idx, row in df.iterrows():
            # Handle timestamp - convert to timestamp if it's a datetime object
            if hasattr(row["timestamp"], "timestamp"):
                base_timestamp = row["timestamp"].timestamp()
            else:
                base_timestamp = (
                    float(row["timestamp"])
                    if isinstance(row["timestamp"], (int, float))
                    else 0.0
                )

            base_price = row[price_column]
            base_volume = row.get("volume", 100)

            # Generate multiple orders per market data record
            for i in range(orders_per_record):
                # Determine order side with some bias based on price movement
                if idx > 0:
                    try:
                        prev_price = df.iloc[idx - 1][price_column]
                        price_change = (
                            (base_price - prev_price) / prev_price
                            if prev_price > 0
                            else 0
                        )
                        buy_probability = 0.5 - (
                            price_change * 10
                        )  # Adjust sensitivity
                        buy_probability = max(0.1, min(0.9, buy_probability))
                    except:
                        buy_probability = 0.5
                else:
                    buy_probability = 0.5

                side = (
                    OrderSide.BUY
                    if np.random.random() < buy_probability
                    else OrderSide.SELL
                )

                # Determine order type
                order_type = (
                    OrderType.MARKET
                    if np.random.random() < market_order_ratio
                    else OrderType.LIMIT
                )

                # Generate price and quantity
                if order_type == OrderType.LIMIT:
                    # Add some spread around the mid price
                    price_offset = np.random.normal(0, 0.001)
                    price = base_price * (1 + price_offset)
                else:
                    price = 0.0  # Market order

                # Generate realistic quantity (power law distribution)
                rand = np.random.random()
                if rand < 0.7:  # 70% small orders
                    quantity = max(
                        1, int(base_volume * 0.001 * np.random.uniform(0.1, 0.5))
                    )
                elif rand < 0.9:  # 20% medium orders
                    quantity = max(
                        1, int(base_volume * 0.001 * np.random.uniform(0.5, 2.0))
                    )
                else:  # 10% large orders
                    quantity = max(
                        1, int(base_volume * 0.001 * np.random.uniform(2.0, 10.0))
                    )

                # Create order with realistic timestamp
                order_timestamp = base_timestamp + (i * 0.001)

                order = Order(
                    order_id=f"{row.get('symbol', 'NIFTY')}_{idx}_{i}",
                    side=side,
                    price=price,
                    quantity=quantity,
                    timestamp=order_timestamp,
                    order_type=order_type,
                )

                orders.append(order)

        print(f"✅ Generated {len(orders)} orders from {len(df)} market records")
        return orders

    def convert_to_orders_stream(
        self,
        df: pd.DataFrame,
        orders_per_record: int = 3,
        market_order_ratio: float = 0.1,
    ):
        """Stream orders generated from market data records (generator).

        Yields Order objects instead of building the full list in memory.
        """
        if len(df) == 0:
            return

        price_column = "mid_price" if "mid_price" in df.columns else "price"

        for idx, row in df.iterrows():
            # Handle timestamp
            if hasattr(row["timestamp"], "timestamp"):
                base_timestamp = row["timestamp"].timestamp()
            else:
                base_timestamp = (
                    float(row["timestamp"])
                    if isinstance(row["timestamp"], (int, float))
                    else 0.0
                )

            base_price = row[price_column]
            base_volume = row.get("volume", 100)

            for i in range(orders_per_record):
                # Determine order side
                if idx > 0:
                    try:
                        prev_price = df.iloc[idx - 1][price_column]
                        price_change = (
                            (base_price - prev_price) / prev_price
                            if prev_price > 0
                            else 0
                        )
                        buy_probability = 0.5 - (price_change * 10)
                        buy_probability = max(0.1, min(0.9, buy_probability))
                    except Exception:
                        buy_probability = 0.5
                else:
                    buy_probability = 0.5

                side = (
                    OrderSide.BUY
                    if np.random.random() < buy_probability
                    else OrderSide.SELL
                )

                order_type = (
                    OrderType.MARKET
                    if np.random.random() < market_order_ratio
                    else OrderType.LIMIT
                )

                if order_type == OrderType.LIMIT:
                    price_offset = np.random.normal(0, 0.001)
                    price = base_price * (1 + price_offset)
                else:
                    price = 0.0

                rand = np.random.random()
                if rand < 0.7:
                    quantity = max(
                        1, int(base_volume * 0.001 * np.random.uniform(0.1, 0.5))
                    )
                elif rand < 0.9:
                    quantity = max(
                        1, int(base_volume * 0.001 * np.random.uniform(0.5, 2.0))
                    )
                else:
                    quantity = max(
                        1, int(base_volume * 0.001 * np.random.uniform(2.0, 10.0))
                    )

                order_timestamp = base_timestamp + (i * 0.001)

                order = Order(
                    order_id=f"{row.get('symbol', 'NIFTY')}_{idx}_{i}",
                    side=side,
                    price=price,
                    quantity=quantity,
                    timestamp=order_timestamp,
                    order_type=order_type,
                )

                yield order


# Global instance
nifty_loader = NiftyDataLoader()
