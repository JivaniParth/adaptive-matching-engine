#!/usr/bin/env python3
"""
Quick test to compare standard vs sharded adaptive matching engine
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.matching_engine import AdaptiveMatchingEngine
from src.core.sharded_matching_engine import ShardedAdaptiveMatchingEngine
from src.data.order_generator import OrderGenerator


def quick_test(num_orders=10000, num_shards=8):
    """Quick performance comparison"""
    print("=" * 80)
    print("QUICK SHARDING PERFORMANCE TEST")
    print("=" * 80)
    print(f"\nTest Configuration:")
    print(f"  Orders: {num_orders:,}")
    print(f"  Shards: {num_shards}")
    print()

    # Generate orders TWICE to ensure fair comparison
    print("Generating orders for standard engine...")
    generator = OrderGenerator()
    orders_standard = generator.generate_orders(count=num_orders)
    print(f"Generated {len(orders_standard)} orders")

    print("Generating orders for sharded engine...")
    orders_sharded = generator.generate_orders(count=num_orders)
    print(f"Generated {len(orders_sharded)} orders\n")

    # Test Standard Adaptive Engine
    print("-" * 80)
    print("Testing Standard Adaptive Engine...")
    print("-" * 80)
    standard_engine = AdaptiveMatchingEngine()

    start_time = time.perf_counter()
    for order in orders_standard:
        standard_engine.process_order(order)
    standard_elapsed = time.perf_counter() - start_time

    standard_throughput = num_orders / standard_elapsed
    standard_orders = len(standard_engine.order_history)
    standard_trades = len(standard_engine.trade_history)

    print(f"Time: {standard_elapsed:.3f}s")
    print(f"Throughput: {standard_throughput:,.0f} orders/sec")
    print(f"Orders processed: {standard_orders}")
    print(f"Trades executed: {standard_trades}")
    print()  # Test Sharded Adaptive Engine
    print("-" * 80)
    print(f"Testing Sharded Adaptive Engine ({num_shards} shards)...")
    print("-" * 80)
    sharded_engine = ShardedAdaptiveMatchingEngine(num_shards=num_shards)

    start_time = time.perf_counter()
    for order in orders_sharded:
        sharded_engine.process_order(order)
    sharded_elapsed = time.perf_counter() - start_time

    sharded_stats = sharded_engine.get_statistics()
    sharded_throughput = num_orders / sharded_elapsed
    sharded_orders = len(sharded_engine.order_history)
    sharded_trades = len(sharded_engine.trade_history)

    print(f"Time: {sharded_elapsed:.3f}s")
    print(f"Throughput: {sharded_throughput:,.0f} orders/sec")
    print(f"Orders processed: {sharded_orders}")
    print(f"Trades executed: {sharded_trades}")
    print()

    # Summary
    print("=" * 80)
    print("PERFORMANCE COMPARISON")
    print("=" * 80)
    speedup = sharded_throughput / standard_throughput

    print(f"\nStandard Engine:    {standard_throughput:>12,.0f} orders/sec")
    print(f"Sharded Engine:     {sharded_throughput:>12,.0f} orders/sec")
    print(f"\nSpeedup:            {speedup:>12.2f}x")

    if speedup > 1:
        improvement = (speedup - 1) * 100
        print(f"Improvement:        {improvement:>12.1f}%")
    else:
        degradation = (1 - speedup) * 100
        print(f"Degradation:        {degradation:>12.1f}%")

    print("\n" + "=" * 80)
    print("Sharded Order Book Distribution:")
    print("=" * 80)

    # Display shard statistics
    if "bids_shards" in sharded_stats:
        print(f"\nBids across {num_shards} shards:")
        for shard_id, count in enumerate(sharded_stats["bids_shards"]):
            print(f"  Shard {shard_id}: {count:>8} orders")

        print(f"\nAsks across {num_shards} shards:")
        for shard_id, count in enumerate(sharded_stats["asks_shards"]):
            print(f"  Shard {shard_id}: {count:>8} orders")


if __name__ == "__main__":
    print("\n")
    quick_test(num_orders=10000, num_shards=8)
    print("\n")
