# Adaptive Heap-Based Order Matching Engine

A high-performance, adaptive order matching engine that dynamically adjusts its matching logic based on market regimes.

## Features

- **Adaptive Matching**: Switches between Price-Time, Price-Size-Time, and other priority rules
- **Regime Detection**: Automatically detects market conditions (normal, volatile, illiquid)
- **High Performance**: O(1) cancellation, O(log M) insertion where M is price levels
- **Modular Design**: Easy to extend with new regimes and matching algorithms
