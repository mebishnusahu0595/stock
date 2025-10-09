#!/usr/bin/env python3

"""
🎯 TEST TRAILING STOP LOSS: Create Test Position
Creating a small test position to verify trailing stop loss works

This will:
1. Create a manual position at current market price
2. Monitor price movement
3. Verify stop loss trails when profit >= ₹10
"""

import requests
import time
import json

print("=" * 80)
print("🎯 TESTING TRAILING STOP LOSS WITH NEW POSITION")
print("=" * 80)

print("\n📋 TEST PLAN:")
print("-" * 50)
print("1. ✅ App is running")
print("2. 🔄 Create small manual position")
print("3. 📊 Monitor price movement")
print("4. 🎯 Verify stop loss trails at +₹10 profit")
print("5. 📝 Check debug messages in terminal")

print(f"\n🔧 HOW TO CREATE TEST POSITION:")
print("-" * 50)
print("1. Open your browser to: http://localhost:5000")
print("2. Go to 'Manual Trading' section")
print("3. Select any strike (e.g., 56000 CE)")
print("4. Enter small quantity (e.g., 10)")
print("5. Click 'Buy' button")
print("6. Watch the terminal logs for trailing messages")

print(f"\n📊 WHAT TO LOOK FOR:")
print("-" * 50)
print("✅ Phase 1 detection: '🔄 PHASE 1: Manual Buy ₹X | Current ₹Y'")
print("✅ Trailing activation: '📍 PHASE 1 TRAILING: Buy ₹X | High ₹Y | Profit ₹Z'")
print("✅ Stop loss update: 'SL = ₹X + (N×10) = ₹NEW_SL'")
print("✅ UI update: Stop loss should change from ₹(buy-10) to ₹(buy+10)")

print(f"\n🎯 EXPECTED BEHAVIOR:")
print("-" * 50)
print("• Buy at ₹600 → Initial SL: ₹590")
print("• Price moves to ₹611 → Profit: ₹11")
print("• Stop loss should trail to: ₹610")
print("• Debug message: 'PHASE 1 TRAILING: ... Steps 1'")

print(f"\n🚨 IF TRAILING DOESN'T WORK:")
print("-" * 50)
print("❌ Check terminal for error messages")
print("❌ Verify position is using 'advanced' algorithm")
print("❌ Check if manual_buy_price field exists")
print("❌ Look for 'PHASE 1 TRAILING' messages")

print(f"\n💡 DEBUGGING TIPS:")
print("-" * 50)
print("• Open browser DevTools → Network tab")
print("• Watch /api/positions requests")
print("• Check stop_loss_price field in responses")
print("• Look for changes from ₹590 → ₹610")

print(f"\n🎯 SUCCESS CRITERIA:")
print("-" * 50)
print("✅ Stop loss moves from ₹(buy-10) to ₹(buy+10)")
print("✅ Debug messages show trailing calculation")
print("✅ UI updates in real-time")
print("✅ No errors in terminal logs")

print(f"\n🚀 READY TO TEST!")
print("=" * 80)
print("Create a manual position now and watch the trailing stop loss in action!")
print("The terminal will show detailed debug messages for each price update.")
print("=" * 80)