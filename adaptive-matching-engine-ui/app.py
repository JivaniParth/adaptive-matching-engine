"""
Adaptive Matching Engine - Performance Comparison Dashboard
Real-time visualization of Adaptive vs NSE Traditional Matching Engine
"""

import streamlit as st
import sys
import os
import time
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import json
from datetime import datetime

# Add parent directory to path to import matching engine
sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "adaptive-matching-engine")
    ),
)

from src.core.matching_engine import AdaptiveMatchingEngine, BaseMatchingEngine
from src.core.nse_matching_engine import NSEMatchingEngine
from src.data.order_generator import OrderGenerator
from src.core.order_types import OrderSide

# Page configuration
st.set_page_config(
    page_title="Matching Engine Performance Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown(
    """
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        padding: 1rem;
        background: linear-gradient(90deg, #e3f2fd 0%, #bbdefb 100%);
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #1f77b4;
    }
    .stMetric {
        background-color: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
</style>
""",
    unsafe_allow_html=True,
)

# Initialize session state
if "benchmark_results" not in st.session_state:
    st.session_state.benchmark_results = None
if "live_data" not in st.session_state:
    st.session_state.live_data = {"base": [], "nse": [], "adaptive": []}


def run_benchmark(order_count, volatility, adaptive_config=None):
    """Run performance benchmark comparing all three engines"""
    if adaptive_config is None:
        adaptive_config = {}  # Use defaults

    progress_bar = st.progress(0)
    status_text = st.empty()

    generator = OrderGenerator(price_range=(18000.0, 19000.0))
    orders = generator.generate_orders(order_count, volatility=volatility)

    results = {}

    # Test Base Engine
    status_text.text("Testing Base Engine...")
    progress_bar.progress(0.1)
    base_engine = BaseMatchingEngine()

    start = time.perf_counter()
    trades_base = 0
    latencies_base = []

    for order in orders:
        order_start = time.perf_counter()
        trades = base_engine.process_order(order)
        latencies_base.append((time.perf_counter() - order_start) * 1000)
        trades_base += len(trades)

    time_base = time.perf_counter() - start

    results["base"] = {
        "name": "Base Engine (Simple Price-Time)",
        "time": time_base,
        "throughput": order_count / time_base,
        "avg_latency": sum(latencies_base) / len(latencies_base),
        "trades": trades_base,
        "latencies": latencies_base,
    }
    progress_bar.progress(0.4)

    # Test NSE Engine
    status_text.text("Testing NSE Traditional Engine...")
    nse_engine = NSEMatchingEngine(symbol="NIFTY")
    nse_engine.set_reference_price(18500.0)

    orders_nse = generator.generate_orders(order_count, volatility=volatility)

    start = time.perf_counter()
    trades_nse = 0
    latencies_nse = []

    for order in orders_nse:
        order_start = time.perf_counter()
        trades = nse_engine.process_order(order)
        latencies_nse.append((time.perf_counter() - order_start) * 1000)
        trades_nse += len(trades)

    time_nse = time.perf_counter() - start
    nse_stats = nse_engine.get_statistics()

    results["nse"] = {
        "name": "NSE Traditional Engine",
        "time": time_nse,
        "throughput": order_count / time_nse,
        "avg_latency": sum(latencies_nse) / len(latencies_nse),
        "trades": trades_nse,
        "latencies": latencies_nse,
        "circuit_breakers": nse_stats["circuit_breaker_hits"],
    }
    progress_bar.progress(0.7)

    # Test Adaptive Engine
    status_text.text("Testing Adaptive Engine...")
    adaptive_engine = AdaptiveMatchingEngine(config=adaptive_config)

    orders_adaptive = generator.generate_orders(order_count, volatility=volatility)

    start = time.perf_counter()
    trades_adaptive = 0
    latencies_adaptive = []

    for order in orders_adaptive:
        order_start = time.perf_counter()
        trades = adaptive_engine.process_order(order)
        latencies_adaptive.append((time.perf_counter() - order_start) * 1000)
        trades_adaptive += len(trades)

    time_adaptive = time.perf_counter() - start

    results["adaptive"] = {
        "name": "Adaptive Engine",
        "time": time_adaptive,
        "throughput": order_count / time_adaptive,
        "avg_latency": sum(latencies_adaptive) / len(latencies_adaptive),
        "trades": trades_adaptive,
        "latencies": latencies_adaptive,
        "regime_changes": adaptive_engine.regime_change_count,
        "final_regime": adaptive_engine.current_regime.value,
        "regime_stats": adaptive_engine.get_regime_statistics(),
        "config": adaptive_engine.get_config(),
    }

    progress_bar.progress(1.0)
    status_text.text("Benchmark Complete!")
    time.sleep(0.5)
    progress_bar.empty()
    status_text.empty()

    return results


