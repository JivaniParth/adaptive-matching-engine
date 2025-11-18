#!/usr/bin/env python3
"""
Main entry point for the Adaptive Matching Engine
Run this file to start the application with various options
"""

import sys
import os
import argparse
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.core.matching_engine import AdaptiveMatchingEngine, BaseMatchingEngine
from src.data.order_generator import OrderGenerator
from src.utils.performance import PerformanceMonitor
from src.utils.logger import setup_logging, get_logger
import json


def run_basic_demo():
    """Run basic demonstration of the matching engine"""
    print("\n" + "=" * 70)
    print("BASIC MATCHING ENGINE DEMONSTRATION")
    print("=" * 70 + "\n")

    from src.core.order_types import Order, OrderSide

    engine = AdaptiveMatchingEngine()

    # Create sample orders with realistic Indian market prices
    print("Creating sample orders (NIFTY-like prices in INR)...")
    orders = [
        Order.create_limit_order(OrderSide.BUY, 18000.0, 100),
        Order.create_limit_order(OrderSide.BUY, 17995.0, 50),
        Order.create_limit_order(OrderSide.SELL, 18010.0, 75),
        Order.create_limit_order(OrderSide.SELL, 18005.0, 100),
    ]

    print("\nProcessing orders:")
    for i, order in enumerate(orders, 1):
        print(f"\n{i}. {order.side.value} {order.quantity} @ ₹{order.price}")
        trades = engine.process_order(order)

        if trades:
            print(f"   ✓ Generated {len(trades)} trade(s):")
            for trade in trades:
                print(f"     - {trade.quantity} units @ ₹{trade.price}")
        else:
            print(f"   → Added to order book")

        snapshot = engine.get_order_book_snapshot()
        print(
            f"   Spread: ₹{snapshot.spread:.2f}, Regime: {engine.current_regime.value}"
        )

    print("\n" + "=" * 70)
    print(
        f"Summary: {len(engine.trade_history)} trades, {engine.regime_change_count} regime changes"
    )
    print("=" * 70 + "\n")


