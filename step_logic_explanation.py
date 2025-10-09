#!/usr/bin/env python3
"""
STEP-BASED TRAILING STOP LOSS EXAMPLES
Practical examples of how the new logic works
"""

print("🎯 STEP-BASED TRAILING STOP LOSS LOGIC")
print("=" * 50)

def calculate_stop_loss(buy_price, current_highest):
    """Calculate stop loss based on step logic"""
    profit = current_highest - buy_price
    
    if profit >= 10:
        steps = int(profit // 10)  # Complete 10-rupee steps
        stop_loss = buy_price + (steps * 10)
    else:
        stop_loss = buy_price - 10  # Initial stop loss
    
    return stop_loss, profit, int(profit // 10)

# Your Examples
examples = [
    ("आपका Example 1", 120.70, 131.50, 130.70),
    ("आपका Example 2", 120.70, 145.00, 140.70),
    ("More Examples", 100.00, 125.50, 120.00),
    ("Edge Case 1", 100.00, 109.99, 90.00),   # No trailing yet
    ("Edge Case 2", 100.00, 110.00, 100.00),  # Exactly 1 step
    ("3 Steps", 100.00, 139.50, 130.00),      # 3 complete steps
]

print("\n📊 CALCULATION EXAMPLES:")
print("-" * 80)
print(f"{'Case':<15} {'Buy Price':<10} {'Highest':<10} {'Profit':<8} {'Steps':<6} {'Stop Loss':<10} {'Expected':<10} {'Status'}")
print("-" * 80)

for case, buy, highest, expected in examples:
    stop_loss, profit, steps = calculate_stop_loss(buy, highest)
    status = "✅ PASS" if stop_loss == expected else "❌ FAIL"
    
    print(f"{case:<15} ₹{buy:<9.2f} ₹{highest:<9.2f} ₹{profit:<7.2f} {steps:<6} ₹{stop_loss:<9.2f} ₹{expected:<9.2f} {status}")

print("\n🔄 AUTO BUY/SELL CYCLE EXAMPLE:")
print("-" * 50)
print("1. Manual Buy: ₹120.70")
print("   └─ Initial Stop Loss: ₹110.70 (buy price - 10)")
print()
print("2. Price rises to ₹131.50 (profit ₹10.80)")
print("   └─ Trailing triggered: 1 complete step")
print("   └─ New Stop Loss: ₹130.70 (buy price + 10)")
print()
print("3. Price drops to ₹130.70 or below")
print("   └─ AUTO SELL triggered")
print("   └─ Position set to 'waiting for auto buy'")
print()
print("4. Price recovers to ₹130.70 or above")
print("   └─ AUTO BUY triggered at ₹130.70")
print("   └─ New Stop Loss: ₹130.70 (no loss on auto buy)")
print()
print("5. Price rises to ₹145.00 (profit ₹14.30 from auto buy)")
print("   └─ Trailing triggered: 1 complete step")
print("   └─ New Stop Loss: ₹140.70 (auto buy price + 10)")

print("\n✅ KEY BENEFITS:")
print("🎯 Predictable 10-rupee step progression")
print("🛡️ Stop loss never goes down, only up")
print("💰 Locks in profit every 10 rupees gained")
print("🔄 Auto buy/sell cycle preserves capital")
print("📈 Maximizes profit in trending markets")

print("\n🚫 REMOVED CONFUSING ELEMENTS:")
print("❌ No more 'trailing_gap' of 0.15")
print("❌ No more '5 points gap' confusion")
print("❌ No more decimal calculations")
print("✅ Simple: Buy Price + (10 × Steps)")
