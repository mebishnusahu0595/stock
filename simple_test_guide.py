#!/usr/bin/env python3

"""
🎯 SIMPLE TRAILING TEST: Manual Position Creation
Step-by-step guide to test trailing stop loss
"""

print("=" * 80)
print("🎯 TRAILING STOP LOSS TEST GUIDE")
print("=" * 80)

print("\n📋 STEP-BY-STEP TEST:")
print("-" * 50)

print("1️⃣ OPEN BROWSER:")
print("   → Go to: http://127.0.0.1:5000")
print("   → App should be running (check terminal)")

print("\n2️⃣ CREATE MANUAL POSITION:")
print("   → Click 'Manual Trading' tab")
print("   → Select any strike (e.g., 56000 CE)")
print("   → Enter quantity: 10 (small for testing)")
print("   → Click 'BUY' button")

print("\n3️⃣ WATCH TERMINAL LOGS:")
print("   → Look for: '📍 MANUAL BUY POSITION CREATED'")
print("   → Should show: 'Stop Loss: ₹(buy_price - 10)'")

print("\n4️⃣ MONITOR PRICE MOVEMENT:")
print("   → Watch option price in live data")
print("   → When price goes +₹10 above buy price...")
print("   → Look for: '📍 PHASE 1 TRAILING:' messages")

print("\n5️⃣ VERIFY TRAILING WORKS:")
print("   → Stop loss should change from ₹(buy-10) to ₹(buy+10)")
print("   → Example: Buy ₹600 → SL ₹590 → Price ₹611 → SL ₹610")

print("\n🎯 EXPECTED TERMINAL MESSAGES:")
print("-" * 50)
print("✅ '🔄 PHASE 1: Manual Buy ₹600 | Current ₹611'")
print("✅ '📍 PHASE 1 TRAILING: Buy ₹600 | High ₹611 | Profit ₹11.00 | Steps 1'")
print("✅ 'SL = ₹600 + (1×10) = ₹610 | Final SL ₹610'")

print("\n🚨 IF YOU DON'T SEE TRAILING:")
print("-" * 50)
print("❌ Check if position shows 'Advanced' algorithm")
print("❌ Verify price actually moved +₹10 above buy")
print("❌ Look for error messages in terminal")
print("❌ Try refreshing the browser page")

print("\n💡 QUICK DEBUG:")
print("-" * 50)
print("• Open browser DevTools (F12)")
print("• Go to Network tab")
print("• Watch /api/positions requests")
print("• Check if stop_loss_price field updates")

print("\n🎯 SUCCESS = Stop loss moves from ₹(buy-10) to ₹(buy+10)!")
print("=" * 80)