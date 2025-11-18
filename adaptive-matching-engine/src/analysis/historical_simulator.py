"""
Historical simulation engine for Nifty data
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
import time
from datetime import datetime
import os

from ..core.matching_engine import AdaptiveMatchingEngine, BaseMatchingEngine
from ..core.order_types import Order, Trade, MarketRegime
from ..utils.performance import PerformanceMonitor
from ..data.nifty_loader import NiftyDataLoader


class HistoricalSimulator:
    """Runs historical simulations with Nifty data"""

    def __init__(self, results_dir: str = "results"):
        self.adaptive_engine = AdaptiveMatchingEngine()
        self.static_engine = BaseMatchingEngine()
        self.data_loader = NiftyDataLoader()
        self.results_dir = results_dir
        os.makedirs(results_dir, exist_ok=True)

        # Results storage
        self.simulation_results = {}

    def run_simulation(
        self, symbol: str, start_year: int, end_year: int, sample_fraction: float = 0.1
    ) -> Dict:
        """Run simulation on historical data"""
        print(f"Starting simulation for {symbol} {start_year}-{end_year}")

        # Load historical data
        historical_data = self.data_loader.load_multiple_years(
            symbol, start_year, end_year
        )

        if len(historical_data) == 0:
            print(f"No data available for {symbol}")
            return {}

        # Sample data if needed for performance
        if sample_fraction < 1.0:
            sample_size = int(len(historical_data) * sample_fraction)
            historical_data = historical_data.sample(
                n=min(sample_size, len(historical_data))
            )
            print(
                f"Using sample of {len(historical_data)} records ({sample_fraction*100}%)"
            )

        # Convert to orders
        orders = self.data_loader.convert_to_orders(historical_data)

        if len(orders) == 0:
            print("No orders generated from historical data")
            return {}

        # Sort orders by timestamp
        orders.sort(key=lambda x: x.timestamp)

        print(f"Processing {len(orders)} orders...")

        # Run simulation on both engines
        adaptive_results = self._run_engine_simulation(
            self.adaptive_engine, orders, "adaptive"
        )
        static_results = self._run_engine_simulation(
            self.static_engine, orders, "static"
        )

        # Analyze regime effectiveness
        regime_analysis = self._analyze_regime_effectiveness(historical_data)

        # Compare results
        comparison = self._compare_engines(adaptive_results, static_results)

        # Store results
        results_key = f"{symbol}_{start_year}_{end_year}"
        self.simulation_results[results_key] = {
            "adaptive": adaptive_results,
            "static": static_results,
            "comparison": comparison,
            "regime_analysis": regime_analysis,
            "symbol": symbol,
            "period": f"{start_year}-{end_year}",
            "order_count": len(orders),
        }

        # Save results
        self._save_results(results_key)

        return self.simulation_results[results_key]

    def _run_engine_simulation(
        self, engine, orders: List[Order], engine_type: str
    ) -> Dict:
        """Run simulation on a single engine"""
        print(f"Running {engine_type} engine simulation...")

        monitor = PerformanceMonitor(engine)
        start_time = time.time()

        # Process all orders
        all_trades = []
        for i, order in enumerate(orders):
            trades = engine.process_order(order)
            all_trades.extend(trades)

            # Progress reporting
            if (i + 1) % 10000 == 0:
                elapsed = time.time() - start_time
                print(f"  Processed {i+1}/{len(orders)} orders ({elapsed:.2f}s)")

        total_time = time.time() - start_time

        # Collect results
        results = {
            "engine_type": engine_type,
            "total_orders": len(orders),
            "total_trades": len(all_trades),
            "execution_time": total_time,
            "throughput": len(orders) / total_time,
            "trades": all_trades,
            "performance_report": (
                monitor.generate_report() if hasattr(monitor, "generate_report") else {}
            ),
        }

        # Add regime info for adaptive engine
        if engine_type == "adaptive":
            results.update(
                {
                    "regime_changes": engine.regime_change_count,
                    "final_regime": engine.current_regime.value,
                    "regime_history": getattr(engine, "regime_history", []),
                    "metrics_history": getattr(engine, "metrics_history", []),
                }
            )

        print(
            f"  {engine_type.upper()} Engine: {len(orders)} orders, {len(all_trades)} trades, "
            f"{total_time:.2f}s, {results['throughput']:.2f} orders/sec"
        )

        return results

    def _analyze_regime_effectiveness(self, historical_data: pd.DataFrame) -> Dict:
        """Analyze how well regimes match historical market conditions"""
        regime_analysis = self.data_loader.analyze_market_regimes(historical_data)

        if len(regime_analysis) == 0:
            return {}

        # Compare detected regimes with historical volatility regimes
        volatility_regimes = []
        for _, row in regime_analysis.iterrows():
            vol = row["volatility"]
            if vol > 0.3:
                vol_regime = "HIGH_VOLATILITY"
            elif vol > 0.2:
                vol_regime = "VOLATILE"
            elif vol > 0.1:
                vol_regime = "NORMAL"
            else:
                vol_regime = "LOW_VOLATILITY"

            volatility_regimes.append(vol_regime)

        regime_analysis["volatility_regime"] = volatility_regimes

        return regime_analysis.to_dict("records")

    def _compare_engines(self, adaptive_results: Dict, static_results: Dict) -> Dict:
        """Compare adaptive vs static engine performance"""
        comparison = {
            "throughput_improvement": (
                adaptive_results["throughput"] - static_results["throughput"]
            )
            / static_results["throughput"]
            * 100,
            "latency_difference": adaptive_results["performance_report"]
            .get("latency_ms", {})
            .get("mean", 0)
            - static_results["performance_report"].get("latency_ms", {}).get("mean", 0),
            "trade_count_difference": adaptive_results["total_trades"]
            - static_results["total_trades"],
            "execution_time_difference": adaptive_results["execution_time"]
            - static_results["execution_time"],
        }

        # Add regime-specific insights if available
        if "regime_changes" in adaptive_results:
            comparison["regime_changes"] = adaptive_results["regime_changes"]

        return comparison

    def _save_results(self, results_key: str):
        """Save simulation results to file"""
        import json

        filename = os.path.join(self.results_dir, f"{results_key}_results.json")

        # Convert to serializable format
        serializable_results = {}
        for key, result in self.simulation_results[results_key].items():
            if key in ["trades", "regime_history", "metrics_history"]:
                # Skip large data structures
                serializable_results[key] = f"Count: {len(result)}"
            elif key == "performance_report":
                serializable_results[key] = result
            else:
                serializable_results[key] = result

        with open(filename, "w") as f:
            json.dump(serializable_results, f, indent=2, default=str)

        print(f"Results saved to {filename}")

    def generate_comparison_report(self):
        """Generate comprehensive comparison report across all simulations"""
        if not self.simulation_results:
            print("No simulation results available")
            return

        print("\n" + "=" * 80)
        print("COMPREHENSIVE SIMULATION RESULTS COMPARISON")
        print("=" * 80)

        for sim_key, results in self.simulation_results.items():
            print(f"\n--- {sim_key.upper()} ---")
            comp = results["comparison"]

            print(
                f"Throughput Improvement: {comp.get('throughput_improvement', 0):+.2f}%"
            )
            print(f"Latency Difference: {comp.get('latency_difference', 0):+.4f} ms")
            print(f"Trade Count Difference: {comp.get('trade_count_difference', 0):+d}")
            print(
                f"Execution Time Difference: {comp.get('execution_time_difference', 0):+.2f} s"
            )

            if "regime_changes" in comp:
                print(f"Regime Changes: {comp['regime_changes']}")

            adaptive = results["adaptive"]
            print(
                f"Adaptive Engine - Final Regime: {adaptive.get('final_regime', 'N/A')}"
            )
