#!/usr/bin/env python3

"""
🎯 DEBUG CHECKLIST: Why Trailing Not Working
Step-by-step debugging guide
"""

print("=" * 80)
print("🎯 DEBUG CHECKLIST: Why Trailing Stop Loss Not Working")
print("=" * 80)

print("\n🔍 STEP 1: CHECK APP STATUS")
print("-" * 50)
print("✅ App running on http://127.0.0.1:5000")
print("✅ No errors in terminal")
print("✅ 'Auto trading background task started' message")

print("\n🔍 STEP 2: CHECK ALGORITHM SETTING")
print("-" * 50)
print("✅ Algorithm should be 'advanced' (not 'simple')")
print("❓ Check terminal for 'ADVANCED' vs 'SIMPLE' messages")
print("❓ If you see 'SIMPLE MONITORING' → Wrong algorithm!")

print("\n🔍 STEP 3: CREATE TEST POSITION")
print("-" * 50)
print("✅ Open browser to http://127.0.0.1:5000")
print("✅ Go to Manual Trading tab")
print("✅ Select any strike (e.g., 56000 CE)")
print("✅ Enter quantity: 10")
print("✅ Click BUY button")

print("\n🔍 STEP 4: WATCH TERMINAL FOR POSITION CREATION")
print("-" * 50)
print("✅ Look for: '📍 MANUAL BUY POSITION CREATED'")
print("✅ Should show: 'Stop Loss: ₹(buy_price - 10)'")
print("❓ If missing → Position creation failed")

print("\n🔍 STEP 5: CHECK POSITION MONITORING")
print("-" * 50)
print("✅ Look for: '🔄 PHASE 1: Manual Buy ₹X | Current ₹Y'")
print("✅ Should show Phase 1 detection")
print("❓ If missing → Position not being monitored")

print("\n🔍 STEP 6: TEST PRICE MOVEMENT")
print("-" * 50)
print("✅ Wait for option price to move +₹10 above buy price")
print("✅ Example: Buy ₹600 → Wait for price ₹611+")
print("✅ Watch terminal for price updates")

print("\n🔍 STEP 7: LOOK FOR TRAILING ACTIVATION")
print("-" * 50)
print("✅ Look for: '📍 PHASE 1 TRAILING: Buy ₹X | High ₹Y | Profit ₹Z'")
print("✅ Look for: 'SL = ₹X + (N×10) = ₹NEW_SL'")
print("❓ If missing → Trailing logic not triggering")

print("\n🔍 STEP 8: CHECK STOP LOSS UPDATE")
print("-" * 50)
print("✅ Stop loss should change in browser")
print("✅ From ₹(buy-10) to ₹(buy+10)")
print("❓ If not changing → UI not updating or field mismatch")

print("\n🚨 MOST COMMON ISSUES:")
print("-" * 50)
print("1. 🔴 'SIMPLE MONITORING' → Algorithm set to 'simple'")
print("2. 🔴 No 'PHASE 1 TRAILING' → Position missing fields")
print("3. 🔴 Stop loss not updating → UI caching old values")
print("4. 🔴 Position created before fixes → Missing manual_buy_price")

print("\n💡 QUICK FIXES:")
print("-" * 50)
print("1. Create NEW position (old ones might be corrupted)")
print("2. Refresh browser page")
print("3. Check algorithm setting in app")
print("4. Look for 'ADVANCED' in terminal messages")

print("\n🎯 SUCCESS = You see 'PHASE 1 TRAILING' messages!")
print("=" * 80)