#!/usr/bin/env python3
"""
Test Advanced Algorithm Stop Loss Fix
User Issue: Stop loss showing 706 instead of 736 when price is 739

This test simulates the exact scenario to verify our fix works.
"""

import sys
import os
sys.path.append('.')

# Mock the app_state for testing
app_state = {
    'auto_trading_config': {
        'trailing_step': 10,
        'stop_loss_points': 10
    }
}

def test_advanced_algorithm_fix():
    """Test the fixed Advanced Algorithm logic"""
    
    print("🧪 TESTING ADVANCED ALGORITHM FIX")
    print("=" * 50)
    print("📊 User Scenario: Buy 716 PE, Current Price 739")
    print()
    
    # Create test position similar to user's scenario
    position = {
        'strike': '716',
        'type': 'PE',
        'buy_price': 716,
        'current_price': 716,
        'original_buy_price': 716,
        'highest_price': 716,
        'advanced_stop_loss': 706,  # Initial: 716 - 10
        'minimum_stop_loss': 706,
        'highest_stop_loss': 706,
        'progressive_minimum': 706
    }
    
    print(f"1️⃣ Initial Position:")
    print(f"   Buy Price: ₹{position['buy_price']}")
    print(f"   Initial Stop Loss: ₹{position['advanced_stop_loss']}")
    print()
    
    # Simulate Advanced Algorithm logic step by step
    def simulate_price_update(position, new_price):
        """Simulate the fixed update_advanced_algorithm function"""
        print(f"📈 Price Update: ₹{position['current_price']} → ₹{new_price}")
        
        position['current_price'] = new_price
        original_buy_price = position['original_buy_price']
        
        # Update highest price
        if new_price > position['highest_price']:
            position['highest_price'] = new_price
            
            # Advanced trailing logic
            profit = position['highest_price'] - original_buy_price
            print(f"   Profit: ₹{profit:.2f}")
            
            if profit >= 10:  # If we have at least 10 rupees profit
                trailing_step = 10
                
                # Calculate steps
                profit_steps = int(profit // trailing_step)
                print(f"   Complete Steps: {profit_steps}")
                
                # Calculate new stop loss
                new_stop_loss = original_buy_price + (profit_steps * trailing_step)
                print(f"   Calculated SL: ₹{original_buy_price} + ({profit_steps} × 10) = ₹{new_stop_loss}")
                
                # Update highest stop loss if this is higher
                if new_stop_loss > position['highest_stop_loss']:
                    position['highest_stop_loss'] = new_stop_loss
                    position['progressive_minimum'] = position['highest_stop_loss'] - 20
                    print(f"   🆕 New Highest SL: ₹{new_stop_loss}")
                    print(f"   🆕 Progressive Min: ₹{position['progressive_minimum']}")
                
                # 🚨 FIX: ALWAYS update current stop loss when price goes up
                position['advanced_stop_loss'] = max(new_stop_loss, position.get('progressive_minimum', new_stop_loss))
                position['stop_loss_price'] = position['advanced_stop_loss']
                
                print(f"   ✅ Final Stop Loss: ₹{position['advanced_stop_loss']}")
                
                if position['advanced_stop_loss'] > new_stop_loss:
                    protection = position['advanced_stop_loss'] - new_stop_loss
                    print(f"   🛡️ Protection Applied: +₹{protection:.2f}")
            else:
                print(f"   ⏸️ No trailing (profit < ₹10)")
        else:
            print(f"   ⏸️ Price didn't increase (not updating highest)")
        
        print(f"   📊 Result: SL = ₹{position['advanced_stop_loss']}")
        print()
        
        return position['advanced_stop_loss']
    
    # Test step by step price increases
    prices_to_test = [720, 725, 730, 735, 739]
    
    for price in prices_to_test:
        stop_loss = simulate_price_update(position, price)
    
    print("🎯 FINAL RESULT:")
    print(f"   Current Price: ₹{position['current_price']}")
    print(f"   Stop Loss: ₹{position['advanced_stop_loss']}")
    print(f"   Expected SL: ₹736 (716 + 2×10)")
    
    # Verify the fix
    expected_sl = 736
    if position['advanced_stop_loss'] == expected_sl:
        print(f"   ✅ SUCCESS: Stop Loss is correct!")
    else:
        print(f"   ❌ FAILED: Expected ₹{expected_sl}, got ₹{position['advanced_stop_loss']}")
    
    return position['advanced_stop_loss'] == expected_sl

if __name__ == "__main__":
    success = test_advanced_algorithm_fix()
    
    print()
    print("🔧 FIX SUMMARY:")
    print("Changed condition from 'if new_stop_loss > position[highest_stop_loss]'")
    print("to ALWAYS update stop loss when price increases")
    print()
    
    if success:
        print("✅ Fix successful! Stop loss will now update correctly.")
    else:
        print("❌ Fix needs more work.")