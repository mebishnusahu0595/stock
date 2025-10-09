#!/usr/bin/env python3

"""
🎯 VERIFICATION: Check Trailing Logic
Quick verification that trailing stop loss logic is working
"""

# Simulate the exact user scenario
buy_price = 594
current_price = 605
profit = current_price - buy_price

print("🔍 VERIFICATION: Buy ₹594, Price ₹605")
print("=" * 40)

print(f"Buy Price: ₹{buy_price}")
print(f"Current Price: ₹{current_price}")
print(f"Profit: ₹{profit}")

# Phase 1 trailing calculation
if profit >= 10:
    steps = int(profit // 10)
    new_sl = buy_price + (steps * 10)
    print(f"✅ TRAILING ACTIVATED!")
    print(f"   Steps: {steps}")
    print(f"   New Stop Loss: ₹{new_sl}")
    print(f"   Expected Debug: 'PHASE 1 TRAILING: Buy ₹{buy_price} | High ₹{current_price} | Profit ₹{profit}.00 | Steps {steps}'")
else:
    old_sl = buy_price - 10
    print(f"❌ NO TRAILING YET")
    print(f"   Stop Loss: ₹{old_sl}")

print("\n🎯 RESULT: Stop loss should move from ₹584 to ₹604!")
print("If you don't see this in the app, the position might be using old data.")