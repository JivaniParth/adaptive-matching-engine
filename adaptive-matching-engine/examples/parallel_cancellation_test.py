#!/usr/bin/env python3
"""
Test to demonstrate sharding benefits with parallel cancellations
"""

import sys
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import threading

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.matching_engine import AdaptiveMatchingEngine
from src.core.sharded_matching_engine import ShardedAdaptiveMatchingEngine
from src.data.order_generator import OrderGenerator


def test_parallel_cancellations(num_orders=10000, cancel_pct=50, num_threads=4):
    """Compare cancellation performance with parallel execution"""
    print("=" * 80)
    print("PARALLEL CANCELLATION PERFORMANCE TEST")
    print("=" * 80)
    print(f"\nTest Configuration:")
    print(f"  Orders: {num_orders:,}")
    print(f"  Cancellation rate: {cancel_pct}%")
    print(f"  Parallel threads: {num_threads}")
    print()

    # Generate orders
    print("Generating orders...")
    generator = OrderGenerator()
    orders_standard = generator.generate_orders(count=num_orders)
    orders_sharded = generator.generate_orders(count=num_orders)
    print(f"Generated {len(orders_standard)} orders\n")

    # Test Standard Engine
    print("-" * 80)
    print("Testing Standard Adaptive Engine (Sequential Cancellations)...")
    print("-" * 80)
    standard_engine = AdaptiveMatchingEngine()

    # Add all orders
    start_add = time.perf_counter()
    for order in orders_standard:
        standard_engine.process_order(order)
    add_elapsed = time.perf_counter() - start_add

    # Collect order IDs to cancel
    all_order_ids = [o.order_id for o in orders_standard]
    num_to_cancel = int(len(all_order_ids) * cancel_pct / 100)
    cancel_ids = all_order_ids[:num_to_cancel]

    # Sequential cancellation
    start_cancel = time.perf_counter()
    cancelled = 0
    for order_id in cancel_ids:
        if standard_engine.cancel_order(order_id):
            cancelled += 1
    cancel_elapsed = time.perf_counter() - start_cancel

    standard_throughput = num_to_cancel / cancel_elapsed if cancel_elapsed > 0 else 0

    print(f"Add time: {add_elapsed:.3f}s")
    print(f"Cancel time: {cancel_elapsed:.3f}s")
    print(f"Cancelled: {cancelled}/{num_to_cancel}")
    print(f"Cancel throughput: {standard_throughput:,.0f} cancellations/sec\n")

    # Test Sharded Engine with Parallel Cancellations
    print("-" * 80)
    print(f"Testing Sharded Engine (Parallel Cancellations, {num_threads} threads)...")
    print("-" * 80)
    sharded_engine = ShardedAdaptiveMatchingEngine(num_shards=8)

    # Add all orders
    start_add = time.perf_counter()
    for order in orders_sharded:
        sharded_engine.process_order(order)
    add_elapsed = time.perf_counter() - start_add

    # Collect order IDs to cancel
    all_order_ids = [o.order_id for o in orders_sharded]
    num_to_cancel = int(len(all_order_ids) * cancel_pct / 100)
    cancel_ids = all_order_ids[:num_to_cancel]

    # Parallel cancellation using ThreadPoolExecutor
    cancelled_count = threading.Lock()
    cancelled = 0

    def cancel_batch(ids):
        nonlocal cancelled
        local_count = 0
        for order_id in ids:
            if sharded_engine.cancel_order(order_id):
                local_count += 1
        with cancelled_count:
            cancelled += local_count

    # Split cancellations across threads
    batch_size = len(cancel_ids) // num_threads
    batches = [
        cancel_ids[i : i + batch_size] for i in range(0, len(cancel_ids), batch_size)
    ]

    start_cancel = time.perf_counter()
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        executor.map(cancel_batch, batches)
    cancel_elapsed = time.perf_counter() - start_cancel

    sharded_throughput = num_to_cancel / cancel_elapsed if cancel_elapsed > 0 else 0

    print(f"Add time: {add_elapsed:.3f}s")
    print(f"Cancel time: {cancel_elapsed:.3f}s")
    print(f"Cancelled: {cancelled}/{num_to_cancel}")
    print(f"Cancel throughput: {sharded_throughput:,.0f} cancellations/sec\n")

    # Summary
    print("=" * 80)
    print("PERFORMANCE COMPARISON")
    print("=" * 80)
    speedup = sharded_throughput / standard_throughput if standard_throughput > 0 else 0

    print(f"\nStandard (Sequential):  {standard_throughput:>12,.0f} cancellations/sec")
    print(f"Sharded (Parallel):     {sharded_throughput:>12,.0f} cancellations/sec")
    print(f"\nSpeedup:                {speedup:>12.2f}x")

    if speedup > 1:
        improvement = (speedup - 1) * 100
        print(f"Improvement:            {improvement:>12.1f}%")
        print(
            f"\n✓ Sharding provides {speedup:.1f}x faster cancellations with parallel execution!"
        )
    else:
        degradation = (1 - speedup) * 100
        print(f"Degradation:            {degradation:>12.1f}%")


if __name__ == "__main__":
    print("\n")
    test_parallel_cancellations(num_orders=10000, cancel_pct=50, num_threads=4)
    print("\n")
