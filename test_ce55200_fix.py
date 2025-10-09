#!/usr/bin/env python3
"""
Test CE55200 Advanced Algorithm Fix
Tests the stop loss calculation and auto buy trigger logic
"""

def test_ce55200_scenario():
    """Test CE55200 with advanced algorithm Phase 2"""
    
    print("🧪 CE55200 ADVANCED ALGORITHM TEST")
    print("=" * 50)
    
    # Your CE55200 position
    position = {
        'strike': 55200,
        'type': 'CE',
        'option_type': 'CE',
        'manual_buy_price': 673.60,  # Original manual buy
        'buy_price': 673.60,
        'original_buy_price': 673.60,
        'current_price': 701.75,     # Current market price
        'highest_price': 701.75,     # Highest seen so far
        'stop_loss_price': 692.00,   # Current (wrong) stop loss
        'advanced_stop_loss': 692.00,
        'algorithm_phase': 2,        # Should be Phase 2
        'progressive_minimum': 673.60, # Activated at manual buy
        'waiting_for_autobuy': False,
        'auto_bought': False
    }
    
    print(f"📊 CURRENT SCENARIO:")
    print(f"   Manual Buy: ₹{position['manual_buy_price']}")
    print(f"   Current Price: ₹{position['current_price']}")
    print(f"   Highest Price: ₹{position['highest_price']}")
    print(f"   Current Stop Loss: ₹{position['stop_loss_price']} (WRONG)")
    print(f"   Phase: {position['algorithm_phase']}")
    print()
    
    # Apply the new advanced algorithm logic
    def apply_advanced_algorithm_fix(position, new_price):
        """Apply the fixed advanced algorithm logic"""
        manual_buy_price = position['manual_buy_price']
        
        # Update current price and highest
        position['current_price'] = new_price
        if new_price > position['highest_price']:
            position['highest_price'] = new_price
        
        # Determine phase
        price_above_buy = new_price - manual_buy_price
        if price_above_buy < 20:
            position['algorithm_phase'] = 1
        elif price_above_buy < 30:
            position['algorithm_phase'] = 2
        else:
            position['algorithm_phase'] = 3
        
        print(f"🔄 PHASE {position['algorithm_phase']}: Manual Buy ₹{manual_buy_price} | Current ₹{new_price} | Above Buy: +₹{price_above_buy:.2f}")
        
        # Apply Phase 2 logic (Buy+20 to Buy+30)
        if position['algorithm_phase'] == 2:
            # Activate progressive minimum
            if position.get('progressive_minimum') is None:
                position['progressive_minimum'] = manual_buy_price
                print(f"🚨 PROGRESSIVE MINIMUM ACTIVATED: ₹{position['progressive_minimum']}")
            
            # Fixed Phase 2 trailing: step-wise from buy price
            profit = position['highest_price'] - manual_buy_price
            trailing_step = 10
            
            if profit >= 10:
                profit_steps = int(profit // trailing_step)
                step_stop_loss = manual_buy_price + (profit_steps * trailing_step)
                position['advanced_stop_loss'] = max(step_stop_loss, position['progressive_minimum'])
                
                print(f"📍 PHASE 2 FIX: Buy ₹{manual_buy_price} | High ₹{position['highest_price']} | Profit ₹{profit:.2f} | Steps {profit_steps}")
                print(f"   SL = ₹{manual_buy_price} + ({profit_steps}×10) = ₹{step_stop_loss} | Progressive Min ₹{position['progressive_minimum']} → Final SL ₹{position['advanced_stop_loss']}")
            else:
                position['advanced_stop_loss'] = position['progressive_minimum']
                print(f"📍 PHASE 2: No profit yet, using Progressive Min ₹{position['progressive_minimum']}")
        
        position['stop_loss_price'] = position['advanced_stop_loss']
        return position
    
    # Test the fix
    print("🔧 APPLYING ADVANCED ALGORITHM FIX:")
    print("-" * 40)
    fixed_position = apply_advanced_algorithm_fix(position.copy(), position['current_price'])
    
    print()
    print("📊 RESULTS COMPARISON:")
    print("-" * 40)
    print(f"   Manual Buy Price: ₹{fixed_position['manual_buy_price']}")
    print(f"   Current Price: ₹{fixed_position['current_price']}")
    print(f"   Highest Price: ₹{fixed_position['highest_price']}")
    print(f"   Price Above Buy: +₹{fixed_position['current_price'] - fixed_position['manual_buy_price']:.2f}")
    print()
    print(f"   OLD Stop Loss: ₹{position['stop_loss_price']} ❌")
    print(f"   NEW Stop Loss: ₹{fixed_position['stop_loss_price']} ✅")
    print()
    
    # Calculate what the correct stop loss should be
    profit = fixed_position['highest_price'] - fixed_position['manual_buy_price']
    profit_steps = int(profit // 10)
    expected_sl = fixed_position['manual_buy_price'] + (profit_steps * 10)
    
    print("🧮 STEP CALCULATION:")
    print(f"   Profit: ₹{fixed_position['highest_price']} - ₹{fixed_position['manual_buy_price']} = ₹{profit:.2f}")
    print(f"   Steps: {profit:.2f} ÷ 10 = {profit_steps} steps")
    print(f"   Expected SL: ₹{fixed_position['manual_buy_price']} + ({profit_steps} × 10) = ₹{expected_sl}")
    print()
    
    # Test auto buy trigger logic
    print("🎯 AUTO BUY TRIGGER TEST:")
    print("-" * 40)
    
    # Simulate sell at stop loss
    sell_price = fixed_position['stop_loss_price']
    print(f"   Simulated Sell at Stop Loss: ₹{sell_price}")
    
    # Test auto buy triggers for Phase 2
    test_prices = [690, 692, 693.60, 695, 673.60]
    
    for test_price in test_prices:
        # Phase 2 should use stop loss trigger, not manual buy price
        phase = fixed_position['algorithm_phase']
        if phase == 1:
            # Phase 1: Manual buy price trigger
            trigger_price = fixed_position['manual_buy_price']
            should_buy = test_price >= trigger_price
            trigger_type = "Manual Buy Price"
        else:
            # Phase 2/3: Stop loss price trigger
            trigger_price = sell_price
            should_buy = abs(test_price - trigger_price) <= 1  # ±1 buffer
            trigger_type = "Stop Loss Price"
        
        status = "✅ AUTO BUY" if should_buy else "❌ NO AUTO BUY"
        print(f"   Price ₹{test_price}: {trigger_type} ₹{trigger_price} → {status}")
    
    print()
    print("🎯 EXPECTED BEHAVIOR:")
    print("   1. Stop Loss = ₹693.60 (not ₹692.00)")
    print("   2. Auto Buy when price comes back to ₹693.60 ± 1")
    print("   3. NOT at manual buy price ₹673.60 for Phase 2")

if __name__ == "__main__":
    test_ce55200_scenario()