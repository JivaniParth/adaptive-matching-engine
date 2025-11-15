import time
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.data.nifty_loader import NiftyDataLoader
from src.core.matching_engine import AdaptiveMatchingEngine, BaseMatchingEngine
from src.core.nse_matching_engine import NSEMatchingEngine


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
    print(f"\n{'='*70}")
    print("MATCHING ENGINE COMPARISON BENCHMARK")
    print(f"{'='*70}\n")

    # 1. Base/Static engine (simple price-time priority)
    print("Testing Base Matching Engine (Simple Price-Time)...")
    static_engine = BaseMatchingEngine()
    t_static = run_benchmark(orders, static_engine)
    print(f"  ✓ Completed in {t_static:.3f}s")
    print(f"  ✓ Throughput: {len(orders) / t_static:,.0f} orders/sec\n")

    # 2. NSE-style engine (with call auctions, circuit breakers, etc.)
    print("Testing NSE-Style Matching Engine (Full Features)...")
    nse_engine = NSEMatchingEngine(symbol="NIFTY")
    # Set reference price for circuit breakers
    if df is not None and not df.empty and "close" in df.columns:
        nse_engine.set_reference_price(float(df["close"].iloc[0]))
    t_nse = run_benchmark(orders, nse_engine)
    print(f"  ✓ Completed in {t_nse:.3f}s")
    print(f"  ✓ Throughput: {len(orders) / t_nse:,.0f} orders/sec")
    nse_stats = nse_engine.get_statistics()
    print(f"  ✓ Circuit breaker hits: {nse_stats['circuit_breaker_hits']}")
    print(f"  ✓ Total trades: {nse_stats['total_trades']}\n")

    # 3. Adaptive benchmark mode (no metrics/regime detection)
    print("Testing Adaptive Matching Engine (Benchmark Mode)...")
    adaptive_engine = AdaptiveMatchingEngine(benchmark_mode=True)
    t_adaptive = run_benchmark(orders, adaptive_engine)
    print(f"  ✓ Completed in {t_adaptive:.3f}s")
    print(f"  ✓ Throughput: {len(orders) / t_adaptive:,.0f} orders/sec\n")

    results = {
        "order_count": len(orders),
        "base_engine": {
            "time_seconds": t_static,
            "throughput_ops_per_sec": len(orders) / t_static if t_static > 0 else None,
        },
        "nse_engine": {
            "time_seconds": t_nse,
            "throughput_ops_per_sec": len(orders) / t_nse if t_nse > 0 else None,
            "circuit_breaker_hits": nse_stats["circuit_breaker_hits"],
            "total_trades": nse_stats["total_trades"],
        },
        "adaptive_engine": {
            "time_seconds": t_adaptive,
            "throughput_ops_per_sec": (
                len(orders) / t_adaptive if t_adaptive > 0 else None
            ),
        },
        "comparison": {
            "nse_vs_base_slowdown": t_nse / t_static if t_static > 0 else None,
            "adaptive_vs_base_slowdown": (
                t_adaptive / t_static if t_static > 0 else None
            ),
            "adaptive_vs_nse_speedup": t_nse / t_adaptive if t_adaptive > 0 else None,
        },
    }

    print(f"{'='*70}")
    print("COMPARISON SUMMARY")
    print(f"{'='*70}")
    print(
        f"\nBase Engine:     {results['base_engine']['throughput_ops_per_sec']:,.0f} orders/sec (baseline)"
    )
    print(
        f"NSE Engine:      {results['nse_engine']['throughput_ops_per_sec']:,.0f} orders/sec ({results['comparison']['nse_vs_base_slowdown']:.2f}x slower)"
    )
    print(
        f"Adaptive Engine: {results['adaptive_engine']['throughput_ops_per_sec']:,.0f} orders/sec ({results['comparison']['adaptive_vs_base_slowdown']:.2f}x slower)"
    )
    print(
        f"\nAdaptive vs NSE: {results['comparison']['adaptive_vs_nse_speedup']:.2f}x speedup\n"
    )

    print(json.dumps(results, indent=2))

    out_file = os.path.join("results", "bench_comparison.json")
    os.makedirs("results", exist_ok=True)
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n✅ Saved benchmark results to: {out_file}")


if __name__ == "__main__":
    main()
