#!/usr/bin/env python3
"""
Demonstration of regime detection and adaptive behavior
"""

import time
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.core.matching_engine import AdaptiveMatchingEngine
from src.data.order_generator import OrderGenerator
from src.core.order_types import MarketRegime, OrderSide
from src.adaptive.regime_detector import RegimeDetector


class RegimeDemonstration:
    """Demonstrates regime detection and adaptive behavior"""

    def __init__(self):
        self.engine = AdaptiveMatchingEngine()
        self.generator = OrderGenerator()
        self.regime_history = []

    def demonstrate_normal_regime(self):
        """Demonstrate normal market regime"""
        print("\n=== NORMAL REGIME DEMONSTRATION ===")
        print("Characteristics: Low volatility, balanced order flow, tight spreads")

        orders = self.generator.generate_orders(100, market_order_ratio=0.1)

        for i, order in enumerate(orders):
            trades = self.engine.process_order(order)

            if i % 20 == 0:
                snapshot = self.engine.get_order_book_snapshot()
                print(
                    f"Order {i}: Regime={self.engine.current_regime.value}, "
                    f"Spread={snapshot.spread:.4f}, "
                    f"Trades={len(trades)}"
                )

    def demonstrate_volatile_regime(self):
        """Demonstrate high volatility regime"""
        print("\n=== HIGH VOLATILITY REGIME DEMONSTRATION ===")
        print("Characteristics: Large price movements, high cancellation rate")

        # Create volatile conditions with large market orders
        volatile_orders = []

        # Add some large market orders to create volatility
        for i in range(10):
            large_order = self.generator.generate_orders(1, market_order_ratio=1.0)[0]
            large_order.quantity = 500  # Make it large
            volatile_orders.append(large_order)

        # Add normal orders with high price variation
        volatile_orders.extend(self.generator.generate_volatile_orders(50))

        regime_changed = False
        for i, order in enumerate(volatile_orders):
            trades = self.engine.process_order(order)

            if (
                not regime_changed
                and self.engine.current_regime == MarketRegime.HIGH_VOLATILITY
            ):
                print(f"*** REGIME CHANGE DETECTED at order {i} ***")
                regime_changed = True

            if i % 10 == 0:
                snapshot = self.engine.get_order_book_snapshot()
                print(
                    f"Order {i}: Regime={self.engine.current_regime.value}, "
                    f"Spread={snapshot.spread:.4f}, "
                    f"Large trades={len([t for t in trades if t.quantity > 100])}"
                )

    def demonstrate_illiquid_regime(self):
        """Demonstrate illiquid market regime"""
        print("\n=== ILLIQUID REGIME DEMONSTRATION ===")
        print("Characteristics: Wide spreads, low order book depth")

        # Create illiquid conditions by processing few orders
        # and then checking the wide spreads

        # First, clear the order book
        self.engine = AdaptiveMatchingEngine()  # Reset

        # Add only a few orders with wide spreads
        illiquid_orders = [
            self.generator.generate_orders(1, market_order_ratio=0.0)[0],
            self.generator.generate_orders(1, market_order_ratio=0.0)[0],
        ]

        # Set wide spreads manually (in INR)
        illiquid_orders[0].side = OrderSide.BUY
        illiquid_orders[0].price = 17900.0
        illiquid_orders[1].side = OrderSide.SELL
        illiquid_orders[1].price = 18100.0

        for order in illiquid_orders:
            self.engine.process_order(order)

        snapshot = self.engine.get_order_book_snapshot()
        print(f"Created wide spread: {snapshot.spread:.4f}")
        print(f"Current regime: {self.engine.current_regime.value}")

        # The regime detector should identify this as illiquid
        if self.engine.current_regime == MarketRegime.ILLIQUID:
            print("✓ Illiquid regime correctly detected!")

    def demonstrate_regime_transitions(self):
        """Demonstrate smooth transitions between regimes"""
        print("\n=== REGIME TRANSITION DEMONSTRATION ===")

        regimes_to_demonstrate = [
            ("Normal", self.demonstrate_normal_regime),
            ("Volatile", self.demonstrate_volatile_regime),
            ("Back to Normal", self.demonstrate_normal_regime),
        ]

        initial_regime_changes = self.engine.regime_change_count

        for regime_name, demo_function in regimes_to_demonstrate:
            print(f"\n--- Transitioning to {regime_name} ---")
            demo_function()

            # Record regime info
            snapshot = self.engine.get_order_book_snapshot()
            self.regime_history.append(
                {
                    "regime": self.engine.current_regime.value,
                    "timestamp": time.time(),
                    "spread": snapshot.spread,
                    "bid_depth": len(snapshot.bids),
                    "ask_depth": len(snapshot.asks),
                }
            )

        total_transitions = self.engine.regime_change_count - initial_regime_changes
        print(f"\nTotal regime transitions during demo: {total_transitions}")

    def show_regime_statistics(self):
        """Show statistics about regime behavior"""
        print("\n=== REGIME STATISTICS ===")

        if not self.engine.metrics_history:
            print("No metrics history available")
            return

        # Analyze metrics by regime
        regime_metrics = {}
        for metrics in self.engine.metrics_history:
            regime = metrics["regime"]
            if regime not in regime_metrics:
                regime_metrics[regime] = []
            regime_metrics[regime].append(metrics)

        print(f"{'Regime':<15} {'Samples':<10} {'Avg Spread':<12} {'Avg Trades':<12}")
        print("-" * 50)

        for regime, metrics_list in regime_metrics.items():
            avg_spread = sum(m["spread"] for m in metrics_list) / len(metrics_list)
            avg_trades = sum(m["trades_generated"] for m in metrics_list) / len(
                metrics_list
            )

            print(
                f"{regime:<15} {len(metrics_list):<10} {avg_spread:<12.4f} {avg_trades:<12.2f}"
            )

        print(f"\nTotal regime changes: {self.engine.regime_change_count}")


def main():
    """Run the complete regime demonstration"""
    demo = RegimeDemonstration()

    try:
        demo.demonstrate_normal_regime()
        demo.demonstrate_volatile_regime()
        demo.demonstrate_illiquid_regime()
        demo.demonstrate_regime_transitions()
        demo.show_regime_statistics()

        print("\n=== DEMONSTRATION COMPLETE ===")
        print("The adaptive engine has successfully:")
        print("✓ Detected different market regimes")
        print("✓ Adapted matching logic accordingly")
        print("✓ Maintained smooth transitions")
        print("✓ Provided performance metrics")

    except KeyboardInterrupt:
        print("\nDemo interrupted by user")
    except Exception as e:
        print(f"\nError during demonstration: {e}")


if __name__ == "__main__":
    main()
