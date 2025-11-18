"""
Demonstration of Adaptive Matching Engine Flexibility
Shows various configuration options and their effects
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.matching_engine import AdaptiveMatchingEngine
from src.data.order_generator import OrderGenerator
from src.core.order_types import MarketRegime
import time


def print_section(title):
    """Print a formatted section header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def test_default_config():
    """Test with default configuration"""
    print_section("Test 1: Default Configuration")

    engine = AdaptiveMatchingEngine()
    config = engine.get_config()

    print("\nDefault Configuration:")
    for key, value in config.items():
        print(f"  {key}: {value}")

    # Generate and process orders
    generator = OrderGenerator(price_range=(18000.0, 19000.0))
    orders = generator.generate_orders(1000, volatility=0.02)

    start = time.perf_counter()
    total_trades = 0

    for order in orders:
        trades = engine.process_order(order)
        total_trades += len(trades)

    elapsed = time.perf_counter() - start

    # Get statistics
    stats = engine.get_regime_statistics()

    print(f"\nResults:")
    print(f"  Orders Processed: 1,000")
    print(f"  Total Trades: {total_trades:,}")
    print(f"  Processing Time: {elapsed:.3f}s")
    print(f"  Throughput: {1000/elapsed:,.0f} ops/s")
    print(f"  Regime Changes: {stats['total_changes']}")
    print(f"  Final Regime: {stats['current_regime']}")


def test_high_sensitivity():
    """Test with high sensitivity configuration"""
    print_section("Test 2: High Sensitivity Configuration (Volatile Markets)")

    config = {
        "detection_interval": 50,  # Check more frequently
        "window_size": 100,
        "volatility_threshold": 0.03,  # Lower thresholds = more sensitive
        "spread_threshold": 0.01,
        "imbalance_threshold": 0.4,
        "cancellation_threshold": 0.15,
    }

    engine = AdaptiveMatchingEngine(config=config)

    print("\nHigh Sensitivity Configuration:")
    for key, value in config.items():
        print(f"  {key}: {value}")

    # Generate more volatile orders
    generator = OrderGenerator(price_range=(18000.0, 19000.0))
    orders = generator.generate_orders(1000, volatility=0.03)

    start = time.perf_counter()
    total_trades = 0

    for order in orders:
        trades = engine.process_order(order)
        total_trades += len(trades)

    elapsed = time.perf_counter() - start

    # Get statistics
    stats = engine.get_regime_statistics()

    print(f"\nResults:")
    print(f"  Orders Processed: 1,000")
    print(f"  Total Trades: {total_trades:,}")
    print(f"  Processing Time: {elapsed:.3f}s")
    print(f"  Throughput: {1000/elapsed:,.0f} ops/s")
    print(f"  Regime Changes: {stats['total_changes']}")
    print(f"  Final Regime: {stats['current_regime']}")

    if stats["regime_distribution"]:
        print(f"\n  Regime Distribution:")
        for regime, count in stats["regime_distribution"].items():
            print(f"    {regime}: {count} changes")


def test_low_sensitivity():
    """Test with low sensitivity configuration"""
    print_section("Test 3: Low Sensitivity Configuration (Stable Markets)")

    config = {
        "detection_interval": 200,  # Check less frequently
        "window_size": 100,
        "volatility_threshold": 0.08,  # Higher thresholds = less sensitive
        "spread_threshold": 0.04,
        "imbalance_threshold": 0.7,
        "cancellation_threshold": 0.4,
    }

    engine = AdaptiveMatchingEngine(config=config)

    print("\nLow Sensitivity Configuration:")
    for key, value in config.items():
        print(f"  {key}: {value}")

    # Generate stable orders
    generator = OrderGenerator(price_range=(18000.0, 19000.0))
    orders = generator.generate_orders(1000, volatility=0.01)

    start = time.perf_counter()
    total_trades = 0

    for order in orders:
        trades = engine.process_order(order)
        total_trades += len(trades)

    elapsed = time.perf_counter() - start

    # Get statistics
    stats = engine.get_regime_statistics()

    print(f"\nResults:")
    print(f"  Orders Processed: 1,000")
    print(f"  Total Trades: {total_trades:,}")
    print(f"  Processing Time: {elapsed:.3f}s")
    print(f"  Throughput: {1000/elapsed:,.0f} ops/s")
    print(f"  Regime Changes: {stats['total_changes']}")
    print(f"  Final Regime: {stats['current_regime']}")


