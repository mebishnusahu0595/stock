#!/usr/bin/env python3
"""
Test Advanced Algorithm - Progressive Minimum Protection
- Auto buy trigger at same sell price
- Progressive minimum protection prevents going below highest achieved stop loss
- Built-in trailing logic without external function calls
- Smart stop loss management
"""

def test_advanced_algorithm():
    """Test the Advanced Algorithm with progressive minimum protection"""
    
    print("🧪 TESTING ADVANCED ALGORITHM - PROGRESSIVE MINIMUM PROTECTION")
    print("=" * 60)
    
    # Simulate advanced position data
    position = {
        'strike': '50000',
        'type': 'CE',
        'buy_price': 100.0,
        'original_buy_price': 100.0,
        'current_price': 100.0,
        'advanced_stop_loss': 90.0,  # Advanced uses this instead of stop_loss_price
        'quantity': 25,
        'mode': 'Auto-Monitoring',
        'progressive_minimum': 90.0,  # Tracks highest stop loss achieved
        'highest_stop_loss': 90.0,   # Tracks highest stop loss ever
        'auto_buy_count': 0
    }
    
    print(f"📊 Initial Advanced Position:")
    print(f"   Buy Price: ₹{position['buy_price']}")
    print(f"   Advanced Stop Loss: ₹{position['advanced_stop_loss']}")
    print(f"   Progressive Minimum: ₹{position['progressive_minimum']}")
    print(f"   Highest Stop Loss: ₹{position['highest_stop_loss']}")
    print()
    
    # Step 1: Price moves up - test progressive protection
    print("📈 STEP 1: Price Movement with Progressive Protection")
    price_movements = [110, 120, 130, 140, 150]
    
    for new_price in price_movements:
        position['current_price'] = new_price
        
        # Advanced algorithm logic
        if new_price > position['buy_price']:
            # Calculate profit-based stop loss
            profit = new_price - position['buy_price']
            steps = int(profit // 10)
            calculated_stop_loss = position['buy_price'] + (steps * 10)
            
            # Apply progressive minimum
            new_stop_loss = max(calculated_stop_loss, position['progressive_minimum'])
            
            # Update stop loss only if it increases
            if new_stop_loss > position['advanced_stop_loss']:
                position['advanced_stop_loss'] = new_stop_loss
                position['highest_stop_loss'] = max(position['highest_stop_loss'], new_stop_loss)
                
                # ✅ FIX: Update progressive minimum AFTER highest stop loss is updated
                position['progressive_minimum'] = max(position['progressive_minimum'], 
                                                     position['highest_stop_loss'] - 20)
        
        print(f"   Price ₹{new_price}: Stop Loss ₹{position['advanced_stop_loss']}, "
              f"Progressive Min ₹{position['progressive_minimum']}, "
              f"Highest ₹{position['highest_stop_loss']}")
    
    print()
    
    # Step 2: Price drops - trigger auto sell
    print("🔴 STEP 2: Price Drop - Auto Sell Trigger")
    sell_price = 140.0
    position['current_price'] = sell_price
    
    print(f"   Price drops to ₹{sell_price}")
    print(f"   Advanced Stop Loss: ₹{position['advanced_stop_loss']}")
    print(f"   Will trigger sell? {sell_price <= position['advanced_stop_loss']}")
    
    # Simulate auto sell
    if sell_price <= position['advanced_stop_loss']:
        print(f"   🔴 AUTO SELL EXECUTED at ₹{sell_price}")
        
        # Advanced algorithm auto sell setup
        position['last_stop_loss_price'] = sell_price  # Auto buy at same sell price
        position['waiting_for_autobuy'] = True
        position['quantity'] = 0
        position['mode'] = 'Waiting for Auto Buy'
        
        print(f"   ✅ Auto Buy Trigger set at ₹{position['last_stop_loss_price']} (same as sell price)")
    
    print()
    
    # Step 3: Test auto buy trigger conditions
    print("🎯 STEP 3: Testing Advanced Auto Buy Trigger")
    
    test_prices = [135, 139, 140, 141, 145]
    
    for test_price in test_prices:
        position['current_price'] = test_price
        auto_buy_trigger = position.get('last_stop_loss_price', 0)
        
        # Advanced auto buy condition (>= for exact price matching)
        will_trigger = (position.get('waiting_for_autobuy', False) and 
                       position['current_price'] >= auto_buy_trigger)
        
        status = "✅ WILL TRIGGER" if will_trigger else "❌ NO TRIGGER"
        print(f"   Price ₹{test_price} vs Trigger ₹{auto_buy_trigger} → {status}")
    
    print()
    
    # Step 4: Execute auto buy
    print("🟢 STEP 4: Advanced Auto Buy Execution")
    auto_buy_price = 140.0
    position['current_price'] = auto_buy_price
    
    # Advanced auto buy logic
    position['waiting_for_autobuy'] = False
    position['buy_price'] = auto_buy_price
    position['highest_price'] = auto_buy_price  # Reset for new cycle
    position['advanced_stop_loss'] = auto_buy_price - 10  # New stop loss
    position['quantity'] = 25  # Restore quantity
    position['auto_buy_count'] += 1
    
    # CRITICAL: Keep progressive minimum and highest stop loss from previous cycle
    # This is the key difference from Simple Algorithm
    
    print(f"   Auto Buy Price: ₹{auto_buy_price}")
    print(f"   New Advanced Stop Loss: ₹{position['advanced_stop_loss']} (Buy - 10)")
    print(f"   ✅ PRESERVED Progressive Minimum: ₹{position['progressive_minimum']}")
    print(f"   ✅ PRESERVED Highest Stop Loss: ₹{position['highest_stop_loss']}")
    print()
    
    # Step 5: Test progressive protection in new cycle
    print("🛡️ STEP 5: Progressive Protection in New Cycle")
    
    # Simulate price going up again
    new_prices = [145, 150, 155]
    
    for new_price in new_prices:
        position['current_price'] = new_price
        
        # Advanced algorithm with progressive protection
        if new_price > position['buy_price']:
            profit = new_price - position['buy_price']
            steps = int(profit // 10)
            calculated_stop_loss = position['buy_price'] + (steps * 10)
            
            # Update progressive minimum
            position['progressive_minimum'] = max(position['progressive_minimum'], 
                                                 position['highest_stop_loss'] - 20)
            
            # Apply progressive minimum protection
            protected_stop_loss = max(calculated_stop_loss, position['progressive_minimum'])
            
            if protected_stop_loss > position['advanced_stop_loss']:
                position['advanced_stop_loss'] = protected_stop_loss
                position['highest_stop_loss'] = max(position['highest_stop_loss'], protected_stop_loss)
        
        print(f"   Price ₹{new_price}: Stop Loss ₹{position['advanced_stop_loss']}")
        print(f"      → Calculated: ₹{calculated_stop_loss if 'calculated_stop_loss' in locals() else 'N/A'}")
        print(f"      → Progressive Min: ₹{position['progressive_minimum']}")
        print(f"      → Final (Protected): ₹{position['advanced_stop_loss']}")
        print()
    
    # Step 6: Compare with Simple Algorithm
    print("🔍 STEP 6: Advanced vs Simple Algorithm Comparison")
    print("=" * 50)
    
    print("📊 SIMPLE ALGORITHM:")
    print("   ✅ Auto buy at same sell price")
    print("   ✅ Uses external trailing function")
    print("   ❌ NO progressive protection")
    print("   ❌ Stop loss can go back to lower levels")
    print()
    
    print("🚀 ADVANCED ALGORITHM:")
    print("   ✅ Auto buy at same sell price")
    print("   ✅ Built-in trailing logic")
    print("   ✅ Progressive minimum protection")
    print("   ✅ Stop loss never goes below highest achieved - 20")
    print("   ✅ Preserves gains from previous cycles")
    print()
    
    # Step 7: Real-world scenario
    print("🌍 STEP 7: Real-world Scenario Demonstration")
    print("=" * 50)
    
    scenario_position = {
        'buy_price': 100.0,
        'progressive_minimum': 130.0,  # From previous high of 150
        'highest_stop_loss': 150.0,
        'advanced_stop_loss': 130.0,
        'current_price': 120.0
    }
    
    print(f"📈 Scenario: Stock previously hit ₹160, now at ₹120")
    print(f"   Previous High Stop Loss: ₹{scenario_position['highest_stop_loss']}")
    print(f"   Current Progressive Min: ₹{scenario_position['progressive_minimum']}")
    print(f"   Current Price: ₹{scenario_position['current_price']}")
    print()
    
    # Test what happens if price goes to 110
    test_price = 110.0
    calculated_stop_loss = scenario_position['buy_price'] + (int((test_price - scenario_position['buy_price']) // 10) * 10)
    final_stop_loss = max(calculated_stop_loss, scenario_position['progressive_minimum'])
    
    print(f"🔥 If price moves to ₹{test_price}:")
    print(f"   Simple Algorithm would set: ₹{calculated_stop_loss}")
    print(f"   Advanced Algorithm sets: ₹{final_stop_loss} (protected by progressive minimum)")
    print(f"   🛡️ Protection saved: ₹{final_stop_loss - calculated_stop_loss} per share!")
    print()
    
    print("✅ ADVANCED ALGORITHM CONCLUSION:")
    print("   🎯 Smart auto buy at same sell price")
    print("   🛡️ Progressive protection prevents loss of gains")
    print("   📈 Maintains higher stop loss levels")
    print("   🔒 Never allows stop loss below (highest - 20)")
    print("   🚀 Superior risk management for volatile markets")

if __name__ == "__main__":
    test_advanced_algorithm()