# NSE-Style Traditional Matching Engine

## Overview

This module provides a comprehensive implementation of a matching engine that closely mimics the National Stock Exchange (NSE) of India's order matching system. It serves as a realistic baseline for comparing against the adaptive matching engine.

## Features

### 1. **Call Auctions**

- **Pre-Open Auction** (9:00-9:15 AM): Collects orders and determines equilibrium opening price
- **Closing Auction** (3:20-3:30 PM): Similar mechanism for closing price
- **Equilibrium Price Calculation**: Maximizes tradeable volume with tie-breaking rules

### 2. **Trading Phases**

- `PRE_OPEN`: Order collection phase (no matching)
- `OPENING`: Opening auction execution
- `CONTINUOUS`: Normal continuous trading with price-time priority
- `CLOSING`: Closing auction
- `POST_CLOSE`: After market close
- `HALTED`: Trading suspended (circuit breaker)

### 3. **Order Types**

- **LIMIT**: Standard limit orders with price and quantity
- **MARKET**: Execute at best available price
- **IOC** (Immediate-or-Cancel): Execute immediately, cancel remainder
- **FOK** (Fill-or-Kill): Execute fully or reject completely
- **STOP_LOSS**: Limit order triggered when stop price is reached
- **STOP_LOSS_MARKET**: Market order triggered when stop price is reached
- **ICEBERG**: Hidden orders with disclosed/visible quantity

### 4. **Order Validity**

- **DAY**: Valid for the trading day
- **IOC**: Immediate-or-Cancel
- **GTC**: Good-Till-Cancelled
- **GTD**: Good-Till-Date

### 5. **Market Protection Mechanisms**

#### Circuit Breakers

- Automatically halt trading when price moves beyond threshold (default: ±10%)
- Based on previous day's closing price (reference price)
- Can be resumed manually

#### Price Bands

- Dynamic upper and lower price limits (default: ±20%)
- Orders outside bands are rejected
- Updated based on reference price

#### Tick Size

- Enforces minimum price movement (default: ₹0.05 for NIFTY)
- Automatically rounds prices to nearest tick

### 6. **Matching Logic**

#### Continuous Trading

- **Price Priority**: Best prices matched first
- **Time Priority**: Within same price, FIFO (First-In-First-Out)
- **Stop-Loss Triggering**: Automatically converts to limit/market when triggered
- **Iceberg Handling**: Only visible quantity shown in order book

#### Call Auction Matching

- Collects all orders during auction phase
- Calculates equilibrium price that maximizes volume
- Executes all matchable orders at single price
- Unmatched orders added to continuous order book

## Architecture Comparison

| Feature             | Base Engine | NSE Engine | Adaptive Engine  |
| ------------------- | ----------- | ---------- | ---------------- |
| Price-Time Priority | ✓           | ✓          | ✓ (regime-based) |
| Market Orders       | ✓           | ✓          | ✓                |
| Limit Orders        | ✓           | ✓          | ✓                |
| Stop-Loss Orders    | ✗           | ✓          | ✗                |
| Iceberg Orders      | ✗           | ✓          | ✗                |
| FOK Orders          | ✗           | ✓          | ✗                |
| Call Auctions       | ✗           | ✓          | ✗                |
| Circuit Breakers    | ✗           | ✓          | ✗                |
| Price Bands         | ✗           | ✓          | ✗                |
| Tick Size           | ✗           | ✓          | ✗                |
| Regime Detection    | ✗           | ✗          | ✓                |
| Adaptive Priority   | ✗           | ✗          | ✓                |

## Usage

### Basic Continuous Trading

```python
from src.core.nse_matching_engine import NSEMatchingEngine
from src.core.order_types import Order, OrderSide, TradingPhase

# Initialize engine
engine = NSEMatchingEngine(
    symbol="NIFTY",
    tick_size=0.05,
    circuit_breaker_pct=10.0,
    price_band_pct=20.0
)

# Set reference price (previous close)
engine.set_reference_price(18000.0)
engine.set_trading_phase(TradingPhase.CONTINUOUS)

# Submit orders
buy_order = Order("B1", OrderSide.BUY, 18000.0, 100, time.time())
sell_order = Order("S1", OrderSide.SELL, 18000.0, 100, time.time())

trades = engine.process_order(buy_order)
trades.extend(engine.process_order(sell_order))

# Check statistics
stats = engine.get_statistics()
print(f"Total trades: {stats['total_trades']}")
```

### Call Auction

```python
# Set to pre-open auction phase
engine.set_trading_phase(TradingPhase.PRE_OPEN)

# Collect orders (no matching yet)
for order in auction_orders:
    engine.process_order(order)

# Execute auction to find equilibrium
trades = engine.execute_call_auction()

print(f"Opening price: ₹{engine.opening_price}")
print(f"Volume: {sum(t.quantity for t in trades)}")
```

### Stop-Loss Orders

