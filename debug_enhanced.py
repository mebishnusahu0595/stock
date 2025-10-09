#!/usr/bin/env python3

"""
🎯 ENHANCED DEBUGGING: Why Stop Loss Not Moving
Real-time check for the specific issue user is facing

USER ISSUE:
"buy 594 !! sl = price reaches more than 605 !! then why stop loss is notmoved ?"

This will help identify the exact problem
"""

print("=" * 80)
print("🎯 ENHANCED DEBUGGING FOR STOP LOSS ISSUE")
print("=" * 80)

print("\n📊 CHECKING ALGORITHM LOGIC FOR USER'S CASE:")
print("-" * 50)

# Simulate the exact user scenario
manual_buy_price = 594
current_price = 605
price_above_buy = current_price - manual_buy_price

print(f"Manual Buy Price: ₹{manual_buy_price}")
print(f"Current Price: ₹{current_price}")
print(f"Price Above Buy: ₹{price_above_buy}")

# Phase determination
if price_above_buy < 20:
    phase = 1
    print(f"✅ Phase: {phase} (Since {price_above_buy} < 20)")
elif price_above_buy < 30:
    phase = 2
    print(f"✅ Phase: {phase} (Since 20 ≤ {price_above_buy} < 30)")
else:
    phase = 3
    print(f"✅ Phase: {phase} (Since {price_above_buy} ≥ 30)")

print(f"\n🔍 PHASE {phase} TRAILING LOGIC:")
print("-" * 50)

if phase == 1:
    # Simulate Phase 1 logic
    highest_price = current_price  # Assume current is highest
    profit = highest_price - manual_buy_price
    trailing_step = 10
    
    print(f"Highest Price: ₹{highest_price}")
    print(f"Profit: ₹{highest_price} - ₹{manual_buy_price} = ₹{profit}")
    
    if profit >= 10:
        profit_steps = int(profit // trailing_step)
        trailing_stop_loss = manual_buy_price + (profit_steps * trailing_step)
        minimum_sl = manual_buy_price - 10
        final_sl = max(trailing_stop_loss, minimum_sl)
        
        print(f"✅ Profit ≥ 10: {profit} ≥ 10")
        print(f"✅ Profit Steps: int({profit} // {trailing_step}) = {profit_steps}")
        print(f"✅ Trailing SL: ₹{manual_buy_price} + ({profit_steps} × {trailing_step}) = ₹{trailing_stop_loss}")
        print(f"✅ Minimum SL: ₹{minimum_sl}")
        print(f"✅ Final SL: max(₹{trailing_stop_loss}, ₹{minimum_sl}) = ₹{final_sl}")
        
        expected_message = f"📍 PHASE 1 TRAILING: Buy ₹{manual_buy_price} | High ₹{highest_price} | Profit ₹{profit:.2f} | Steps {profit_steps}"
        print(f"\n📝 Expected Debug Message:")
        print(f"   {expected_message}")
        print(f"   SL = ₹{manual_buy_price} + ({profit_steps}×10) = ₹{trailing_stop_loss} | Final SL ₹{final_sl}")
        
    else:
        final_sl = manual_buy_price - 10
        print(f"❌ Profit < 10: {profit} < 10")
        print(f"❌ Simple SL: ₹{manual_buy_price} - 10 = ₹{final_sl}")

print(f"\n🚨 CRITICAL DEBUGGING QUESTIONS:")
print("=" * 50)
print("1. ❓ Is your position using 'advanced' algorithm?")
print("   → Check app logs for 'ADVANCED' vs 'SIMPLE' messages")

print(f"\n2. ❓ Is the position in Phase 1?")
print(f"   → Look for 'PHASE 1:' in logs")

print(f"\n3. ❓ Is highest_price updating?")
print(f"   → Check if highest_price reaches ₹{current_price}")

print(f"\n4. ❓ Are you seeing trailing debug messages?")
print(f"   → Look for 'PHASE 1 TRAILING:' messages")

print(f"\n5. ❓ Is advanced_stop_loss being updated?")
print(f"   → Check if advanced_stop_loss changes to ₹{final_sl if 'final_sl' in locals() else 'N/A'}")

print(f"\n🔧 IMMEDIATE DEBUGGING STEPS:")
print("=" * 50)
print("1. Open browser dev tools → Network tab")
print("2. Watch for /api/positions calls")
print("3. Look for stop_loss_price field in response")
print("4. Check if it changes from ₹584 to ₹604 when price hits ₹605")

print(f"\n💡 POSSIBLE ROOT CAUSES:")
print("=" * 50)
print("1. 🤔 Position created before algorithm fixes")
print("2. 🤔 Position missing required fields (manual_buy_price, etc.)")
print("3. 🤔 UI caching old stop loss value")
print("4. 🤔 Price update frequency too slow")
print("5. 🤔 Position still using simple algorithm")

print(f"\n🚀 QUICK FIX TO TEST:")
print("=" * 50)
print("1. Create a NEW manual position at ₹594")
print("2. Watch price move to ₹605")
print("3. Check if NEW position shows trailing SL")
print("4. If it works → Old position had stale data")
print("5. If it doesn't → Algorithm issue")

print("=" * 80)