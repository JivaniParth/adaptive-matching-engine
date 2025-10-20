#!/usr/bin/env python3
"""
Test script for Nifty data loader
"""

import sys
import os

# Add the root directory to Python path so we can import src
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from src.data.nifty_loader import NiftyDataLoader
    from src.core.order_types import Order, OrderSide, OrderType

    print("✅ Successfully imported NiftyDataLoader and dependencies")

    # Test the loader
    loader = NiftyDataLoader()
    print("✅ NiftyDataLoader initialized successfully")

    # Test creating a sample order
    order = Order.create_limit_order(OrderSide.BUY, 18000.0, 100)
    print(f"✅ Sample order created: {order.order_id}")

    print("\n🎉 Nifty data loader is working correctly!")

except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running this from the root directory")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback

    traceback.print_exc()