```python
from src.core.order_types import OrderType

# Create stop-loss sell order
stop_order = Order(
    "SL1",
    OrderSide.SELL,
    17900.0,  # limit price
    100,
    time.time(),
    order_type=OrderType.STOP_LOSS
)
stop_order.stop_price = 17950.0  # trigger price

# Order stays pending until stop price hit
engine.process_order(stop_order)

# When market drops to 17950, order becomes active
```

### Iceberg Orders

```python
iceberg = Order(
    "ICE1",
    OrderSide.BUY,
    18000.0,
    1000,  # total quantity
    time.time(),
    order_type=OrderType.ICEBERG
)
iceberg.disclosed_quantity = 100  # only 100 visible

engine.process_order(iceberg)
print(f"Visible: {iceberg.visible_quantity}")  # 100
print(f"Total: {iceberg.quantity}")  # 1000
```

### Fill-or-Kill Orders

```python
fok_order = Order(
    "FOK1",
    OrderSide.BUY,
    18010.0,
    500,
    time.time(),
    order_type=OrderType.FOK
)

trades = engine.process_order(fok_order)
if not trades:
    print("FOK rejected - insufficient liquidity")
```

## Running Examples

### Demo Script

```bash
python examples/nse_engine_demo.py
```

Demonstrates:

- Call auction execution
- Circuit breaker triggering
- Stop-loss order triggering
- Iceberg order matching
- FOK order handling

### Performance Benchmark

```bash
python tools/run_bench_comparison.py
```

Compares:

- Base matching engine (simple)
- NSE matching engine (full features)
- Adaptive matching engine

### Unit Tests

```bash
python -m pytest tests/test_nse_engine.py -v
```

Tests all NSE engine features including edge cases.

## Implementation Details

### Call Auction Algorithm

1. **Order Collection**: Accumulate orders during auction phase
2. **Price Discovery**:
   - For each potential price, calculate buy volume (all buys ≥ price)
   - Calculate sell volume (all sells ≤ price)
   - Tradeable volume = min(buy_volume, sell_volume)
3. **Equilibrium Selection**:
   - Choose price with maximum tradeable volume
   - Tie-breaker: price closest to reference price
4. **Matching**: Execute all orders at equilibrium price in time priority
5. **Transition**: Add unmatched orders to continuous order book

### Circuit Breaker Logic

```python
price_change_pct = |trade_price - reference_price| / reference_price * 100

if price_change_pct >= circuit_breaker_threshold:
    halt_trading()
    trading_phase = HALTED
```

### Stop-Loss Triggering

**Buy Stop-Loss**: Triggers when market_price ≥ stop_price
**Sell Stop-Loss**: Triggers when market_price ≤ stop_price

When triggered:

- `STOP_LOSS` → converts to `LIMIT` order
- `STOP_LOSS_MARKET` → converts to `MARKET` order

## Performance Characteristics

### Computational Complexity

- Order insertion: O(log n) average
- Order matching: O(1) per price level
- Call auction: O(n log n) for sorting
- Circuit breaker check: O(1)

### Memory Usage

- Order book: O(n) for n orders
- Price levels: O(p) for p unique prices
- Pending stop orders: O(s) for s stop orders

### Throughput

Typical performance on modern hardware:

- Base Engine: ~500K orders/sec
- NSE Engine: ~250K orders/sec (with all features)
- Adaptive Engine: ~200K orders/sec (with regime detection)

The NSE engine has ~2x overhead compared to base engine due to:

- Circuit breaker checks
- Price band validation
- Tick size rounding
- Stop-loss order management
- Iceberg order handling

## Limitations & Simplifications

Compared to real NSE system:

1. **Pro-Rata Matching**: Not implemented (NSE uses for some contracts)
2. **Order Modification**: Basic - doesn't handle all modification types
3. **Market Depth Broadcasting**: No real-time depth updates
4. **Member/Participant Logic**: No member ID or risk checks
5. **Settlement Integration**: No clearing/settlement simulation
6. **Regulatory Checks**: Simplified compared to exchange requirements
7. **Multi-Symbol**: Single symbol focus (no cross-symbol logic)
8. **Time Precision**: Uses seconds, NSE uses nanosecond precision
9. **Recovery/Persistence**: In-memory only, no crash recovery
10. **Network Layer**: Direct function calls, no network protocol

## Future Enhancements

Potential additions to make it even closer to NSE:

- [ ] Pro-rata matching for bulk orders
- [ ] Order modification with proper validation
- [ ] Market-by-order (MBO) data feed
- [ ] Multiple trading symbols
- [ ] Member risk limits
- [ ] Position limits and margin checks
- [ ] Trade reporting and audit logs
- [ ] Snapshot and recovery mechanisms
- [ ] Network protocol simulation (FIX/OUCH)
- [ ] Clearing and settlement simulation

## References

- [NSE Trading System Documentation](https://www.nseindia.com/)
- NSE Circulars on Market Microstructure
- SEBI Regulations on Circuit Breakers and Price Bands

## License

Part of the Adaptive Matching Engine research project.
