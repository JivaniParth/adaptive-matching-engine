import time
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.data.nifty_loader import NiftyDataLoader
from src.core.matching_engine import AdaptiveMatchingEngine, BaseMatchingEngine


def run_benchmark(orders, engine):
    start = time.time()
    for o in orders:
        engine.process_order(o)
    dur = time.time() - start
    return dur


def main():
    loader = NiftyDataLoader(data_directory="data")
    df = loader.load_intraday_data("NIFTY", 2008)
    if df is None or df.empty:
        print("No data loaded; aborting benchmark.")
        return

    # Stream orders to avoid building full list
    stream = loader.convert_to_orders_stream(df, orders_per_record=1)

    # Materialize a moderate chunk for consistent measurement
    orders = list(stream)
    print(f"Generated {len(orders)} orders for benchmark")

    # Static engine
    static_engine = BaseMatchingEngine()
    t_static = run_benchmark(orders, static_engine)

    # Adaptive benchmark mode (no metrics/regime detection)
    adaptive_engine = AdaptiveMatchingEngine(benchmark_mode=True)
    t_adaptive = run_benchmark(orders, adaptive_engine)

    results = {
        "order_count": len(orders),
        "static_seconds": t_static,
        "adaptive_seconds": t_adaptive,
        "static_ops_per_sec": len(orders) / t_static if t_static > 0 else None,
        "adaptive_ops_per_sec": len(orders) / t_adaptive if t_adaptive > 0 else None,
    }

    print(json.dumps(results, indent=2))

    out_file = os.path.join("results", "bench_comparison.json")
    os.makedirs("results", exist_ok=True)
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)

    print(f"Saved benchmark results to: {out_file}")


if __name__ == "__main__":
    main()
