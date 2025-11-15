"""
NSE Matching Engine Demo

Demonstrates the features of the NSE-style matching engine including:
- Call auctions (opening/closing)
- Circuit breakers
- Stop-loss orders
- Iceberg orders
- Fill-or-Kill orders
"""

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.core.nse_matching_engine import NSEMatchingEngine
from src.core.order_types import (
    Order,
    OrderSide,
    OrderType,
    OrderValidity,
    TradingPhase,
)
import time


def demo_call_auction():
    """Demonstrate opening call auction."""
    print("\n" + "=" * 70)
    print("DEMO 1: OPENING CALL AUCTION")
    print("=" * 70 + "\n")

    engine = NSEMatchingEngine(symbol="NIFTY", tick_size=0.05)
    engine.set_trading_phase(TradingPhase.PRE_OPEN)
    engine.set_reference_price(18000.0)

    print("Phase: PRE-OPEN AUCTION")
    print("Accumulating orders...\n")

    # Add buy orders
    buy1 = Order("B1", OrderSide.BUY, 18010.0, 100, time.time())
    buy2 = Order("B2", OrderSide.BUY, 18005.0, 200, time.time())
    buy3 = Order("B3", OrderSide.BUY, 18000.0, 150, time.time())

    # Add sell orders
    sell1 = Order("S1", OrderSide.SELL, 18005.0, 120, time.time())
    sell2 = Order("S2", OrderSide.SELL, 18010.0, 180, time.time())
    sell3 = Order("S3", OrderSide.SELL, 18015.0, 100, time.time())

    orders = [buy1, buy2, buy3, sell1, sell2, sell3]

    for order in orders:
        engine.process_order(order)
        print(f"  Added: {order.side.value} {order.quantity}@{order.price}")

    print("\nExecuting call auction...")
    trades = engine.execute_call_auction()

    print(f"\n✓ Auction completed!")
    print(f"  Equilibrium Price: ₹{engine.opening_price}")
    print(f"  Trades Executed: {len(trades)}")
    print(f"  Total Volume: {sum(t.quantity for t in trades)}")

    print("\nTrades:")
    for trade in trades:
        print(f"  {trade.quantity}@₹{trade.price}")

    print(f"\nEngine now in {engine.trading_phase.value} phase")


def demo_circuit_breaker():
    """Demonstrate circuit breaker functionality."""
    print("\n" + "=" * 70)
    print("DEMO 2: CIRCUIT BREAKER")
    print("=" * 70 + "\n")

    engine = NSEMatchingEngine(
        symbol="NIFTY",
        circuit_breaker_pct=5.0,  # 5% circuit breaker
        price_band_pct=10.0,
    )

    reference_price = 18000.0
    engine.set_reference_price(reference_price)
    engine.set_trading_phase(TradingPhase.CONTINUOUS)

    print(f"Reference Price: ₹{reference_price}")
    print(f"Circuit Breaker: ±5%")
    print(f"Upper Band: ₹{engine.upper_band:.2f}")
    print(f"Lower Band: ₹{engine.lower_band:.2f}\n")

    # Add orders that would trigger circuit breaker
    print("Adding orders near circuit breaker threshold...")

    # Seller at very low price
    sell_order = Order("S1", OrderSide.SELL, 17000.0, 100, time.time())
    engine.process_order(sell_order)

    # Buyer willing to pay (this will trigger circuit breaker)
    buy_order = Order("B1", OrderSide.BUY, 17000.0, 100, time.time())
    trades = engine.process_order(buy_order)

    if trades:
        print(f"\n⚠️  Trade executed at ₹{trades[0].price}")
        print(
            f"   Price change: {abs(trades[0].price - reference_price) / reference_price * 100:.2f}%"
        )

    if engine.is_halted:
        print("\n🛑 CIRCUIT BREAKER TRIGGERED!")
        print(f"   Trading halted in {engine.trading_phase.value} phase")
        print(f"   Circuit breaker hits: {engine.circuit_breaker_hits}")

    # Resume trading
    print("\n   Resuming trading...")
    engine.resume_trading()
    print(f"   Trading phase: {engine.trading_phase.value}")


def demo_stop_loss_orders():
    """Demonstrate stop-loss order triggering."""
    print("\n" + "=" * 70)
    print("DEMO 3: STOP-LOSS ORDERS")
    print("=" * 70 + "\n")

    engine = NSEMatchingEngine(symbol="NIFTY")
    engine.set_trading_phase(TradingPhase.CONTINUOUS)
    engine.last_traded_price = 18000.0

    print(f"Current Market Price: ₹{engine.last_traded_price}\n")

    # Add resting sell order
    sell_order = Order("S1", OrderSide.SELL, 17950.0, 100, time.time())
    engine.process_order(sell_order)
    print(f"Added resting sell order: 100@₹17950")

    # Add stop-loss sell order (trigger at 17980)
    print("\nAdding Stop-Loss Sell order:")
    print("  Stop Price: ₹17980")
    print("  Limit Price: ₹17950")

    stop_order = Order(
        "SL1",
        OrderSide.SELL,
        17950.0,  # limit price
        50,
        time.time(),
        order_type=OrderType.STOP_LOSS,
        stop_price=17980.0,  # Set in constructor
    )

    trades = engine.process_order(stop_order)
    print(f"  Status: Order placed (not triggered yet)")
    print(f"  Pending stop orders: {len(engine.pending_stop_orders)}")

    # Market moves down - trigger stop loss
    print("\n📉 Market drops to ₹17975")
    buy_trigger = Order("B1", OrderSide.BUY, 17975.0, 10, time.time())
    trades = engine.process_order(buy_trigger)

    if trades:
        engine.last_traded_price = trades[-1].price
        print(f"  Trade executed at ₹{trades[-1].price}")

    # Check if stop loss was triggered
    print(f"\n  Pending stop orders: {len(engine.pending_stop_orders)}")
    if len(engine.pending_stop_orders) == 0:
        print("  ✓ Stop-loss order was triggered and executed!")