def run_performance_test(order_count=5000):
    """Run performance benchmark"""
    print("\n" + "=" * 70)
    print(f"PERFORMANCE BENCHMARK - {order_count:,} ORDERS")
    print("=" * 70 + "\n")

    # Test both engines
    print("Testing STATIC engine...")
    static_engine = BaseMatchingEngine()
    static_monitor = PerformanceMonitor(static_engine)
    generator = OrderGenerator()

    orders = generator.generate_orders(order_count)
    static_stats = static_monitor.measure_throughput(orders)

    print(f"✓ Static Engine:")
    print(f"  Throughput: {static_stats['throughput_ops']:,.0f} orders/sec")
    print(f"  Avg Latency: {static_stats['avg_latency_ms']:.4f} ms")
    print(f"  P95 Latency: {static_stats['p95_latency_ms']:.4f} ms")
    print(f"  P99 Latency: {static_stats['p99_latency_ms']:.4f} ms")

    print("\nTesting ADAPTIVE engine...")
    adaptive_engine = AdaptiveMatchingEngine()
    adaptive_monitor = PerformanceMonitor(adaptive_engine)

    orders = generator.generate_orders(order_count)
    adaptive_stats = adaptive_monitor.measure_throughput(orders)

    print(f"✓ Adaptive Engine:")
    print(f"  Throughput: {adaptive_stats['throughput_ops']:,.0f} orders/sec")
    print(f"  Avg Latency: {adaptive_stats['avg_latency_ms']:.4f} ms")
    print(f"  P95 Latency: {adaptive_stats['p95_latency_ms']:.4f} ms")
    print(f"  P99 Latency: {adaptive_stats['p99_latency_ms']:.4f} ms")
    print(f"  Regime Changes: {adaptive_engine.regime_change_count}")

    # Save results
    results_dir = "results"
    os.makedirs(results_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = os.path.join(results_dir, f"performance_test_{timestamp}.json")

    results = {
        "timestamp": timestamp,
        "order_count": order_count,
        "static_engine": static_stats,
        "adaptive_engine": adaptive_stats,
        "comparison": {
            "throughput_ratio": adaptive_stats["throughput_ops"]
            / static_stats["throughput_ops"],
            "latency_overhead_pct": (
                (adaptive_stats["avg_latency_ms"] - static_stats["avg_latency_ms"])
                / static_stats["avg_latency_ms"]
                * 100
            ),
        },
    }

    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n✓ Results saved to: {results_file}")
    print("=" * 70 + "\n")


def run_regime_detection_demo():
    """Demonstrate regime detection capabilities"""
    print("\n" + "=" * 70)
    print("REGIME DETECTION DEMONSTRATION")
    print("=" * 70 + "\n")

    engine = AdaptiveMatchingEngine()
    generator = OrderGenerator()

    # Phase 1: Normal market
    print("Phase 1: Normal Market Conditions")
    normal_orders = generator.generate_orders(100)
    for order in normal_orders[:50]:
        engine.process_order(order)
    print(f"  Current Regime: {engine.current_regime.value}")

    # Phase 2: Volatile market
    print("\nPhase 2: Introducing Volatility")
    volatile_orders = generator.generate_volatile_orders(100)
    regime_changed = False
    for i, order in enumerate(volatile_orders):
        engine.process_order(order)
        if not regime_changed and engine.regime_change_count > 0:
            print(
                f"  ✓ Regime changed to: {engine.current_regime.value} (after {i} orders)"
            )
            regime_changed = True

    print(f"\n  Final Regime: {engine.current_regime.value}")
    print(f"  Total Regime Changes: {engine.regime_change_count}")

    # Save regime history
    if engine.regime_history:
        results_dir = "results"
        os.makedirs(results_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        regime_file = os.path.join(results_dir, f"regime_history_{timestamp}.json")

        with open(regime_file, "w") as f:
            json.dump(engine.regime_history, f, indent=2)

        print(f"\n✓ Regime history saved to: {regime_file}")

    print("=" * 70 + "\n")


def run_nifty_analysis(symbol="NIFTY", year=2020, sample_size=2000):
    """Run analysis on Nifty data"""
    print("\n" + "=" * 70)
    print(f"NIFTY DATA ANALYSIS - {symbol} {year}")
    print("=" * 70 + "\n")

    from src.data.nifty_loader import NiftyDataLoader

    loader = NiftyDataLoader()

    print(f"Loading {symbol} data for {year}...")
    data = loader.load_intraday_data(symbol, year)

    if data is None or len(data) == 0:
        print(f"❌ No data found for {symbol} {year}")
        print(f"   Make sure data file exists: data/{symbol}_{year}_intraday.csv")
        return

    print(f"✓ Loaded {len(data)} records")

    # Sample if too large
    if len(data) > sample_size:
        data = data.sample(sample_size)
        print(f"  Using sample of {len(data)} records")

    # Convert to orders
    print("\nConverting to orders...")
    orders = loader.convert_to_orders(data, orders_per_record=2)
    print(f"✓ Generated {len(orders)} orders")

    # Test with both engines
    print("\n1. Testing STATIC engine...")
    static_engine = BaseMatchingEngine()
    static_trades = 0
    import time

    start = time.time()
    for order in orders:
        trades = static_engine.process_order(order)
        static_trades += len(trades)
    static_time = time.time() - start

    print(f"   Time: {static_time:.2f}s")
    print(f"   Trades: {static_trades}")
    print(f"   Throughput: {len(orders)/static_time:.0f} orders/sec")

    print("\n2. Testing ADAPTIVE engine...")
    adaptive_engine = AdaptiveMatchingEngine()
    adaptive_trades = 0
    start = time.time()
    for order in orders:
        trades = adaptive_engine.process_order(order)
        adaptive_trades += len(trades)
    adaptive_time = time.time() - start

    print(f"   Time: {adaptive_time:.2f}s")
    print(f"   Trades: {adaptive_trades}")
    print(f"   Throughput: {len(orders)/adaptive_time:.0f} orders/sec")
    print(f"   Regime Changes: {adaptive_engine.regime_change_count}")
    print(f"   Final Regime: {adaptive_engine.current_regime.value}")

    # Save results
    results_dir = "results"
    os.makedirs(results_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = os.path.join(
        results_dir, f"nifty_analysis_{symbol}_{year}_{timestamp}.json"
    )

    results = {
        "symbol": symbol,
        "year": year,
        "timestamp": timestamp,
        "data_records": len(data),
        "orders_generated": len(orders),
        "static_engine": {
            "time_sec": static_time,
            "trades": static_trades,
            "throughput": len(orders) / static_time,
        },
        "adaptive_engine": {
            "time_sec": adaptive_time,
            "trades": adaptive_trades,
            "throughput": len(orders) / adaptive_time,
            "regime_changes": adaptive_engine.regime_change_count,
            "final_regime": adaptive_engine.current_regime.value,
        },
    }

    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n✓ Results saved to: {results_file}")
    print("=" * 70 + "\n")


def list_results():
    """List all saved results"""
    results_dir = "results"

    if not os.path.exists(results_dir):
        print(f"\n❌ Results directory not found: {results_dir}")
        print("   Run some tests first to generate results!\n")
        return

    files = [f for f in os.listdir(results_dir) if f.endswith(".json")]

    if not files:
        print(f"\n❌ No result files found in {results_dir}/")
        print("   Run some tests first to generate results!\n")
        return

    print("\n" + "=" * 70)
    print(f"SAVED RESULTS ({len(files)} files)")
    print("=" * 70 + "\n")

    for i, filename in enumerate(sorted(files), 1):
        filepath = os.path.join(results_dir, filename)
        size = os.path.getsize(filepath)
        mtime = datetime.fromtimestamp(os.path.getmtime(filepath))

        print(f"{i}. {filename}")
        print(f"   Size: {size:,} bytes")
        print(f"   Modified: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
        print()

    print("=" * 70 + "\n")


def show_help():
    """Show detailed help and usage examples"""
    print("\n" + "=" * 70)
    print("ADAPTIVE MATCHING ENGINE - HELP")
    print("=" * 70 + "\n")

    print("📁 PROJECT STRUCTURE:")
    print("  main.py                 ← YOU ARE HERE (main entry point)")
    print("  config/                 ← Configuration files")
    print("  src/")
    print("    ├── core/             ← Core matching engine logic")
    print("    ├── adaptive/         ← Adaptive regime detection")
    print("    ├── data/             ← Data loaders and generators")
    print("    └── utils/            ← Utilities and monitoring")
    print("  examples/               ← Example scripts")
    print("  tests/                  ← Unit tests")
    print("  results/                ← Output files (auto-created)")
    print("  data/                   ← Input data files (Nifty CSV)")

    print("\n📋 AVAILABLE COMMANDS:")
    print("  python main.py demo              - Basic demonstration")
    print("  python main.py performance       - Run performance benchmark")
    print("  python main.py regime            - Regime detection demo")
    print("  python main.py nifty             - Analyze Nifty data")
    print("  python main.py results           - List saved results")
    print("  python main.py help              - Show this help")

    print("\n🎯 COMMON USAGE:")
    print("  # Quick start - see how it works")
    print("  python main.py demo")
    print()
    print("  # Performance test with 10,000 orders")
    print("  python main.py performance --orders 10000")
    print()
    print("  # Analyze Nifty 2020 data")
    print("  python main.py nifty --symbol NIFTY --year 2020")
    print()
    print("  # Check saved results")
    print("  python main.py results")

    print("\n📊 NIFTY DATA FORMAT:")
    print("  Place your Nifty data files in: data/NIFTY_2020_intraday.csv")
    print("  Required columns: timestamp, price, volume (flexible column names)")

    print("\n💡 TIPS:")
    print("  - Results are automatically saved in results/ folder")
    print("  - Use --orders flag to control test size")
    print("  - Check results/ folder for JSON output files")
    print("  - Run tests/ folder for unit tests: python -m pytest tests/")

    print("\n" + "=" * 70 + "\n")


def main():
    """Main entry point with argument parsing"""
    parser = argparse.ArgumentParser(
        description="Adaptive Heap-Based Order Matching Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "command",
        choices=["demo", "performance", "regime", "nifty", "results", "help"],
        help="Command to run",
    )

    parser.add_argument(
        "--orders",
        type=int,
        default=5000,
        help="Number of orders for performance test (default: 5000)",
    )

    parser.add_argument(
        "--symbol",
        type=str,
        default="NIFTY",
        help="Symbol for Nifty analysis (default: NIFTY)",
    )

    parser.add_argument(
        "--year", type=int, default=2020, help="Year for Nifty analysis (default: 2020)"
    )

    parser.add_argument(
        "--sample",
        type=int,
        default=2000,
        help="Sample size for Nifty analysis (default: 2000)",
    )

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)",
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(level=args.log_level)

    # Create results directory
    os.makedirs("results", exist_ok=True)

    # Route to appropriate function
    if args.command == "demo":
        run_basic_demo()

    elif args.command == "performance":
        run_performance_test(args.orders)

    elif args.command == "regime":
        run_regime_detection_demo()

    elif args.command == "nifty":
        run_nifty_analysis(args.symbol, args.year, args.sample)

    elif args.command == "results":
        list_results()

    elif args.command == "help":
        show_help()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user\n")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}\n")
        import traceback

        traceback.print_exc()
        sys.exit(1)