def plot_throughput_comparison(results):
    """Create throughput comparison bar chart"""

    engines = [
        results["base"]["name"],
        results["nse"]["name"],
        results["adaptive"]["name"],
    ]
    throughputs = [
        results["base"]["throughput"],
        results["nse"]["throughput"],
        results["adaptive"]["throughput"],
    ]
    colors = ["#636EFA", "#EF553B", "#00CC96"]

    fig = go.Figure(
        data=[
            go.Bar(
                x=engines,
                y=throughputs,
                marker_color=colors,
                text=[f"{t:,.0f}" for t in throughputs],
                textposition="outside",
            )
        ]
    )

    fig.update_layout(
        title="Throughput Comparison (Orders/Second)",
        yaxis_title="Orders per Second",
        height=400,
        showlegend=False,
    )

    return fig


def plot_latency_comparison(results):
    """Create latency comparison chart"""

    engines = [
        results["base"]["name"],
        results["nse"]["name"],
        results["adaptive"]["name"],
    ]
    latencies = [
        results["base"]["avg_latency"],
        results["nse"]["avg_latency"],
        results["adaptive"]["avg_latency"],
    ]
    colors = ["#636EFA", "#EF553B", "#00CC96"]

    fig = go.Figure(
        data=[
            go.Bar(
                x=engines,
                y=latencies,
                marker_color=colors,
                text=[f"{l:.4f}ms" for l in latencies],
                textposition="outside",
            )
        ]
    )

    fig.update_layout(
        title="Average Latency Comparison (Milliseconds)",
        yaxis_title="Latency (ms)",
        height=400,
        showlegend=False,
    )

    return fig


def plot_latency_distribution(results):
    """Create latency distribution histogram"""

    fig = go.Figure()

    fig.add_trace(
        go.Histogram(
            x=results["base"]["latencies"],
            name=results["base"]["name"],
            opacity=0.7,
            marker_color="#636EFA",
        )
    )

    fig.add_trace(
        go.Histogram(
            x=results["nse"]["latencies"],
            name=results["nse"]["name"],
            opacity=0.7,
            marker_color="#EF553B",
        )
    )

    fig.add_trace(
        go.Histogram(
            x=results["adaptive"]["latencies"],
            name=results["adaptive"]["name"],
            opacity=0.7,
            marker_color="#00CC96",
        )
    )

    fig.update_layout(
        title="Latency Distribution",
        xaxis_title="Latency (ms)",
        yaxis_title="Frequency",
        barmode="overlay",
        height=400,
    )

    return fig


def plot_performance_metrics(results):
    """Create radar chart comparing multiple metrics"""

    # Normalize metrics to 0-100 scale
    max_throughput = max(
        results["base"]["throughput"],
        results["nse"]["throughput"],
        results["adaptive"]["throughput"],
    )
    max_trades = max(
        results["base"]["trades"],
        results["nse"]["trades"],
        results["adaptive"]["trades"],
    )

    categories = ["Throughput", "Trade Execution", "Efficiency"]

    fig = go.Figure()

    fig.add_trace(
        go.Scatterpolar(
            r=[
                (results["base"]["throughput"] / max_throughput) * 100,
                (results["base"]["trades"] / max_trades) * 100,
                100,  # Base as reference
            ],
            theta=categories,
            fill="toself",
            name=results["base"]["name"],
            line_color="#636EFA",
        )
    )

    fig.add_trace(
        go.Scatterpolar(
            r=[
                (results["nse"]["throughput"] / max_throughput) * 100,
                (results["nse"]["trades"] / max_trades) * 100,
                95,  # Slightly lower due to additional checks
            ],
            theta=categories,
            fill="toself",
            name=results["nse"]["name"],
            line_color="#EF553B",
        )
    )

    fig.add_trace(
        go.Scatterpolar(
            r=[
                (results["adaptive"]["throughput"] / max_throughput) * 100,
                (results["adaptive"]["trades"] / max_trades) * 100,
                90,  # Lower due to regime detection
            ],
            theta=categories,
            fill="toself",
            name=results["adaptive"]["name"],
            line_color="#00CC96",
        )
    )

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        showlegend=True,
        title="Overall Performance Comparison",
        height=500,
    )

    return fig


