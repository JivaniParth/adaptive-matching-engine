# Adaptive Matching Engine - Performance Dashboard UI

A comprehensive web-based dashboard for comparing the performance of Adaptive and NSE Traditional matching engines.

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd adaptive-matching-engine-ui
pip install -r requirements.txt
```

### 2. Run the Dashboard

```bash
streamlit run app.py
```

The dashboard will open in your browser at `http://localhost:8501`

## 📊 Features

### Real-Time Performance Comparison

Compare three matching engines:

- **Base Engine**: Simple price-time priority (baseline)
- **NSE Traditional Engine**: Full NSE features (circuit breakers, stop-loss, price bands)
- **Adaptive Engine**: Regime-based adaptive matching

### Visualization Charts

1. **Throughput Comparison**: Orders processed per second
2. **Latency Analysis**: Average processing time per order
3. **Latency Distribution**: Histogram of response times
4. **Performance Radar**: Multi-metric comparison
5. **Detailed Statistics**: Comprehensive metrics table

### Benchmark Configuration

- **Order Count**: Test with 1K to 50K orders
- **Volatility Control**: Adjust market conditions (0.001 - 0.05)
- **Real-time Progress**: Live progress indicators during testing

### Export Capabilities

- Download results as JSON
- Export summary as CSV
- Save for further analysis

## 📁 Project Structure

```
adaptive-matching-engine-ui/
├── app.py                  # Main Streamlit dashboard
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## 🎯 Usage Guide

### Step 1: Configure Benchmark

1. Open the sidebar (left panel)
2. Select number of orders to test
3. Adjust market volatility level
4. Click "Run Benchmark"

### Step 2: Analyze Results

View comprehensive metrics:

- **Throughput**: How many orders/second each engine processes
- **Latency**: How quickly each order is processed
- **Trades**: Number of successful trades executed
- **Special Features**:
  - NSE: Circuit breaker hits
  - Adaptive: Regime changes and final regime

### Step 3: Compare Performance

Interactive charts show:

- Bar charts for throughput and latency comparison
- Histogram for latency distribution
- Radar chart for overall performance
- Detailed statistics table

### Step 4: Export Results

Download results for:

- Further analysis
- Documentation
- Research papers
- Performance tracking

## 💡 Understanding the Engines

### Base Engine (Baseline)

- Simple price-time priority
- No special features
- Fastest raw performance
- Reference for comparison

### NSE Traditional Engine

- Mimics real NSE matching logic
- Circuit breakers (±10% threshold)
- Price bands (±20% limits)
- Stop-loss order support
- Iceberg orders
- Tick size validation (₹0.05)
- More realistic but slower

### Adaptive Engine

- Detects market regimes automatically
- Switches matching strategy:
  - **Normal**: Price-time priority
  - **Volatile**: Price-size-time priority
  - **Illiquid**: Enhanced matching
  - **High-Frequency**: Optimized handling
- Balances performance and intelligence

## 📊 Sample Results

Typical performance (5,000 orders):

| Engine   | Throughput  | Avg Latency | Trades |
| -------- | ----------- | ----------- | ------ |
| Base     | ~500K ops/s | 0.002 ms    | 2,450  |
| NSE      | ~250K ops/s | 0.004 ms    | 2,430  |
| Adaptive | ~200K ops/s | 0.005 ms    | 2,440  |

_Note: Results vary based on hardware and configuration_

## 🔧 Configuration Options

### Sidebar Controls

**Number of Orders**

- Range: 1,000 - 50,000
- Default: 5,000
- Impact: Longer tests show sustained performance

**Market Volatility**

- Range: 0.001 - 0.05
- Default: 0.01
- Impact: Higher volatility triggers more regime changes

## 🎨 Dashboard Sections

### 1. Key Performance Metrics

Three-column layout showing:

- Throughput (orders/second)
- Average latency (milliseconds)
- Total trades executed
- Engine-specific metrics

### 2. Performance Comparison Charts

- **Throughput Bar Chart**: Direct comparison
- **Latency Bar Chart**: Processing time comparison

### 3. Latency Distribution

- Overlaid histograms showing response time distribution
- Helps identify outliers and consistency

### 4. Performance Radar

- Multi-dimensional comparison
- Normalized metrics (0-100 scale)
- Shows overall balance

### 5. Detailed Statistics Table

- Comprehensive metrics
- Formatted for easy reading
- Sortable columns

### 6. Export Options

- JSON: Full detailed results
- CSV: Summary table

## 🚨 System Requirements

- Python 3.8+
- 4GB RAM minimum (8GB recommended)
- Modern web browser (Chrome, Firefox, Edge)
- The matching engine project must be in the parent directory

## 📂 Directory Structure

```
Implementation/
├── adaptive-matching-engine/          # Main engine project
│   ├── src/
│   │   ├── core/
│   │   ├── adaptive/
│   │   └── data/
│   └── ...
│
└── adaptive-matching-engine-ui/       # This UI project
    ├── app.py
    ├── requirements.txt
    └── README.md
```

## 🐛 Troubleshooting

### Import Error: Module not found

**Solution**: Make sure the matching engine is in the parent directory:

```
Implementation/
├── adaptive-matching-engine/
└── adaptive-matching-engine-ui/
```

### Streamlit Not Starting

**Solution**: Install streamlit:

```bash
pip install streamlit
```

### Charts Not Displaying

**Solution**: Install plotly:

```bash
pip install plotly
```

### Performance Issues

**Solution**:

- Reduce order count
- Close other applications
- Use lower volatility setting

## 💻 Development

### Running in Development Mode

```bash
streamlit run app.py --server.runOnSave true
```

### Customizing the Dashboard

Edit `app.py` to:

- Add new visualizations
- Modify chart styles
- Add custom metrics
- Change color schemes

## 📝 Notes

- The dashboard imports the matching engine from the parent directory
- Results are stored in session state (cleared on refresh)
- Export feature saves results with timestamp
- All prices shown in INR (₹) for Indian markets

## 🎓 For Research/Academic Use

This dashboard is ideal for:

- Performance analysis
- Algorithm comparison
- Research paper demonstrations
- Academic presentations
- Thesis/dissertation work

## 📧 Support

For issues related to:

- **UI**: Check this README and Streamlit documentation
- **Matching Engine**: See the main project's README
- **Performance**: Adjust benchmark parameters

## 🔄 Updates

The dashboard automatically uses the latest matching engine code. No separate updates needed.

## ⚡ Performance Tips

1. **Start Small**: Begin with 1K-5K orders
2. **Gradual Increase**: Scale up to test limits
3. **Monitor Resources**: Watch CPU/RAM usage
4. **Compare Fairly**: Same order count for all tests
5. **Multiple Runs**: Average results across runs

## 📊 Understanding Results

### Good Performance

- Base: 400K+ ops/s
- NSE: 200K+ ops/s
- Adaptive: 150K+ ops/s

### Expected Latency

- Base: 0.001-0.005 ms
- NSE: 0.003-0.010 ms
- Adaptive: 0.004-0.015 ms

### Regime Changes

- Normal market: 0-2 changes
- Volatile market: 5-15 changes
- Optimal: Adapts to conditions

---

**Built with**: Streamlit, Plotly, Python
**For**: Adaptive Matching Engine Research Project
**Market**: Indian Stock Markets (NSE/BSE)
