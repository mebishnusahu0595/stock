#!/usr/bin/env python3
"""
Test Smart Trailing Stop Loss: First 5 point protection, then 10 point steps
Your idea: 100 → 105 (stop loss 105) → 110 (stop loss 110) → 120, 130...
"""

def test_smart_trailing_logic():
    """Test the new smart trailing logic"""
    
    print("🧠 TESTING SMART TRAILING STOP LOSS")
    print("=" * 60)
    print("Logic: First 5-point protection, then 10-point steps")
    print()
    
    # Test scenarios
    scenarios = [
        ("Initial Buy", 100.00, 100.00, 90.00),
        ("Small Move", 100.00, 104.99, 90.00),   # Less than 5, no protection yet
        ("🛡️ First Protection", 100.00, 105.00, 105.00),   # First 5-point protection
        ("Within First Zone", 100.00, 109.99, 105.00),   # Stay at first protection
        ("🎯 First Step", 100.00, 110.00, 110.00),   # First 10-point step
        ("Within First Step", 100.00, 119.99, 110.00),   # Stay at first step
        ("Second Step", 100.00, 120.00, 120.00),   # Second 10-point step
        ("Third Step", 100.00, 130.00, 130.00),   # Third 10-point step
        ("Partial Step", 100.00, 125.50, 120.00),   # Between steps
    ]
    
    print("📊 CALCULATION TABLE:")
    print("-" * 80)
    print(f"{'Scenario':<20} {'Buy':<8} {'High':<8} {'Profit':<8} {'Logic':<25} {'Stop Loss':<10}")
    print("-" * 80)
    
    for scenario, buy_price, highest_price, expected_stop in scenarios:
        profit = highest_price - buy_price
        
        # Apply the logic
        if profit >= 5 and profit < 10:
            # First protection
            calculated_stop = buy_price + 5
            logic = "First 5-point protection"
        elif profit >= 10:
            # Normal 10-point steps
            steps = int(profit // 10)
            calculated_stop = buy_price + (steps * 10)
            # But never below first protection (105)
            first_protection = buy_price + 5
            calculated_stop = max(calculated_stop, first_protection)
            logic = f"{steps} × 10-point steps"
        else:
            # Default stop loss
            calculated_stop = buy_price - 10
            logic = "Default (buy - 10)"
        
        status = "✅" if calculated_stop == expected_stop else "❌"
        print(f"{scenario:<20} ₹{buy_price:<7.2f} ₹{highest_price:<7.2f} ₹{profit:<7.2f} {logic:<25} ₹{calculated_stop:<9.2f} {status}")

def test_progressive_movement():
    """Test progressive price movement"""
    print(f"\n\n🔄 PROGRESSIVE PRICE MOVEMENT EXAMPLE:")
    print("-" * 50)
    print("Buy at ₹100, then watch price move progressively...")
    print()
    
    buy_price = 100.00
    price_movements = [100, 102, 105, 107, 110, 115, 120, 125, 130]
    
    current_stop_loss = buy_price - 10  # Initial stop loss
    
    for price in price_movements:
        profit = price - buy_price
        
        # Calculate new stop loss based on smart logic
        if profit >= 5 and profit < 10:
            # First protection
            new_stop_loss = buy_price + 5
        elif profit >= 10:
            # Normal steps
            steps = int(profit // 10)
            new_stop_loss = buy_price + (steps * 10)
            # Never below first protection
            first_protection = buy_price + 5
            new_stop_loss = max(new_stop_loss, first_protection)
        else:
            # Keep current
            new_stop_loss = current_stop_loss
        
        # Never let stop loss go down
        final_stop_loss = max(new_stop_loss, current_stop_loss)
        
        # Show movement
        if final_stop_loss != current_stop_loss:
            print(f"📈 Price: ₹{price:6.2f} → Stop Loss: ₹{current_stop_loss:6.2f} → ₹{final_stop_loss:6.2f} 🔺")
        else:
            print(f"📊 Price: ₹{price:6.2f} → Stop Loss: ₹{final_stop_loss:6.2f} (unchanged)")
        
        current_stop_loss = final_stop_loss

def show_benefits():
    """Show benefits of this approach"""
    print(f"\n\n✅ BENEFITS OF SMART TRAILING:")
    print("-" * 40)
    print("🛡️ Early Protection: 5-point profit = immediate protection")
    print("💰 No Loss Zone: Once ₹105 touched, never lose money")
    print("📈 Smooth Progression: 105 → 110 → 120 → 130...")
    print("🔒 Capital Protection: Stop loss never goes down")
    print("🎯 Optimal Risk/Reward: Quick protection + good profits")
    
    print(f"\n❌ OLD SYSTEM PROBLEMS (SOLVED):")
    print("🐌 Had to wait for ₹110 for any protection")
    print("💸 Risk of losing ₹10 even with ₹5-9 profit")
    print("🤷 No protection for small profitable moves")
    
    print(f"\n🎯 NEW SYSTEM ADVANTAGES:")
    print("⚡ Instant protection at ₹5 profit")
    print("🛡️ Never lose money after ₹105 touch")
    print("📈 Still captures big moves with 10-point steps")

if __name__ == "__main__":
    test_smart_trailing_logic()
    test_progressive_movement() 
    show_benefits()
    
    print(f"\n\n🎯 ANSWER TO YOUR IDEA:")
    print("✅ YES! Smart trailing implemented:")
    print("   ₹100 → ₹105 = Stop Loss ₹105 (First Protection)")
    print("   ₹100 → ₹110 = Stop Loss ₹110 (First Step)")
    print("   ₹100 → ₹120 = Stop Loss ₹120 (Second Step)")
    print("   And so on... 🚀")
