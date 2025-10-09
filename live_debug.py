#!/usr/bin/env python3

"""
🎯 LIVE DEBUG: Check Terminal Output
Monitor the app's terminal output for trailing messages
"""

print("=" * 80)
print("🎯 LIVE DEBUGGING TRAILING STOP LOSS")
print("=" * 80)

print("\n📋 CHECK TERMINAL OUTPUT FOR:")
print("-" * 50)
print("✅ '🔄 PHASE 1: Manual Buy ₹X | Current ₹Y'")
print("✅ '📍 PHASE 1 TRAILING: Buy ₹X | High ₹Y | Profit ₹Z'")
print("✅ 'SL = ₹X + (N×10) = ₹NEW_SL'")
print("❌ 'SIMPLE MONITORING' (means wrong algorithm)")

print("\n🔧 IF YOU SEE:")
print("-" * 50)
print("❌ 'SIMPLE MONITORING' → Algorithm is set to 'simple'")
print("❌ No 'PHASE 1 TRAILING' → Position not in Phase 1")
print("❌ No messages → Position monitoring not running")

print("\n🚀 QUICK TEST:")
print("-" * 50)
print("1. Create manual position in browser")
print("2. Watch terminal for debug messages")
print("3. Move price +₹10 above buy price")
print("4. Look for trailing activation messages")

print("\n💡 COMMON ISSUES:")
print("-" * 50)
print("• Position created before fixes → Missing fields")
print("• Algorithm set to 'simple' → No trailing")
print("• Position not in Phase 1 → Wrong phase logic")
print("• Price not moving enough → Need +₹10 profit")

print("\n🎯 SUCCESS INDICATORS:")
print("-" * 50)
print("✅ 'PHASE 1 TRAILING' messages appear")
print("✅ Stop loss changes from ₹(buy-10) to ₹(buy+10)")
print("✅ Debug shows profit calculation")

print("=" * 80)
print("Watch the terminal output when you create/move positions!")
print("=" * 80)