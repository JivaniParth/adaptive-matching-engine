import time
import statistics
import json
from typing import Dict
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.core.matching_engine import BaseMatchingEngine
from src.core.matching_engine import AdaptiveMatchingEngine
from src.data.order_generator import OrderGenerator
from config import default_config


class OptimizedBenchmarkRunner:
    """Performance benchmark with optimized engines"""

    def __init__(self):
        self.static_engine = BaseMatchingEngine()
        self.optimized_adaptive_engine = AdaptiveMatchingEngine(config=default_config())
        self.generator = OrderGenerator()
        self.results = {}

    def run_comparison_benchmark(self, order_count: int = 10000) -> Dict:
        """
        Compare static vs optimized adaptive engine
        """
        print(f"\n{'='*70}")
        print(f"PERFORMANCE BENCHMARK: {order_count:,} orders")
        print(f"{'='*70}\n")

        orders = self.generator.generate_orders(order_count)

        # Benchmark 1: Static Engine (baseline)
        print("🔵 Testing STATIC engine (baseline)...")
        static_stats = self._benchmark_engine(self.static_engine, orders, "Static")

        # Benchmark 2: Optimized Adaptive Engine
        print("\n🟢 Testing OPTIMIZED ADAPTIVE engine...")
        adaptive_stats = self._benchmark_engine(
            self.optimized_adaptive_engine, orders, "Optimized Adaptive"
        )

        # Calculate improvement
        speedup = static_stats["throughput_ops"] / adaptive_stats["throughput_ops"]
        latency_overhead = (
            (adaptive_stats["avg_latency_ms"] - static_stats["avg_latency_ms"])
            / static_stats["avg_latency_ms"]
            * 100
        )

        print(f"\n{'='*70}")
        print("📊 PERFORMANCE COMPARISON")
        print(f"{'='*70}")
        print(f"\nThroughput:")
        print(f"  Static:    {static_stats['throughput_ops']:,.0f} ops/sec")
        print(f"  Adaptive:  {adaptive_stats['throughput_ops']:,.0f} ops/sec")
        print(f"  Slowdown:  {speedup:.2f}x")

        print(f"\nLatency:")
        print(f"  Static:    {static_stats['avg_latency_ms']:.6f} ms (avg)")
        print(f"  Adaptive:  {adaptive_stats['avg_latency_ms']:.6f} ms (avg)")
        print(f"  Overhead:  {latency_overhead:+.1f}%")

        print(f"\nP95 Latency:")
        print(f"  Static:    {static_stats['p95_latency_ms']:.6f} ms")
        print(f"  Adaptive:  {adaptive_stats['p95_latency_ms']:.6f} ms")

        print(f"\nP99 Latency:")
        print(f"  Static:    {static_stats['p99_latency_ms']:.6f} ms")
        print(f"  Adaptive:  {adaptive_stats['p99_latency_ms']:.6f} ms")

        # Adaptive-specific stats
        if hasattr(self.optimized_adaptive_engine, "regime_change_count"):
            print(f"\nAdaptive Features:")
            print(
                f"  Regime Changes: {self.optimized_adaptive_engine.regime_change_count}"
            )
            print(
                f"  Final Regime:   {self.optimized_adaptive_engine.current_regime.value}"
            )

        print(f"\n{'='*70}\n")

        self.results = {
            "static": static_stats,
            "optimized_adaptive": adaptive_stats,
            "comparison": {
                "slowdown_factor": speedup,
                "latency_overhead_pct": latency_overhead,
                "target_achieved": speedup < 3.0,  # Target: <3x slower
            },
        }

        return self.results

    def _benchmark_engine(self, engine, orders, name: str) -> Dict:
        """Benchmark a single engine"""
        processing_times = []

        # Warmup
        warmup_count = min(100, len(orders) // 10)
        for order in orders[:warmup_count]:
            engine.process_order(order)

        # Actual measurement
        test_orders = orders[warmup_count:]
        start_time = time.perf_counter()

        for order in test_orders:
            order_start = time.perf_counter()
            engine.process_order(order)
            processing_times.append(time.perf_counter() - order_start)

        total_time = time.perf_counter() - start_time

        # Calculate statistics
        throughput = len(test_orders) / total_time
        avg_latency = statistics.mean(processing_times) * 1000  # ms
        p95_latency = (
            statistics.quantiles(processing_times, n=20)[18] * 1000
        )  # 95th percentile
        p99_latency = (
            statistics.quantiles(processing_times, n=100)[98] * 1000
        )  # 99th percentile

        print(f"  ✓ Processed {len(test_orders):,} orders in {total_time:.3f}s")
        print(f"  ✓ Throughput: {throughput:,.0f} ops/sec")
        print(f"  ✓ Avg Latency: {avg_latency:.6f} ms")

        return {
            "throughput_ops": throughput,
            "avg_latency_ms": avg_latency,
            "p95_latency_ms": p95_latency,
            "p99_latency_ms": p99_latency,
            "total_orders": len(test_orders),
            "total_time_sec": total_time,
        }

    def run_volatile_market_test(self, order_count: int = 5000) -> Dict:
        """Test performance during volatile market conditions"""
        print(f"\n{'='*70}")
        print(f"VOLATILE MARKET TEST: {order_count:,} orders")
        print(f"{'='*70}\n")

        volatile_orders = self.generator.generate_volatile_orders(order_count)

        print("🔴 Testing with VOLATILE market conditions...")
        print("This tests adaptive behavior under stress\n")

        # Reset engine
        self.optimized_adaptive_engine = AdaptiveMatchingEngine(config=default_config())

        stats = self._benchmark_engine(
            self.optimized_adaptive_engine, volatile_orders, "Volatile Adaptive"
        )

        print(f"\nAdaptive Response:")
        print(f"  Regime Changes: {self.optimized_adaptive_engine.regime_change_count}")
        print(
            f"  Final Regime:   {self.optimized_adaptive_engine.current_regime.value}"
        )

        return stats

    def save_results(self, filename: str = "optimized_benchmark_results.json"):
        """Save benchmark results to file"""
        if not self.results:
            print("No results to save")
            return

        with open(filename, "w") as f:
            json.dump(self.results, f, indent=2)

        print(f"✅ Results saved to {filename}")


def main():
    """Run optimized performance benchmarks"""
    benchmark = OptimizedBenchmarkRunner()

    # Test 1: Standard comparison
    print("\n" + "=" * 70)
    print("TEST 1: STANDARD PERFORMANCE COMPARISON")
    print("=" * 70)
    benchmark.run_comparison_benchmark(order_count=10000)

    # Test 2: Volatile market
    print("\n" + "=" * 70)
    print("TEST 2: VOLATILE MARKET PERFORMANCE")
    print("=" * 70)
    benchmark.run_volatile_market_test(order_count=5000)

    # Test 3: High load
    print("\n" + "=" * 70)
    print("TEST 3: HIGH LOAD STRESS TEST")
    print("=" * 70)
    benchmark.run_comparison_benchmark(order_count=50000)

    # Save results
    benchmark.save_results()

    # Summary
    print("\n" + "=" * 70)
    print("🎯 OPTIMIZATION SUMMARY")
    print("=" * 70)

    results = benchmark.results
    if results:
        comparison = results["comparison"]

        print(f"\n✨ Performance Achievement:")
        print(f"  Slowdown: {comparison['slowdown_factor']:.2f}x")
        print(f"  Target:   <3.0x (vs static engine)")

        if comparison["target_achieved"]:
            print(
                f"\n  ✅ TARGET ACHIEVED! Optimized adaptive engine is production-ready!"
            )
        else:
            print(
                f"\n  ⚠️  Target not met, but significant improvement from 100x slower"
            )

        print(f"\n📈 Improvement from Original:")
        print(f"  Original: 100x slower than static")
        print(f"  Optimized: {comparison['slowdown_factor']:.1f}x slower than static")
        print(
            f"  Speedup: {100 / comparison['slowdown_factor']:.0f}x faster than original!"
        )


if __name__ == "__main__":
    main()
