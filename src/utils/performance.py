import time
from typing import List, Dict, Any
import numpy as np
from ..core.order_types import Order, Trade
from ..core.matching_engine import AdaptiveMatchingEngine


class PerformanceMonitor:
    """Monitors and analyzes matching engine performance"""

    def __init__(self, engine: AdaptiveMatchingEngine):
        self.engine = engine
        self.performance_stats = {
            "order_processing_times": [],
            "throughput_measurements": [],
            "latency_percentiles": {},
            "regime_change_times": [],
            "memory_usage": [],
        }

    def measure_throughput(
        self, orders: List[Order], warmup: int = 100
    ) -> Dict[str, float]:
        """Measure throughput and latency for a batch of orders"""
        processing_times = []

        # Warmup
        for i in range(min(warmup, len(orders))):
            order = orders[i]
            start_time = time.perf_counter()
            self.engine.process_order(order)
            processing_times.append(time.perf_counter() - start_time)

        # Actual measurement
        processing_times.clear()
        start_batch_time = time.perf_counter()

        for order in orders[warmup:]:
            start_time = time.perf_counter()
            self.engine.process_order(order)
            processing_times.append(time.perf_counter() - start_time)

        total_batch_time = time.perf_counter() - start_batch_time
        orders_processed = len(orders) - warmup

        # Calculate statistics
        throughput = orders_processed / total_batch_time
        avg_latency = np.mean(processing_times) * 1000  # Convert to ms
        p95_latency = np.percentile(processing_times, 95) * 1000
        p99_latency = np.percentile(processing_times, 99) * 1000

        stats = {
            "throughput_ops": throughput,
            "avg_latency_ms": avg_latency,
            "p95_latency_ms": p95_latency,
            "p99_latency_ms": p99_latency,
            "total_orders": orders_processed,
            "total_time_sec": total_batch_time,
        }

        # Update performance stats
        self.performance_stats["order_processing_times"].extend(processing_times)
        self.performance_stats["throughput_measurements"].append(throughput)

        return stats

    def analyze_regime_effectiveness(self) -> Dict[str, Any]:
        """Analyze how effective regime changes are"""
        if not self.engine.metrics_history:
            return {}

        # Group metrics by regime
        regime_metrics = {}
        for metrics in self.engine.metrics_history:
            regime = metrics["regime"]
            if regime not in regime_metrics:
                regime_metrics[regime] = []
            regime_metrics[regime].append(metrics)

        # Calculate statistics per regime
        regime_stats = {}
        for regime, metrics_list in regime_metrics.items():
            spreads = [m["spread"] for m in metrics_list]
            volumes = [m["volume_executed"] for m in metrics_list]
            trades_per_order = [
                m["trades_generated"] for m in metrics_list if m["trades_generated"] > 0
            ]

            regime_stats[regime] = {
                "avg_spread": np.mean(spreads) if spreads else 0,
                "avg_volume_executed": np.mean(volumes) if volumes else 0,
                "avg_trades_per_order": (
                    np.mean(trades_per_order) if trades_per_order else 0
                ),
                "sample_count": len(metrics_list),
            }

        return regime_stats

    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        if not self.performance_stats["order_processing_times"]:
            return {}

        processing_times = self.performance_stats["order_processing_times"]

        report = {
            "latency_ms": {
                "mean": np.mean(processing_times) * 1000,
                "median": np.median(processing_times) * 1000,
                "p95": np.percentile(processing_times, 95) * 1000,
                "p99": np.percentile(processing_times, 99) * 1000,
                "min": np.min(processing_times) * 1000,
                "max": np.max(processing_times) * 1000,
            },
            "throughput": {
                "mean_ops": np.mean(self.performance_stats["throughput_measurements"]),
                "max_ops": np.max(self.performance_stats["throughput_measurements"]),
            },
            "regime_changes": {
                "total_changes": self.engine.regime_change_count,
                "change_times": self.performance_stats["regime_change_times"],
            },
            "engine_stats": {
                "total_orders_processed": len(self.engine.order_history),
                "total_trades_generated": len(self.engine.trade_history),
                "current_regime": self.engine.current_regime.value,
            },
        }

        # Add regime effectiveness analysis
        regime_effectiveness = self.analyze_regime_effectiveness()
        if regime_effectiveness:
            report["regime_effectiveness"] = regime_effectiveness

        return report

    def print_report(self):
        """Print formatted performance report"""
        report = self.generate_report()
        if not report:
            print("No performance data available")
            return

        print("=" * 50)
        print("PERFORMANCE REPORT")
        print("=" * 50)

        print(f"\nLATENCY (ms):")
        latency = report["latency_ms"]
        print(f"  Average: {latency['mean']:.4f} ms")
        print(f"  Median:  {latency['median']:.4f} ms")
        print(f"  P95:     {latency['p95']:.4f} ms")
        print(f"  P99:     {latency['p99']:.4f} ms")
        print(f"  Min:     {latency['min']:.4f} ms")
        print(f"  Max:     {latency['max']:.4f} ms")

        print(f"\nTHROUGHPUT:")
        throughput = report["throughput"]
        print(f"  Average: {throughput['mean_ops']:.2f} orders/sec")
        print(f"  Maximum: {throughput['max_ops']:.2f} orders/sec")

        print(f"\nENGINE STATISTICS:")
        stats = report["engine_stats"]
        print(f"  Total Orders: {stats['total_orders_processed']}")
        print(f"  Total Trades: {stats['total_trades_generated']}")
        print(f"  Regime Changes: {report['regime_changes']['total_changes']}")
        print(f"  Current Regime: {stats['current_regime']}")

        if "regime_effectiveness" in report:
            print(f"\nREGIME EFFECTIVENESS:")
            for regime, metrics in report["regime_effectiveness"].items():
                print(f"  {regime}:")
                print(f"    Avg Spread: {metrics['avg_spread']:.6f}")
                print(f"    Avg Volume: {metrics['avg_volume_executed']:.2f}")
                print(f"    Avg Trades/Order: {metrics['avg_trades_per_order']:.2f}")
                print(f"    Samples: {metrics['sample_count']}")
