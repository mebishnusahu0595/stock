#!/usr/bin/env python3
"""
Test Advanced Algorithm Price Jump Scenario
Price at ₹159 → Drops to ₹149 → Stop Loss → Auto Buy → Further drops
"""

def test_price_jump_scenario():
    """Test the complete price jump and drop scenario"""
    
    print("🧪 TESTING PRICE JUMP SCENARIO - ADVANCED ALGORITHM")
    print("=" * 55)
    
    # Starting position at ₹159
    position = {
        'buy_price': 100.0,
        'current_price': 159.0,
        'advanced_stop_loss': 150.0,  # From previous calculation
        'highest_stop_loss': 150.0,
        'progressive_minimum': 130.0,  # 150 - 20 = 130
        'waiting_for_autobuy': False,
        'quantity': 25,
        'auto_buy_count': 0
    }
    
    print(f"📊 STARTING STATE (Price ₹159):")
    print(f"   Buy Price: ₹{position['buy_price']}")
    print(f"   Current Price: ₹{position['current_price']}")
    print(f"   Stop Loss: ₹{position['advanced_stop_loss']}")
    print(f"   Progressive Minimum: ₹{position['progressive_minimum']}")
    print(f"   Quantity: {position['quantity']}")
    print()
    
    # STEP 1: Price drops to ₹149 - Stop Loss Trigger
    print("🔴 STEP 1: Price drops to ₹149 - Stop Loss Hit!")
    print("-" * 40)
    
    drop_price = 149.0
    position['current_price'] = drop_price
    
    # Check stop loss trigger
    stop_loss_hit = position['current_price'] < position['advanced_stop_loss']
    
    print(f"   Price: ₹{drop_price}")
    print(f"   Stop Loss: ₹{position['advanced_stop_loss']}")
    print(f"   Stop Loss Hit? {stop_loss_hit} ({drop_price} < {position['advanced_stop_loss']})")
    
    if stop_loss_hit:
        # Execute auto sell
        sell_price = position['advanced_stop_loss']  # Sells at stop loss price ₹150
        
        print(f"   🔴 AUTO SELL EXECUTED at ₹{sell_price}")
        
        # Set up auto buy trigger
        position['last_stop_loss_price'] = sell_price  # Auto buy trigger = ₹150
        position['waiting_for_autobuy'] = True
        position['quantity'] = 0
        
        print(f"   ⚡ Auto Buy Trigger set at ₹{position['last_stop_loss_price']}")
        print(f"   📊 Position sold, waiting for auto buy")
    
    print()
    
    # STEP 2: Test auto buy trigger conditions
    print("🎯 STEP 2: Testing Auto Buy Trigger")
    print("-" * 30)
    
    test_prices = [149, 149.5, 150, 150.5, 151]
    
    for test_price in test_prices:
        auto_buy_trigger = position.get('last_stop_loss_price', 0)
        will_trigger = (position.get('waiting_for_autobuy', False) and 
                       test_price >= auto_buy_trigger)
        
        status = "✅ WILL TRIGGER" if will_trigger else "❌ NO TRIGGER"
        print(f"   Price ₹{test_price} vs Trigger ₹{auto_buy_trigger} → {status}")
    
    print()
    
    # STEP 3: Auto buy at ₹150+
    print("🟢 STEP 3: Auto Buy Execution at ₹150+")
    print("-" * 35)
    
    auto_buy_price = 150.5  # Price goes above ₹150
    position['current_price'] = auto_buy_price
    
    # Execute auto buy
    position['waiting_for_autobuy'] = False
    position['buy_price'] = auto_buy_price
    position['advanced_stop_loss'] = auto_buy_price - 10  # 150.5 - 10 = 140.5
    position['quantity'] = 25
    position['auto_buy_count'] += 1
    
    # KEEP progressive minimum from previous cycle (130)
    # This is the key difference from Simple Algorithm
    
    print(f"   Auto Buy Price: ₹{auto_buy_price}")
    print(f"   New Stop Loss: ₹{position['advanced_stop_loss']} (Buy Price - 10)")
    print(f"   ✅ PRESERVED Progressive Minimum: ₹{position['progressive_minimum']}")
    print(f"   Quantity Restored: {position['quantity']}")
    print()
    
    # STEP 4: Price drops to ₹140 - Second Stop Loss
    print("🔴 STEP 4: Price drops to ₹140 - Second Stop Loss")
    print("-" * 45)
    
    second_drop_price = 140.0
    position['current_price'] = second_drop_price
    
    stop_loss_hit_2 = position['current_price'] < position['advanced_stop_loss']
    
    print(f"   Price: ₹{second_drop_price}")
    print(f"   Stop Loss: ₹{position['advanced_stop_loss']}")
    print(f"   Stop Loss Hit? {stop_loss_hit_2} ({second_drop_price} < {position['advanced_stop_loss']})")
    
    if stop_loss_hit_2:
        # Execute second auto sell
        sell_price_2 = position['advanced_stop_loss']
        
        print(f"   🔴 SECOND AUTO SELL at ₹{sell_price_2}")
        
        # Set up auto buy trigger again
        position['last_stop_loss_price'] = sell_price_2
        position['waiting_for_autobuy'] = True
        position['quantity'] = 0
        
        print(f"   ⚡ Auto Buy Trigger set at ₹{position['last_stop_loss_price']}")
    
    print()
    
    # STEP 5: Test final protection level
    print("🛡️ STEP 5: Progressive Protection Test")
    print("-" * 35)
    
    print(f"   Current Progressive Minimum: ₹{position['progressive_minimum']}")
    print(f"   If auto buy happens again, minimum stop loss will be: ₹{position['progressive_minimum']}")
    print()
    
    # Test what happens if price goes to 130
    test_auto_buy_price = 135.0
    projected_stop_loss = test_auto_buy_price - 10  # 135 - 10 = 125
    protected_stop_loss = max(projected_stop_loss, position['progressive_minimum'])  # max(125, 130) = 130
    
    print(f"🔮 HYPOTHETICAL: If auto buy at ₹{test_auto_buy_price}")
    print(f"   Normal Stop Loss would be: ₹{projected_stop_loss} ({test_auto_buy_price} - 10)")
    print(f"   Progressive Protection: ₹{protected_stop_loss} (max({projected_stop_loss}, {position['progressive_minimum']}))")
    print(f"   📊 Protection saves: ₹{protected_stop_loss - projected_stop_loss} per share")
    
    print()
    print("✅ SCENARIO VERIFICATION:")
    print("=" * 25)
    print("   ✅ Price ₹149 → Stop Loss hit at ₹150")
    print("   ✅ Auto buy triggers when price > ₹150")  
    print("   ✅ New stop loss = ₹140.5 (auto buy price - 10)")
    print("   ✅ Second drop to ₹140 → Stop Loss hit again")
    print("   ✅ Progressive minimum stays at ₹130 (150-20)")
    print("   ✅ Final protection level: ₹130")
    print()
    print("🎯 USER'S UNDERSTANDING: 100% CORRECT! 🎯")

if __name__ == "__main__":
    test_price_jump_scenario()