def demo_iceberg_orders():
    """Demonstrate iceberg (hidden) orders."""
    print("\n" + "=" * 70)
    print("DEMO 4: ICEBERG ORDERS")
    print("=" * 70 + "\n")

    engine = NSEMatchingEngine(symbol="NIFTY")
    engine.set_trading_phase(TradingPhase.CONTINUOUS)

    print("Adding Iceberg Buy Order:")
    print("  Total Quantity: 1000")
    print("  Disclosed Quantity: 100 (only 100 visible at a time)\n")

    # Add iceberg buy order
    iceberg = Order(
        "ICE1",
        OrderSide.BUY,
        18000.0,
        1000,  # total quantity
        time.time(),
        order_type=OrderType.ICEBERG,
        disclosed_quantity=100,  # Set in constructor
    )

    engine.process_order(iceberg)

    print(f"  Total quantity in book: {iceberg.quantity}")
    print(f"  Visible quantity: {iceberg.visible_quantity}")

    # Add sell order to match
    print("\nAdding sell order: 150@₹18000")
    sell_order = Order("S1", OrderSide.SELL, 18000.0, 150, time.time())
    trades = engine.process_order(sell_order)

    print(f"\n  Trades executed: {len(trades)}")
    print(f"  Volume traded: {sum(t.quantity for t in trades)}")
    print(f"  Iceberg remaining: {iceberg.remaining_quantity}")
    print(f"  Iceberg visible: {iceberg.visible_quantity}")


def demo_fok_orders():
    """Demonstrate Fill-or-Kill orders."""
    print("\n" + "=" * 70)
    print("DEMO 5: FILL-OR-KILL (FOK) ORDERS")
    print("=" * 70 + "\n")

    engine = NSEMatchingEngine(symbol="NIFTY")
    engine.set_trading_phase(TradingPhase.CONTINUOUS)

    # Add liquidity
    print("Adding resting sell orders:")
    sell1 = Order("S1", OrderSide.SELL, 18010.0, 50, time.time())
    sell2 = Order("S2", OrderSide.SELL, 18015.0, 50, time.time())
    engine.process_order(sell1)
    engine.process_order(sell2)
    print("  50@₹18010, 50@₹18015")

    # Try FOK that can be filled
    print("\nFOK Buy Order #1: 80@₹18020 (can be filled)")
    fok1 = Order(
        "FOK1", OrderSide.BUY, 18020.0, 80, time.time(), order_type=OrderType.FOK
    )
    trades1 = engine.process_order(fok1)

    if trades1:
        print(
            f"  ✓ FOK executed: {len(trades1)} trades, {sum(t.quantity for t in trades1)} volume"
        )
    else:
        print(f"  ✗ FOK rejected (cannot fill)")

    # Try FOK that cannot be filled
    print("\nFOK Buy Order #2: 200@₹18020 (cannot be filled)")
    fok2 = Order(
        "FOK2", OrderSide.BUY, 18020.0, 200, time.time(), order_type=OrderType.FOK
    )
    trades2 = engine.process_order(fok2)

    if trades2:
        print(
            f"  ✓ FOK executed: {len(trades2)} trades, {sum(t.quantity for t in trades2)} volume"
        )
    else:
        print(f"  ✗ FOK rejected (insufficient liquidity)")


def demo_statistics():
    """Show engine statistics."""
    print("\n" + "=" * 70)
    print("ENGINE STATISTICS")
    print("=" * 70 + "\n")

    engine = NSEMatchingEngine(symbol="NIFTY")
    engine.set_reference_price(18000.0)
    engine.set_trading_phase(TradingPhase.CONTINUOUS)

    # Generate some activity
    for i in range(10):
        buy = Order(f"B{i}", OrderSide.BUY, 18000.0 - i, 100, time.time())
        sell = Order(f"S{i}", OrderSide.SELL, 18000.0 + i, 100, time.time())
        engine.process_order(buy)
        engine.process_order(sell)

    stats = engine.get_statistics()

    print("Engine Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")


def main():
    """Run all demos."""
    print("\n" + "=" * 70)
    print("NSE MATCHING ENGINE DEMONSTRATION")
    print("=" * 70)

    demo_call_auction()
    demo_circuit_breaker()
    demo_stop_loss_orders()
    demo_iceberg_orders()
    demo_fok_orders()
    demo_statistics()

    print("\n" + "=" * 70)
    print("✓ All demos completed!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
