#!/usr/bin/env python3
"""
SIMPLE 10-POINT TRAILING STOP LOSS - BACK TO BASICS
No 5-point confusion, just clean 10-rupee steps
"""

print("💰 SIMPLE 10-POINT TRAILING STOP LOSS")
print("=" * 60)

def calculate_simple_stop_loss(buy_price, current_highest):
    """Calculate stop loss based on simple 10-point logic"""
    profit = current_highest - buy_price
    
    if profit >= 10:
        steps = int(profit // 10)  # Complete 10-rupee steps
        stop_loss = buy_price + (steps * 10)
    else:
        stop_loss = buy_price - 10  # Initial stop loss
    
    return stop_loss, profit, int(profit // 10)

# Create the table you requested
examples = [
    (100.00, 104.99),   # No protection yet
    (100.00, 109.99),   # Still no protection
    (100.00, 110.00),   # First 10-point step
    (100.00, 119.99),   # Stay at step 1
    (100.00, 120.00),   # Second 10-point step
    (100.00, 129.99),   # Stay at step 2
    (100.00, 130.00),   # Third 10-point step
    (100.00, 139.99),   # Stay at step 3
    (100.00, 140.00),   # Fourth 10-point step
]

print("\n📊 SIMPLE 10-POINT TRAILING LOGIC:")
print("-" * 80)
print(f"{'Buy Price':<12} {'Price Reaches':<15} {'Stop Loss':<12} {'Logic':<30}")
print("-" * 80)

for buy_price, highest_price in examples:
    stop_loss, profit, steps = calculate_simple_stop_loss(buy_price, highest_price)
    
    if profit < 10:
        logic = "No protection yet"
    else:
        logic = f"🎯 Step {steps}: {steps} × 10-point progression"
    
    print(f"₹{buy_price:<11.2f} ₹{highest_price:<14.2f} ₹{stop_loss:<11.2f} {logic}")

print("\n✅ BENEFITS OF SIMPLE SYSTEM:")
print("-" * 40)
print("🎯 Clean 10-rupee steps only")
print("💰 Less frequent trades = Lower costs")
print("🔒 Stop loss never goes down")
print("📈 Captures major profit moves")
print("⚡ Simple to understand & debug")

print("\n🔄 AUTO BUY/SELL CYCLE EXAMPLE:")
print("-" * 50)
print("1. Manual Buy: ₹100")
print("   └─ Initial Stop Loss: ₹90 (buy price - 10)")
print()
print("2. Price rises to ₹110 (profit ₹10)")
print("   └─ Trailing triggered: 1 complete step")
print("   └─ New Stop Loss: ₹110 (buy price + 10)")
print()
print("3. Price drops to ₹110 or below")
print("   └─ AUTO SELL triggered")
print("   └─ Position set to 'waiting for auto buy'")
print()
print("4. Price recovers to ₹110 or above")
print("   └─ AUTO BUY triggered at ₹110")
print("   └─ New Stop Loss: ₹110 (no loss on auto buy)")
print()
print("5. Price rises to ₹120 (profit ₹10 from auto buy)")
print("   └─ Trailing triggered: 1 complete step")
print("   └─ New Stop Loss: ₹120 (auto buy price + 10)")

print("\n❌ REMOVED COMPLEXITY:")
print("🚫 No more 5-point protection")
print("🚫 No frequent small trades")
print("🚫 No early stop loss movement")
print("✅ Simple: Only 10-rupee steps!")

print("\n" + "=" * 60)
print("🎯 FINAL LOGIC: Wait for ₹10 profit, then trail every ₹10")
print("💡 Less trades = Lower costs = Better profits!")