def main():
    # Header
    st.markdown(
        '<div class="main-header">📊 Adaptive Matching Engine Performance Dashboard</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        """
    <div style='background-color: #e8f4f8; padding: 1rem; border-radius: 8px; margin-bottom: 2rem;'>
        <h4 style='margin: 0; color: #0277bd;'>🎯 Compare Performance: Adaptive vs NSE Traditional Engine</h4>
        <p style='margin: 0.5rem 0 0 0;'>Real-time benchmarking and visualization of matching engine performance for Indian markets (NSE/BSE)</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # Sidebar
    st.sidebar.header("⚙️ Benchmark Configuration")

    order_count = st.sidebar.select_slider(
        "Number of Orders", options=[1000, 2500, 5000, 10000, 25000, 50000], value=5000
    )

    volatility = st.sidebar.slider(
        "Market Volatility",
        min_value=0.001,
        max_value=0.05,
        value=0.01,
        step=0.001,
        format="%.3f",
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🎛️ Adaptive Engine Configuration")

    with st.sidebar.expander("⚙️ Regime Detection Settings", expanded=False):
        detection_interval = st.number_input(
            "Detection Interval (orders)",
            min_value=10,
            max_value=500,
            value=100,
            step=10,
            help="How often to check for regime changes (lower = more sensitive, slower)",
        )

        window_size = st.number_input(
            "Analysis Window Size",
            min_value=50,
            max_value=500,
            value=100,
            step=50,
            help="Number of orders to analyze for regime detection",
        )

    with st.sidebar.expander("🎯 Regime Thresholds", expanded=False):
        volatility_threshold = st.slider(
            "Volatility Threshold",
            min_value=0.01,
            max_value=0.20,
            value=0.05,
            step=0.01,
            format="%.2f",
            help="Threshold to trigger HIGH_VOLATILITY regime",
        )

        spread_threshold = st.slider(
            "Spread Threshold",
            min_value=0.005,
            max_value=0.10,
            value=0.02,
            step=0.005,
            format="%.3f",
            help="Threshold to trigger ILLIQUID regime",
        )

        imbalance_threshold = st.slider(
            "Imbalance Threshold",
            min_value=0.3,
            max_value=0.95,
            value=0.5,
            step=0.05,
            format="%.2f",
            help="Threshold to trigger DIRECTIONAL regime",
        )

        cancellation_threshold = st.slider(
            "Cancellation Rate Threshold",
            min_value=0.1,
            max_value=0.7,
            value=0.25,
            step=0.05,
            format="%.2f",
            help="Threshold to trigger HIGH_FREQUENCY regime",
        )

    # Collect adaptive config
    adaptive_config = {
        "detection_interval": int(detection_interval),
        "window_size": int(window_size),
        "volatility_threshold": float(volatility_threshold),
        "spread_threshold": float(spread_threshold),
        "imbalance_threshold": float(imbalance_threshold),
        "cancellation_threshold": float(cancellation_threshold),
    }

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📌 Engine Types")
    st.sidebar.markdown(
        """
    - **Base Engine**: Simple Price-Time Priority
    - **NSE Engine**: Full NSE features (circuit breakers, stop-loss, etc.)
    - **Adaptive Engine**: Regime-based adaptive matching
    """
    )

    if st.sidebar.button("🚀 Run Benchmark", type="primary", use_container_width=True):
        with st.spinner("Running benchmark..."):
            results = run_benchmark(order_count, volatility, adaptive_config)
            st.session_state.benchmark_results = results
            st.session_state.adaptive_config = adaptive_config  # Store config
            st.success("✅ Benchmark completed successfully!")

    # Display results if available
    if st.session_state.benchmark_results:
        results = st.session_state.benchmark_results

        # Show adaptive configuration used
        if "adaptive_config" in st.session_state:
            with st.expander("🔧 View Adaptive Engine Configuration", expanded=False):
                config_data = []
                config_data.append(
                    {
                        "Parameter": "Detection Interval",
                        "Value": str(
                            st.session_state.adaptive_config.get(
                                "detection_interval", 100
                            )
                        ),
                        "Description": "Orders between regime checks",
                    }
                )
                config_data.append(
                    {
                        "Parameter": "Window Size",
                        "Value": str(
                            st.session_state.adaptive_config.get("window_size", 100)
                        ),
                        "Description": "Orders analyzed for metrics",
                    }
                )
                config_data.append(
                    {
                        "Parameter": "Volatility Threshold",
                        "Value": f"{st.session_state.adaptive_config.get('volatility_threshold', 0.05):.2f}",
                        "Description": "Triggers HIGH_VOLATILITY regime",
                    }
                )
                config_data.append(
                    {
                        "Parameter": "Spread Threshold",
                        "Value": f"{st.session_state.adaptive_config.get('spread_threshold', 0.02):.3f}",
                        "Description": "Triggers ILLIQUID regime",
                    }
                )
                config_data.append(
                    {
                        "Parameter": "Imbalance Threshold",
                        "Value": f"{st.session_state.adaptive_config.get('imbalance_threshold', 0.5):.2f}",
                        "Description": "Triggers DIRECTIONAL regime",
                    }
                )
                config_data.append(
                    {
                        "Parameter": "Cancellation Threshold",
                        "Value": f"{st.session_state.adaptive_config.get('cancellation_threshold', 0.25):.2f}",
                        "Description": "Triggers HIGH_FREQUENCY regime",
                    }
                )
                config_df = pd.DataFrame(config_data)
                st.dataframe(config_df, use_container_width=True, hide_index=True)

        # Performance Comparison Charts
        st.subheader("📊 Performance Comparison")

        col1, col2 = st.columns(2)

        with col1:
            st.plotly_chart(
                plot_throughput_comparison(results), use_container_width=True
            )

        with col2:
            st.plotly_chart(plot_latency_comparison(results), use_container_width=True)

        # Latency Distribution
        st.subheader("📉 Latency Distribution Analysis")
        st.plotly_chart(plot_latency_distribution(results), use_container_width=True)

        # Regime Analysis (if adaptive engine was tested)
        if "regime_stats" in results.get("adaptive", {}):
            st.subheader("🔄 Adaptive Engine Regime Analysis")

            regime_stats = results["adaptive"]["regime_stats"]

            st.markdown("#### Regime Distribution")
            if regime_stats["regime_distribution"]:
                regime_df = pd.DataFrame(
                    [
                        {"Regime": regime, "Occurrences": count}
                        for regime, count in regime_stats["regime_distribution"].items()
                    ]
                )

                fig = px.pie(
                    regime_df,
                    values="Occurrences",
                    names="Regime",
                    title="Time Spent in Each Regime",
                    color_discrete_sequence=px.colors.qualitative.Set3,
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No regime changes occurred during the test")

        # Radar Chart
        st.subheader("🎯 Overall Performance Radar")
        st.plotly_chart(plot_performance_metrics(results), use_container_width=True)

        # Detailed Statistics
        st.subheader("📋 Detailed Statistics")

        comparison_df = pd.DataFrame(
            {
                "Engine": [
                    results["base"]["name"],
                    results["nse"]["name"],
                    results["adaptive"]["name"],
                ],
                "Throughput (ops/s)": [
                    f"{results['base']['throughput']:,.0f}",
                    f"{results['nse']['throughput']:,.0f}",
                    f"{results['adaptive']['throughput']:,.0f}",
                ],
                "Avg Latency (ms)": [
                    f"{results['base']['avg_latency']:.4f}",
                    f"{results['nse']['avg_latency']:.4f}",
                    f"{results['adaptive']['avg_latency']:.4f}",
                ],
                "Total Time (s)": [
                    f"{results['base']['time']:.3f}",
                    f"{results['nse']['time']:.3f}",
                    f"{results['adaptive']['time']:.3f}",
                ],
                "Trades Executed": [
                    results["base"]["trades"],
                    results["nse"]["trades"],
                    results["adaptive"]["trades"],
                ],
            }
        )

        st.dataframe(comparison_df, use_container_width=True)

        # Download Results
        st.subheader("💾 Export Results")

        json_results = json.dumps(results, indent=2, default=str)

        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label="📥 Download JSON Results",
                data=json_results,
                file_name=f"benchmark_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
            )

        with col2:
            csv_data = comparison_df.to_csv(index=False)
            st.download_button(
                label="📥 Download CSV Summary",
                data=csv_data,
                file_name=f"benchmark_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
            )

    else:
        # Initial state - show instructions
        st.info(
            "👈 Configure benchmark parameters in the sidebar and click 'Run Benchmark' to start!"
        )

        st.markdown(
            """
        ### 🔍 What This Dashboard Does
        
        This dashboard provides a comprehensive comparison of three matching engines:
        
        1. **Base Engine**: Simple price-time priority matching (baseline)
        2. **NSE Traditional Engine**: Full NSE-style features including:
           - Circuit breakers
           - Stop-loss orders
           - Iceberg orders
           - Price bands
           - Tick size validation
        
        3. **Adaptive Engine**: Smart regime-based matching that adapts to:
           - Normal markets (price-time priority)
           - Volatile markets (price-size-time priority)
           - Illiquid markets (enhanced matching)
           - High-frequency scenarios
        
        ### 📊 Metrics Analyzed
        
        - **Throughput**: Orders processed per second
        - **Latency**: Time to process each order
        - **Trade Execution**: Number of successful trades
        - **Regime Detection**: Adaptive engine's market awareness
        - **Circuit Breakers**: NSE engine's safety mechanisms
        
        ### 🚀 Get Started
        
        1. Select the number of orders to test (1K - 50K)
        2. Adjust market volatility (0.001 - 0.05)
        3. Click "Run Benchmark" to see results
        4. Analyze charts and download results
        """
        )


if __name__ == "__main__":
    main()
