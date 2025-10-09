#!/usr/bin/env python3

"""
🎯 QUICK TEST: Verify Auto Buy Logic
Create a test position to verify the auto buy behavior
"""

print("=" * 60)
print("🎯 QUICK TEST FOR AUTO BUY LOGIC")
print("=" * 60)

print("\n📋 HOW TO TEST YOUR LOGIC:")
print("-" * 40)

print("1️⃣ CREATE MANUAL POSITION:")
print("   → Buy any option at current price (e.g., ₹100)")
print("   → Stop loss will be set to ₹90 (buy - 10)")

print("\n2️⃣ WAIT FOR STOP LOSS:")
print("   → Let price drop to ₹90")
print("   → Position will be auto-sold at ₹90")

print("\n3️⃣ WATCH AUTO BUY:")
print("   → Auto buy triggers at ₹90")
print("   → But buys back at ₹100 (original price)")
print("   → NOT at ₹90 (current price)")

print("\n4️⃣ VERIFY IN TERMINAL:")
print("   → Look for: 'PHASE 1 AUTO BUY: Using manual buy price ₹100'")
print("   → Look for: 'instead of current price ₹90'")

print("\n🎯 SUCCESS CRITERIA:")
print("-" * 40)
print("✅ Auto buy price = Original manual buy price")
print("✅ NOT current market price")
print("✅ Debug messages confirm correct behavior")

print("\n💡 WHY THIS MATTERS:")
print("-" * 40)
print("• Old: Buy at ₹90 → Immediate ₹10 loss")
print("• New: Buy at ₹100 → Breakeven")
print("• Result: No more rapid loss cycles!")

print("\n🚀 READY TO TEST!")
print("=" * 60)