# Adaptive Heap-Based Order Matching Engine

A high-performance, adaptive order matching engine that dynamically adjusts its matching logic based on market regimes.

## 🚀 Quick Start

### 1. Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

### 2. Run the Application

```bash
# Basic demonstration
python main.py demo

# Performance benchmark
python main.py performance

# Regime detection demo
python main.py regime

# Analyze Nifty data (if you have data files)
python main.py nifty --symbol NIFTY --year 2020

# List saved results
python main.py results

# Show help
python main.py help
```

## 📁 Project Structure

```
adaptive-matching-engine/
│
├── main.py                    ← **START HERE** - Main entry point
│
├── config/                    ← Configuration files
│   └── default_config.py
│
├── src/                       ← Source code
│   ├── core/                  ← Core matching engine
│   │   ├── matching_engine.py ← Main engine logic
│   │   ├── order_book.py      ← Order book implementation
│   │   └── order_types.py     ← Data types
│   │
│   ├── adaptive/              ← Adaptive logic
│   │   ├── regime_detector.py ← Market regime detection
│   │   ├── adaptive_priority.py
│   │   └── policies.py
│   │
│   ├── data/                  ← Data handling
│   │   ├── order_generator.py ← Generate test orders
│   │   ├── nifty_loader.py    ← Load Nifty data
│   │   └── market_data.py
│   │
│   └── utils/                 ← Utilities
│       ├── performance.py     ← Performance monitoring
│       ├── logger.py
│       └── validators.py
│
├── examples/                  ← Example scripts
│   ├── basic_usage.py
│   ├── performance_benchmark.py
│   └── nifty_analysis.py
│
├── tests/                     ← Unit tests
│   ├── test_matching_engine.py
│   ├── test_order_book.py
│   └── test_regime_detector.py
│
├── results/                   ← **OUTPUT FILES** (auto-created)
│   └── *.json                 ← Benchmark results
│
├── data/                      ← Input data (you provide)
│   └── NIFTY_*_intraday.csv   ← Nifty data files
│
└── requirements.txt           ← Dependencies
```

## 🎯 Main Features

1. **Adaptive Matching**: Switches between Price-Time, Price-Size-Time, and other priority rules
2. **Regime Detection**: Automatically detects market conditions (normal, volatile, illiquid)
3. **High Performance**: O(1) cancellation, O(log M) insertion
4. **Results Tracking**: All results saved to `results/` folder

## 📊 Usage Examples

### Example 1: Basic Demo

```bash
python main.py demo
```

Shows how the engine processes orders and generates trades.

### Example 2: Performance Test

```bash
# Test with 10,000 orders
python main.py performance --orders 10000
```

Results saved to: `results/performance_test_YYYYMMDD_HHMMSS.json`

### Example 3: Nifty Data Analysis

```bash
# First, place your data file in: data/NIFTY_2020_intraday.csv
python main.py nifty --symbol NIFTY --year 2020 --sample 5000
```

Results saved to: `results/nifty_analysis_NIFTY_2020_YYYYMMDD_HHMMSS.json`

### Example 4: Check Results

```bash
python main.py results
```

Lists all saved result files in `results/` folder.

## 📋 Nifty Data Format

If you want to analyze Nifty data, place your CSV files in the `data/` folder:

```
data/
├── NIFTY_2020_intraday.csv
├── NIFTY_2021_intraday.csv
└── BANKNIFTY_2020_intraday.csv
```

**Flexible column names supported:**

- Timestamp: `timestamp`, `time`, `datetime`, `date`
- Price: `price`, `close`, `last`, `ltp`
- Volume: `volume`, `quantity`, `qty`
- Bid/Ask: `bid`, `ask`, `bid_price`, `ask_price`

## 🧪 Running Tests

```bash
# Run all tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_matching_engine.py

# Run with verbose output
python -m pytest tests/ -v
```

## 📈 Understanding Results

Results are saved as JSON files in `results/` folder:

### Performance Test Result

```json
{
  "timestamp": "20241026_143022",
  "order_count": 5000,
  "static_engine": {
    "throughput_ops": 1134285.52,
    "avg_latency_ms": 0.000768
  },
  "adaptive_engine": {
    "throughput_ops": 12007.31,
    "avg_latency_ms": 0.083053,
    "regime_changes": 12
  }
}
```

### Nifty Analysis Result

```json
{
  "symbol": "NIFTY",
  "year": 2020,
  "orders_generated": 4000,
  "adaptive_engine": {
    "trades": 1250,
    "regime_changes": 8,
    "final_regime": "HIGH_VOLATILITY"
  }
}
```

## 🔧 Configuration

Edit `config/default_config.py` to customize:

- Regime detection thresholds
- Performance monitoring settings
- Order validation rules
- Logging configuration

## 💡 Key Files Explained

### Main Entry Point

- **`main.py`** - Run this file for everything! No need to navigate complex folders.

### Core Engine Files

- **`src/core/matching_engine.py`** - The main matching engine logic

  - `BaseMatchingEngine` - Basic Price-Time priority
  - `AdaptiveMatchingEngine` - Adaptive regime-based matching

- **`src/core/order_book.py`** - Order book implementation
  - Heap-based price level management
  - O(1) order cancellation

### Adaptive Logic

- **`src/adaptive/regime_detector.py`** - Detects market regimes
  - Monitors volatility, spread, volume imbalance
  - Triggers regime changes

### Data Handling

- **`src/data/order_generator.py`** - Generates test orders
- **`src/data/nifty_loader.py`** - Loads Nifty/Bank Nifty data

### Utilities

- **`src/utils/performance.py`** - Performance monitoring
- **`src/utils/logger.py`** - Logging utilities

## 🎓 Learning Path

1. **Start here**: `python main.py demo`
2. **Understand performance**: `python main.py performance --orders 1000`
3. **See regime detection**: `python main.py regime`
4. **Check results**: `python main.py results`
5. **Read the code**: Start with `src/core/matching_engine.py`
6. **Run tests**: `python -m pytest tests/`

## ❓ Common Questions

### Q: Where are my results?

**A:** Check the `results/` folder. Run `python main.py results` to list all files.

### Q: Which file should I run?

**A:** Always run `main.py` - it's your main entry point!

### Q: How do I add my own data?

**A:** Place CSV files in `data/` folder, then run:

```bash
python main.py nifty --symbol YOUR_SYMBOL --year 2020
```

### Q: Can I run without Nifty data?

**A:** Yes! Use synthetic data:

```bash
python main.py demo
python main.py performance
python main.py regime
```

### Q: How do I see detailed logs?

**A:** Use the log level flag:

```bash
python main.py demo --log-level DEBUG
```

## 📞 Support

If you encounter issues:

1. Check `results/` folder exists and is writable
2. Ensure you're running from project root directory
3. Verify Python version >= 3.8
4. Check all dependencies are installed: `pip install -r requirements.txt`

## 📜 License

This project is for educational and research purposes.

---

**Remember:** Always start with `python main.py` - it's your command center! 🎯
