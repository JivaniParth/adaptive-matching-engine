#!/usr/bin/env python3
"""
Basic usage example for the Adaptive Matching Engine
"""

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.core.matching_engine import AdaptiveMatchingEngine
from src.core.order_types import Order, OrderSide, OrderType
from src.data.order_generator import OrderGenerator
from src.utils.performance import PerformanceMonitor
import time


def demo_basic_functionality():
    """Demonstrate basic matching engine functionality"""
    print("=== Adaptive Matching Engine Demo ===\n")

    # Initialize engine
    engine = AdaptiveMatchingEngine()

    # Create some sample orders
    orders = [
        Order.create_limit_order(OrderSide.BUY, 100.0, 100),
        Order.create_limit_order(OrderSide.BUY, 99.5, 50),
        Order.create_limit_order(OrderSide.SELL, 101.0, 75),
        Order.create_limit_order(OrderSide.SELL, 100.5, 100),
    ]

    print("Initial Order Book:")
    snapshot = engine.get_order_book_snapshot()
    print(f"Bids: {snapshot.bids}")
    print(f"Asks: {snapshot.asks}")
    print(f"Spread: {snapshot.spread:.2f}\n")

    # Process orders
    for i, order in enumerate(orders):
        print(
            f"Processing order {i+1}: {order.side.value} {order.quantity} @ {order.price}"
        )
        trades = engine.process_order(order)

        if trades:
            for trade in trades:
                print(f"  TRADE: {trade.quantity} @ {trade.price}")

        snapshot = engine.get_order_book_snapshot()
        print(
            f"  Spread: {snapshot.spread:.2f}, Regime: {engine.current_regime.value}\n"
        )

    # Final order book state
    print("Final Order Book:")
    snapshot = engine.get_order_book_snapshot()
    print(f"Bids: {snapshot.bids}")
    print(f"Asks: {snapshot.asks}")
    print(f"Regime changes: {engine.regime_change_count}")


def demo_performance():
    """Demonstrate performance measurement"""
    print("\n=== Performance Demo ===\n")

    engine = AdaptiveMatchingEngine()
    monitor = PerformanceMonitor(engine)
    generator = OrderGenerator()

    # Generate test orders
    orders = generator.generate_orders(1000)

    # Measure performance
    print("Running performance test with 1000 orders...")
    stats = monitor.measure_throughput(orders)

    print("Performance Results:")
    print(f"Throughput: {stats['throughput_ops']:.2f} orders/sec")
    print(f"Average Latency: {stats['avg_latency_ms']:.4f} ms")
    print(f"P95 Latency: {stats['p95_latency_ms']:.4f} ms")
    print(f"P99 Latency: {stats['p99_latency_ms']:.4f} ms")

    # Generate report
    print("\nDetailed Report:")
    monitor.print_report()


def demo_regime_detection():
    """Demonstrate regime detection with volatile orders"""
    print("\n=== Regime Detection Demo ===\n")

    engine = AdaptiveMatchingEngine()
    generator = OrderGenerator()

    # Start with normal orders
    print("Phase 1: Normal market conditions")
    normal_orders = generator.generate_orders(200)
    for order in normal_orders[:50]:  # Process first 50
        engine.process_order(order)

    print(f"Current regime: {engine.current_regime.value}")

    # Switch to volatile orders
    print("\nPhase 2: Volatile market conditions")
    volatile_orders = generator.generate_volatile_orders(100)
    for order in volatile_orders:
        trades = engine.process_order(order)
        if engine.regime_change_count > 0:
            print(f"Regime changed to: {engine.current_regime.value}")
            break

    # Show final state
    print(f"\nFinal regime: {engine.current_regime.value}")
    print(f"Total regime changes: {engine.regime_change_count}")


if __name__ == "__main__":
    demo_basic_functionality()
    demo_performance()
    demo_regime_detection()
