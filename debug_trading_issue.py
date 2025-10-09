#!/usr/bin/env python3
"""
🔍 DEBUG: Analysis of the Trading Pattern Issue
==================================================

PROBLEM IDENTIFIED:
==================
Manual Buy ₹424.15 → SL ₹414.15
Price ₹434.10 → SL ₹424.10, Progressive Min ₹404.10 (424.10-20)
Sell ₹434.10 → Auto Buy ₹434.10

EXPECTED AFTER AUTO BUY:
========================
Auto Buy ₹434.10 → SL ₹424.10 (434.10-10)
Progressive Min ₹404.10 (from highest SL ever)
Final SL = max(424.10, 404.10) = ₹424.10 ✅

ACTUAL BEHAVIOR (WRONG):
========================
Auto Buy ₹434.10 → SL gets calculated wrong
Sells at ₹433.45, ₹433.25, ₹433.00 (very close prices)

ROOT CAUSE:
===========
The 'buy_price' and 'highest_price' are being reset incorrectly in auto buy,
which might be affecting the trailing logic or progressive minimum calculation.

ISSUE: After auto buy, when price moves slightly, the algorithm might be
using wrong reference points for trailing or progressive minimum.

Let me trace what should happen step by step:

1. Manual Buy ₹424.15
   - highest_price = ₹424.15
   - advanced_stop_loss = ₹414.15 (424.15-10)
   - highest_stop_loss = ₹414.15
   - progressive_minimum = ₹394.15 (414.15-20)

2. Price rises to ₹434.10
   - highest_price = ₹434.10  
   - new_stop_loss = ₹424.10 (434.10-10)
   - highest_stop_loss = ₹424.10
   - progressive_minimum = ₹404.10 (424.10-20)
   - advanced_stop_loss = ₹424.10

3. Sell at ₹434.10 (profit booking)
   - last_stop_loss_price = ₹434.10 (current price, not SL price!)

4. Auto Buy at ₹434.10
   - buy_price = ₹434.10 (RESET)
   - highest_price = ₹434.10 (RESET)
   - calculated_stop_loss = ₹424.10 (434.10-10)
   - progressive_minimum = ₹404.10 (SHOULD NOT RESET!)
   - advanced_stop_loss = max(424.10, 404.10) = ₹424.10 ✅

5. Price drops to ₹433.45
   - Should NOT sell because ₹433.45 > ₹424.10
   - But it's selling! This means SL calculation is wrong!

LIKELY ISSUE:
=============
Either:
A) The progressive minimum is being reset incorrectly
B) The buy_price reset is affecting trailing calculation  
C) There's a different algorithm running (Simple instead of Advanced)
D) The stop loss trigger condition has wrong logic

Let me check the exact values in debugging...
"""

def debug_trading_scenario():
    """Debug the exact scenario from user's history"""
    print("=" * 80)
    print("🔍 DEBUGGING TRADING SCENARIO")
    print("=" * 80)
    
    # Simulate the exact scenario
    print("\n📊 SCENARIO: PE 55600")
    print("Manual Buy: ₹424.15")
    print("Highest reached: ₹434.10") 
    print("Profit sell: ₹434.10 (₹1044.75 profit)")
    print("Auto buy: ₹434.10")
    print("Then selling at: ₹433.45, ₹433.25, ₹433.00")
    print("\n🚨 ISSUE: Why selling so close to buy price?")
    
    print("\n🧮 EXPECTED CALCULATION:")
    manual_buy = 424.15
    highest_price = 434.10
    
    print(f"1. Manual Buy: ₹{manual_buy}")
    print(f"   Initial SL: ₹{manual_buy - 10} = ₹{manual_buy - 10}")
    print(f"   Initial Progressive Min: ₹{(manual_buy - 10) - 20} = ₹{(manual_buy - 10) - 20}")
    
    print(f"\n2. Price reaches: ₹{highest_price}")
    new_sl = highest_price - 10
    print(f"   New SL: ₹{highest_price} - 10 = ₹{new_sl}")
    print(f"   Highest SL: ₹{new_sl}")
    progressive_min = new_sl - 20
    print(f"   Progressive Min: ₹{new_sl} - 20 = ₹{progressive_min}")
    
    print(f"\n3. Sell at: ₹{highest_price} (profit booking)")
    print(f"   Auto buy trigger: ₹{highest_price}")
    
    print(f"\n4. Auto Buy at: ₹{highest_price}")
    auto_buy_sl = highest_price - 10
    print(f"   Calculated SL: ₹{highest_price} - 10 = ₹{auto_buy_sl}")
    print(f"   Progressive Min: ₹{progressive_min} (should not reset)")
    final_sl = max(auto_buy_sl, progressive_min)
    print(f"   Final SL: max(₹{auto_buy_sl}, ₹{progressive_min}) = ₹{final_sl}")
    
    print(f"\n5. Price drops to ₹433.45")
    price_drop = 433.45
    print(f"   Should sell? ₹{price_drop} <= ₹{final_sl}? {price_drop <= final_sl}")
    if price_drop <= final_sl:
        print("   ✅ YES - Should sell (correct)")
        print(f"   Because ₹{price_drop} is <= ₹{final_sl}")
    else:
        print("   ❌ NO - Should NOT sell (ISSUE!)")
        print(f"   Because ₹{price_drop} is > ₹{final_sl}")
    
    print(f"\n🎯 CONCLUSION:")
    print(f"Expected Final SL: ₹{final_sl}")
    print(f"Actual selling at: ₹{price_drop}")
    print(f"Difference: ₹{price_drop - final_sl:.2f}")
    
    if price_drop <= final_sl:
        print("✅ LOGIC CORRECT: Stop loss triggered as expected")
        print("🚨 BUT WAIT! This means SL is ₹424.1 but selling at ₹433.45?")
        print("� REAL ISSUE: Stop loss value is wrong in the system!")
    else:
        print("🚨 ISSUE: Stop loss is too high! Algorithm error.")

if __name__ == "__main__":
    debug_trading_scenario()