def test_dynamic_updates():
    """Test dynamic configuration updates"""
    print_section("Test 4: Dynamic Configuration Updates")

    engine = AdaptiveMatchingEngine()

    print("\nInitial Configuration:")
    config = engine.get_config()
    print(f"  Volatility Threshold: {config['volatility_threshold']}")
    print(f"  Detection Interval: {config['detection_interval']}")

    # Update configuration dynamically
    print("\nUpdating configuration...")
    engine.update_config({"volatility_threshold": 0.08, "detection_interval": 150})

    print("\nUpdated Configuration:")
    config = engine.get_config()
    print(f"  Volatility Threshold: {config['volatility_threshold']}")
    print(f"  Detection Interval: {config['detection_interval']}")

    # Update individual threshold
    print("\nUpdating individual threshold...")
    engine.set_regime_threshold("spread", 0.05)

    config = engine.get_config()
    print(f"  Spread Threshold: {config['spread_threshold']}")


def test_benchmark_mode():
    """Test benchmark mode (no adaptive features)"""
    print_section("Test 5: Benchmark Mode (Maximum Performance)")

    # Regular adaptive mode
    engine_adaptive = AdaptiveMatchingEngine()

    # Benchmark mode
    engine_benchmark = AdaptiveMatchingEngine(
        config={"enable_regime_detection": False}, benchmark_mode=True
    )

    generator = OrderGenerator(price_range=(18000.0, 19000.0))
    orders = generator.generate_orders(5000, volatility=0.01)

    # Test adaptive mode
    print("\nAdaptive Mode:")
    start = time.perf_counter()
    for order in orders:
        engine_adaptive.process_order(order)
    adaptive_time = time.perf_counter() - start

    print(f"  Processing Time: {adaptive_time:.3f}s")
    print(f"  Throughput: {5000/adaptive_time:,.0f} ops/s")

    # Test benchmark mode
    print("\nBenchmark Mode:")
    orders_benchmark = generator.generate_orders(5000, volatility=0.01)
    start = time.perf_counter()
    for order in orders_benchmark:
        engine_benchmark.process_order(order)
    benchmark_time = time.perf_counter() - start

    print(f"  Processing Time: {benchmark_time:.3f}s")
    print(f"  Throughput: {5000/benchmark_time:,.0f} ops/s")

    # Comparison
    speedup = adaptive_time / benchmark_time
    print(f"\nPerformance Comparison:")
    print(f"  Benchmark mode is {speedup:.2f}x faster")
    print(f"  Adaptive overhead: {(speedup-1)*100:.1f}%")


def test_custom_scenarios():
    """Test custom market scenarios"""
    print_section("Test 6: Custom Market Scenarios")

    scenarios = [
        {
            "name": "Crypto Market (High Volatility)",
            "config": {
                "detection_interval": 50,
                "volatility_threshold": 0.10,
                "spread_threshold": 0.05,
                "imbalance_threshold": 0.7,
            },
            "volatility": 0.04,
        },
        {
            "name": "Blue-Chip Stocks (Stable)",
            "config": {
                "detection_interval": 200,
                "volatility_threshold": 0.02,
                "spread_threshold": 0.005,
                "imbalance_threshold": 0.6,
            },
            "volatility": 0.005,
        },
        {
            "name": "Small-Cap Stocks (Illiquid)",
            "config": {
                "detection_interval": 100,
                "volatility_threshold": 0.08,
                "spread_threshold": 0.03,
                "imbalance_threshold": 0.8,
            },
            "volatility": 0.02,
        },
    ]

    for scenario in scenarios:
        print(f"\n{scenario['name']}:")
        print(f"  Configuration: {scenario['config']}")

        engine = AdaptiveMatchingEngine(config=scenario["config"])
        generator = OrderGenerator(price_range=(18000.0, 19000.0))
        orders = generator.generate_orders(1000, volatility=scenario["volatility"])

        start = time.perf_counter()
        for order in orders:
            engine.process_order(order)
        elapsed = time.perf_counter() - start

        stats = engine.get_regime_statistics()

        print(f"  Throughput: {1000/elapsed:,.0f} ops/s")
        print(f"  Regime Changes: {stats['total_changes']}")
        print(f"  Final Regime: {stats['current_regime']}")


def main():
    """Run all flexibility demonstrations"""
    print("\n" + "=" * 70)
    print("  ADAPTIVE MATCHING ENGINE - FLEXIBILITY DEMONSTRATION")
    print("=" * 70)
    print("\nThis demo shows various configuration options and their effects")
    print("on performance and regime detection behavior.\n")

    test_default_config()
    test_high_sensitivity()
    test_low_sensitivity()
    test_dynamic_updates()
    test_benchmark_mode()
    test_custom_scenarios()

    print("\n" + "=" * 70)
    print("  DEMONSTRATION COMPLETE")
    print("=" * 70)
    print("\nFor more details, see FLEXIBILITY_GUIDE.md")
    print("For UI testing, run: streamlit run ../adaptive-matching-engine-ui/app.py\n")


if __name__ == "__main__":
    main()
