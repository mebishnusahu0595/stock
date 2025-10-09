#!/usr/bin/env python3

"""
🎯 DEBUGGING: Stop Loss Not Moving Issue
Testing why stop loss doesn't move when price goes from ₹594 to ₹605+

USER ISSUE:
"buy 594 !! sl = price reaches more than 605 !! then why stop loss is notmoved ?"

Expected behavior:
- Buy: ₹594
- Price: ₹605 (₹11 profit)
- Stop Loss should move from ₹584 to ₹604
"""

print("=" * 80)
print("🎯 DEBUGGING: Stop Loss Not Moving")
print("=" * 80)

print("\n📊 USER'S SCENARIO:")
print("-" * 50)
buy_price = 594
current_price = 605
initial_sl = buy_price - 10  # 584
profit = current_price - buy_price

print(f"Buy Price: ₹{buy_price}")
print(f"Current Price: ₹{current_price}")
print(f"Profit: ₹{profit}")
print(f"Initial Stop Loss: ₹{initial_sl}")

print(f"\n🧪 EXPECTED TRAILING CALCULATION:")
print("-" * 50)

# Phase 1 trailing logic simulation
if profit >= 10:
    trailing_step = 10
    profit_steps = int(profit // trailing_step)
    trailing_stop_loss = buy_price + (profit_steps * trailing_step)
    minimum_sl = buy_price - 10
    final_sl = max(trailing_stop_loss, minimum_sl)
    
    print(f"✅ Profit ≥ ₹10: {profit} ≥ 10")
    print(f"✅ Profit Steps: int({profit} // 10) = {profit_steps}")
    print(f"✅ Trailing SL: ₹{buy_price} + ({profit_steps} × 10) = ₹{trailing_stop_loss}")
    print(f"✅ Minimum SL: ₹{minimum_sl}")
    print(f"✅ Final SL: max(₹{trailing_stop_loss}, ₹{minimum_sl}) = ₹{final_sl}")
    
    print(f"\n🎯 EXPECTED RESULT:")
    print(f"   Stop Loss should move from ₹{initial_sl} → ₹{final_sl}")
else:
    print(f"❌ Profit < ₹10: {profit} < 10")
    print(f"❌ No trailing, SL stays at ₹{initial_sl}")

print(f"\n🔍 POSSIBLE REASONS WHY SL NOT MOVING:")
print("-" * 50)
print("1. ❓ Position might be in wrong phase (not Phase 1)")
print("2. ❓ highest_price not updating correctly") 
print("3. ❓ advanced_stop_loss not being used for display")
print("4. ❓ Position using simple algorithm instead of advanced")
print("5. ❓ Highest price reset after auto buy")

print(f"\n🔧 DEBUGGING STEPS:")
print("-" * 50)
print("1. Check which algorithm is being used (simple vs advanced)")
print("2. Check which phase the position is in")
print("3. Check if highest_price is updating")
print("4. Check if advanced_stop_loss field is being updated")
print("5. Check if UI is showing advanced_stop_loss or old stop_loss_price")

print(f"\n🎯 QUICK TEST SCENARIOS:")
print("-" * 50)

test_prices = [594, 600, 605, 610, 615, 620]
print("Price Movement Test:")
for price in test_prices:
    profit = price - buy_price
    if profit >= 10:
        steps = int(profit // 10)
        sl = buy_price + (steps * 10)
    else:
        sl = buy_price - 10
    print(f"  Price ₹{price} → Profit ₹{profit} → SL ₹{sl}")

print(f"\n🚀 NEXT ACTIONS:")
print("="*50)
print("1. Check app logs when price moves from ₹594 to ₹605")
print("2. Look for 'PHASE 1 TRAILING' debug messages")
print("3. Verify position is using advanced algorithm")
print("4. Check if highest_price field is updating correctly")

print("=" * 80)