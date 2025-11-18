#!/usr/bin/env python3
"""
Fast Nifty analysis with optimized performance
"""

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.core.matching_engine import AdaptiveMatchingEngine, BaseMatchingEngine
from src.core.order_types import Order, OrderSide, OrderType
from src.utils.performance import PerformanceMonitor
from src.data.nifty_loader import NiftyDataLoader
import time
from datetime import datetime


class FastNiftyAnalysis:
    """Optimized analysis for faster results"""

    def __init__(self):
        self.loader = NiftyDataLoader()

    def run_quick_comparison(self, symbol: str, year: int, sample_size: int = 1000):
        """Run quick comparison with limited data"""
        print(f"🚀 FAST ANALYSIS: {symbol} {year} (Sample: {sample_size} orders)")
        print("=" * 60)

        # Load single year data
        data = self.loader.load_intraday_data(symbol, year)
        if data is None or len(data) == 0:
            print(f"❌ No data for {symbol} {year}")
            return

        # Use smaller sample
        if len(data) > sample_size:
            data = data.sample(sample_size)

        # Convert to orders
        orders = self.loader.convert_to_orders(data, orders_per_record=1)

        if len(orders) == 0:
            print("❌ No orders generated")
            return

        print(f"📊 Testing with {len(orders)} orders")

        # Test Adaptive Engine
        adaptive_engine = AdaptiveMatchingEngine()
        adaptive_monitor = PerformanceMonitor(adaptive_engine)

        print("🔄 Testing ADAPTIVE engine...")
        adaptive_start = time.time()
        adaptive_trades = []

        for i, order in enumerate(orders):
            trades = adaptive_engine.process_order(order)
            adaptive_trades.extend(trades)

            # Progress every 100 orders
            if (i + 1) % 100 == 0:
                elapsed = time.time() - adaptive_start
                print(f"  Processed {i+1}/{len(orders)} orders ({elapsed:.1f}s)")

        adaptive_time = time.time() - adaptive_start

        # Test Static Engine
        static_engine = BaseMatchingEngine()
        static_monitor = PerformanceMonitor(static_engine)

        print("🔄 Testing STATIC engine...")
        static_start = time.time()
        static_trades = []

        for i, order in enumerate(orders):
            trades = static_engine.process_order(order)
            static_trades.extend(trades)

        static_time = time.time() - static_start

        # Results
        print("\n📈 RESULTS:")
        print("-" * 40)
        print(f"Adaptive Engine:")
        print(f"  Time: {adaptive_time:.2f}s")
        print(f"  Throughput: {len(orders)/adaptive_time:.1f} orders/sec")
        print(f"  Trades: {len(adaptive_trades)}")
        print(f"  Regime Changes: {adaptive_engine.regime_change_count}")
        print(f"  Final Regime: {adaptive_engine.current_regime.value}")

        print(f"\nStatic Engine:")
        print(f"  Time: {static_time:.2f}s")
        print(f"  Throughput: {len(orders)/static_time:.1f} orders/sec")
        print(f"  Trades: {len(static_trades)}")

        # Comparison
        if static_time > 0:
            speedup = adaptive_time / static_time
            print(f"\n⚡ Performance Comparison:")
            print(
                f"  Adaptive is {speedup:.1f}x {'slower' if speedup > 1 else 'faster'} than Static"
            )
            print(
                f"  Throughput improvement: {(len(orders)/adaptive_time - len(orders)/static_time):.1f} orders/sec"
            )

        return {
            "adaptive": {
                "time": adaptive_time,
                "trades": len(adaptive_trades),
                "throughput": len(orders) / adaptive_time,
                "regime_changes": adaptive_engine.regime_change_count,
            },
            "static": {
                "time": static_time,
                "trades": len(static_trades),
                "throughput": len(orders) / static_time,
            },
        }


def main():
    """Run fast analysis"""
    print("🚀 FAST NIFTY ANALYSIS - OPTIMIZED FOR QUICK RESULTS")
    print("This will give you immediate insights without long waits\n")

    analyzer = FastNiftyAnalysis()

    # Test cases - smaller datasets for speed
    test_cases = [
        ("NIFTY", 2020, 2000),  # COVID year, 2000 orders
        ("NIFTY", 2008, 1500),  # Crisis year, 1500 orders
        ("NIFTY", 2015, 1000),  # Normal year, 1000 orders
    ]

    all_results = {}

    for symbol, year, sample_size in test_cases:
        try:
            results = analyzer.run_quick_comparison(symbol, year, sample_size)
            all_results[f"{symbol}_{year}"] = results
            print("\n" + "=" * 60 + "\n")

        except Exception as e:
            print(f"❌ Error analyzing {symbol} {year}: {e}")
            continue

    # Summary
    if all_results:
        print("🎯 SUMMARY ACROSS ALL TESTS:")
        print("=" * 50)

        for test_name, results in all_results.items():
            adaptive = results["adaptive"]
            static = results["static"]

            print(f"\n{test_name}:")
            print(
                f"  Adaptive: {adaptive['trades']} trades, {adaptive['regime_changes']} regime changes"
            )
            print(f"  Static: {static['trades']} trades")

            if static["time"] > 0:
                speed_ratio = adaptive["time"] / static["time"]
                print(f"  Speed Ratio: {speed_ratio:.2f}x")


if __name__ == "__main__":
    main()
