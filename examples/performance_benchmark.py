#!/usr/bin/env python3
"""
Performance benchmarking for the adaptive matching engine
"""

import time
import statistics
from typing import Dict, List
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.core.matching_engine import AdaptiveMatchingEngine, BaseMatchingEngine
from src.data.order_generator import OrderGenerator
from src.utils.performance import PerformanceMonitor
from src.core.order_types import Order


class BenchmarkRunner:
    """Runs comprehensive performance benchmarks"""

    def __init__(self):
        self.adaptive_engine = AdaptiveMatchingEngine()
        self.static_engine = BaseMatchingEngine()
        self.generator = OrderGenerator()
        self.results = {}

    def run_latency_benchmark(self, order_count: int = 10000) -> Dict:
        """Benchmark order processing latency"""
        print(f"Running latency benchmark with {order_count} orders...")

        orders = self.generator.generate_orders(order_count)

        # Test adaptive engine
        adaptive_monitor = PerformanceMonitor(self.adaptive_engine)
        adaptive_stats = adaptive_monitor.measure_throughput(orders)

        # Test static engine
        static_monitor = PerformanceMonitor(self.static_engine)
        static_stats = static_monitor.measure_throughput(orders)

        self.results["latency"] = {"adaptive": adaptive_stats, "static": static_stats}

        return self.results["latency"]

    def run_regime_transition_benchmark(self) -> Dict:
        """Benchmark regime transition performance"""
        print("Running regime transition benchmark...")

        # Generate orders that trigger regime changes
        orders = self.generator.generate_volatile_orders(500)
        normal_orders = self.generator.generate_orders(500)

        transition_times = []

        for i, order in enumerate(orders + normal_orders):
            start_time = time.perf_counter()
            self.adaptive_engine.process_order(order)
            processing_time = time.perf_counter() - start_time

            # Check if regime changed
            if i > 0 and self.adaptive_engine.regime_change_count > len(
                transition_times
            ):
                transition_times.append(processing_time)

        self.results["regime_transition"] = {
            "total_transitions": len(transition_times),
            "avg_transition_time_ms": (
                statistics.mean(transition_times) * 1000 if transition_times else 0
            ),
            "max_transition_time_ms": (
                max(transition_times) * 1000 if transition_times else 0
            ),
            "transition_times_ms": [t * 1000 for t in transition_times],
        }

        return self.results["regime_transition"]

    def run_memory_benchmark(self, order_count: int = 1000) -> Dict:
        """Benchmark memory usage under load"""
        import psutil
        import os

        print(f"Running memory benchmark with {order_count} orders...")

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        orders = self.generator.generate_orders(order_count)

        # Process orders
        for order in orders:
            self.adaptive_engine.process_order(order)

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        self.results["memory"] = {
            "initial_memory_mb": initial_memory,
            "final_memory_mb": final_memory,
            "memory_increase_mb": memory_increase,
            "memory_per_order_kb": (memory_increase * 1024) / order_count,
        }

        return self.results["memory"]

    def run_comprehensive_benchmark(self):
        """Run all benchmarks and generate report"""
        print("=== COMPREHENSIVE PERFORMANCE BENCHMARK ===\n")

        # Run all benchmarks
        latency_results = self.run_latency_benchmark(5000)
        transition_results = self.run_regime_transition_benchmark()
        memory_results = self.run_memory_benchmark(2000)

        # Generate comparison report
        self._generate_comparison_report(latency_results)

        print("\n=== BENCHMARK COMPLETE ===")
        return self.results

    def _generate_comparison_report(self, latency_results: Dict):
        """Generate comparison report between adaptive and static engines"""
        adaptive = latency_results["adaptive"]
        static = latency_results["static"]

        print("\n--- PERFORMANCE COMPARISON ---")
        print(f"{'Metric':<25} {'Adaptive':<12} {'Static':<12} {'Difference':<12}")
        print("-" * 65)

        metrics = [
            (
                "Throughput (ops/sec)",
                adaptive["throughput_ops"],
                static["throughput_ops"],
            ),
            ("Avg Latency (ms)", adaptive["avg_latency_ms"], static["avg_latency_ms"]),
            ("P95 Latency (ms)", adaptive["p95_latency_ms"], static["p95_latency_ms"]),
            ("P99 Latency (ms)", adaptive["p99_latency_ms"], static["p99_latency_ms"]),
        ]

        for name, adaptive_val, static_val in metrics:
            diff = adaptive_val - static_val
            diff_pct = (diff / static_val) * 100 if static_val != 0 else 0

            print(
                f"{name:<25} {adaptive_val:<12.2f} {static_val:<12.2f} {diff:+.2f} ({diff_pct:+.1f}%)"
            )

    def save_results(self, filename: str = "benchmark_results.json"):
        """Save benchmark results to file"""
        import json

        with open(filename, "w") as f:
            # Convert to serializable format
            serializable_results = {}
            for category, results in self.results.items():
                if isinstance(results, dict):
                    serializable_results[category] = {
                        k: (v if not isinstance(v, list) else [float(x) for x in v])
                        for k, v in results.items()
                    }

            json.dump(serializable_results, f, indent=2)

        print(f"Results saved to {filename}")


if __name__ == "__main__":
    benchmark = BenchmarkRunner()
    results = benchmark.run_comprehensive_benchmark()
    benchmark.save_results()
