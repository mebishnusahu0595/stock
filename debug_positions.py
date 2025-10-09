#!/usr/bin/env python3

"""
🎯 DEBUG: Why Trailing Stop Loss Not Working
Checking the actual position data and algorithm status
"""

import requests
import json

print("=" * 80)
print("🎯 DEBUGGING: Why Trailing Stop Loss Not Working")
print("=" * 80)

try:
    # Check positions API
    response = requests.get('http://127.0.0.1:5000/api/positions', timeout=5)
    if response.status_code == 200:
        positions = response.json()
        print(f"\n✅ API Connection: Working")
        print(f"📊 Positions Found: {len(positions)}")

        for i, pos in enumerate(positions):
            print(f"\n🔍 POSITION {i+1}: {pos.get('strike', 'N/A')} {pos.get('type', 'N/A')}")
            print(f"   Buy Price: ₹{pos.get('buy_price', 'N/A')}")
            print(f"   Current Price: ₹{pos.get('current_price', 'N/A')}")
            print(f"   Stop Loss: ₹{pos.get('stop_loss_price', 'N/A')}")
            print(f"   Algorithm Phase: {pos.get('algorithm_phase', 'N/A')}")
            print(f"   Manual Buy Price: ₹{pos.get('manual_buy_price', 'N/A')}")
            print(f"   Highest Price: ₹{pos.get('highest_price', 'N/A')}")
            print(f"   Advanced Stop Loss: ₹{pos.get('advanced_stop_loss', 'N/A')}")

            # Check if trailing should be active
            if pos.get('manual_buy_price') and pos.get('highest_price'):
                profit = pos['highest_price'] - pos['manual_buy_price']
                print(f"   Profit: ₹{profit}")
                if profit >= 10:
                    steps = int(profit // 10)
                    expected_sl = pos['manual_buy_price'] + (steps * 10)
                    print(f"   ✅ SHOULD BE TRAILING: Steps {steps}, Expected SL ₹{expected_sl}")
                else:
                    print(f"   ⏳ WAITING FOR PROFIT: Need ₹{10 - profit} more for trailing")

    else:
        print(f"❌ API Error: {response.status_code}")
        print("   → App might not be running or API issue")

except requests.exceptions.RequestException as e:
    print(f"❌ Connection Error: {e}")
    print("   → App is not running on http://127.0.0.1:5000")

print(f"\n🔧 POSSIBLE ISSUES:")
print("-" * 50)
print("1. ❓ App not running")
print("2. ❓ No positions created yet")
print("3. ❓ Position missing manual_buy_price")
print("4. ❓ Algorithm not set to 'advanced'")
print("5. ❓ Position not in Phase 1")
print("6. ❓ Price not moved +₹10 above buy price")

print(f"\n🚀 NEXT STEPS:")
print("-" * 50)
print("1. Open browser to http://127.0.0.1:5000")
print("2. Create a manual position")
print("3. Run this debug script again")
print("4. Check if trailing activates when price moves up")

print("=" * 80)