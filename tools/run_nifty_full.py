import time
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.data.nifty_loader import NiftyDataLoader
from src.core.matching_engine import AdaptiveMatchingEngine


def main():
    loader = NiftyDataLoader(data_directory="data")
    df = loader.load_intraday_data("NIFTY", 2008)
    if df is None or df.empty:
        print("No data loaded; aborting test.")
        return

    orders = loader.convert_to_orders(df, orders_per_record=2)
    print(f"Total generated orders: {len(orders)}")

    engine = AdaptiveMatchingEngine()

    N = len(orders)
    print(f"Processing {N} orders through AdaptiveMatchingEngine (FULL RUN)...")
    start = time.time()
    for o in orders:
        engine.process_order(o)
    dur = time.time() - start

    print(f"Processed {N} orders in {dur:.4f}s ({N/dur:.2f} orders/s)")
    print(f"Generated trades: {len(engine.trade_history)}")
    print(f"Metrics recorded: {len(engine.metrics_history)}")
    print(f"Regime changes: {engine.regime_change_count}")


if __name__ == "__main__":
    main()
