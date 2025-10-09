#!/usr/bin/env python3
"""
Test Advanced Algorithm at Price ₹159
Show what happens when price goes beyond ₹150 to ₹159
"""

def test_price_159_advanced():
    """Test Advanced Algorithm behavior at ₹159"""
    
    print("🧪 TESTING ADVANCED ALGORITHM AT PRICE ₹159")
    print("=" * 50)
    
    # Starting from our previous state at ₹150
    position = {
        'buy_price': 100.0,
        'current_price': 150.0,
        'highest_stop_loss': 150.0,
        'progressive_minimum': 130.0,  # 150 - 20 = 130
        'advanced_stop_loss': 150.0
    }
    
    print(f"📊 Starting State (at ₹150):")
    print(f"   Buy Price: ₹{position['buy_price']}")
    print(f"   Current Price: ₹{position['current_price']}")
    print(f"   Stop Loss: ₹{position['advanced_stop_loss']}")
    print(f"   Highest Stop Loss: ₹{position['highest_stop_loss']}")
    print(f"   Progressive Minimum: ₹{position['progressive_minimum']}")
    print()
    
    # Now price moves to ₹159
    new_price = 159.0
    position['current_price'] = new_price
    
    print(f"📈 PRICE MOVES TO ₹{new_price}")
    print("-" * 30)
    
    # Calculate new stop loss using Advanced Algorithm logic
    profit = new_price - position['buy_price']  # 159 - 100 = 59
    steps = int(profit // 10)  # 59 ÷ 10 = 5 complete steps
    calculated_stop_loss = position['buy_price'] + (steps * 10)  # 100 + (5 × 10) = 150
    
    print(f"🔢 CALCULATIONS:")
    print(f"   Profit: ₹{profit} (159 - 100)")
    print(f"   Steps: {steps} complete steps (59 ÷ 10 = 5.9 → 5)")
    print(f"   Calculated Stop Loss: ₹{calculated_stop_loss} (100 + 5×10)")
    print()
    
    # Check if we need to update highest stop loss
    if calculated_stop_loss > position['highest_stop_loss']:
        print("🔄 STOP LOSS UPDATE NEEDED:")
        print(f"   New SL ₹{calculated_stop_loss} > Current Highest ₹{position['highest_stop_loss']}")
        
        # Update highest stop loss first
        position['highest_stop_loss'] = calculated_stop_loss
        
        # Then calculate new progressive minimum
        new_progressive_min = position['highest_stop_loss'] - 20
        position['progressive_minimum'] = max(position['progressive_minimum'], new_progressive_min)
        
        # Set the new stop loss
        position['advanced_stop_loss'] = calculated_stop_loss
        
        print(f"   ✅ Updated Highest Stop Loss: ₹{position['highest_stop_loss']}")
        print(f"   ✅ Updated Progressive Min: ₹{position['progressive_minimum']} (max(130, {new_progressive_min}))")
        print(f"   ✅ Updated Stop Loss: ₹{position['advanced_stop_loss']}")
    else:
        print("❌ NO STOP LOSS UPDATE:")
        print(f"   Calculated SL ₹{calculated_stop_loss} ≤ Current Highest ₹{position['highest_stop_loss']}")
        print("   Stop Loss remains: ₹{position['advanced_stop_loss']}")
    
    print()
    print(f"📋 FINAL STATE AT ₹159:")
    print(f"   Current Price: ₹{position['current_price']}")
    print(f"   Stop Loss: ₹{position['advanced_stop_loss']}")
    print(f"   Highest Stop Loss: ₹{position['highest_stop_loss']}")
    print(f"   Progressive Minimum: ₹{position['progressive_minimum']}")
    print()
    
    # Show what happens for different price levels
    print("🔮 WHAT IF PRICE CONTINUES HIGHER?")
    print("-" * 35)
    
    test_prices = [160, 165, 170, 175]
    current_highest = position['highest_stop_loss']
    current_progressive = position['progressive_minimum']
    
    for test_price in test_prices:
        profit = test_price - position['buy_price']
        steps = int(profit // 10)
        new_sl = position['buy_price'] + (steps * 10)
        
        if new_sl > current_highest:
            current_highest = new_sl
            new_pm = new_sl - 20
            current_progressive = max(current_progressive, new_pm)
        
        print(f"   Price ₹{test_price}: SL ₹{new_sl}, Progressive Min ₹{current_progressive if new_sl > position['highest_stop_loss'] else position['progressive_minimum']}")
    
    print()
    print("💡 KEY INSIGHTS:")
    print("   🔹 At ₹159, stop loss stays at ₹150 (no new complete step)")
    print("   🔹 Next stop loss update at ₹160 → ₹160 stop loss")
    print("   🔹 Progressive minimum protects at ₹130 level")
    print("   🔹 Advanced Algorithm waits for complete ₹10 steps")

if __name__ == "__main__":
    test_price_159_advanced()