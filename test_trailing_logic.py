#!/usr/bin/env python3
"""
Test Trailing Stop Loss Logic - Verify Current Implementation
"""

def test_trailing_logic():
    """Test the trailing stop loss calculation"""
    
    # Simulate app_state config
    trailing_step = 10
    stop_loss_point = 10
    
    def calculate_trailing_stop_loss(buy_price, current_price, original_stop_loss):
        """Simulate the current trailing logic"""
        profit = current_price - buy_price
        
        if profit >= trailing_step:
            # Calculate completed steps
            profit_steps = int(profit // trailing_step)
            
            # New stop loss = buy price + (steps × 10)
            new_stop_loss = buy_price + (profit_steps * trailing_step)
            
            # Never go below original stop loss
            final_stop_loss = max(new_stop_loss, original_stop_loss)
            
            return final_stop_loss, profit_steps
        else:
            # No trailing yet, keep original stop loss
            return original_stop_loss, 0
    
    print("🧪 TESTING TRAILING STOP LOSS LOGIC")
    print("=" * 50)
    
    # Test Case 1: Your Example 1
    print("\n📊 Test Case 1: Buy ₹100, Price ₹145")
    buy_price = 100
    current_price = 145
    original_stop_loss = 90  # 100 - 10
    
    new_stop_loss, steps = calculate_trailing_stop_loss(buy_price, current_price, original_stop_loss)
    
    print(f"   Buy Price: ₹{buy_price}")
    print(f"   Current Price: ₹{current_price}")
    print(f"   Profit: ₹{current_price - buy_price}")
    print(f"   Steps: {steps}")
    print(f"   Expected Stop Loss: ₹140")
    print(f"   Calculated Stop Loss: ₹{new_stop_loss}")
    print(f"   ✅ CORRECT!" if new_stop_loss == 140 else f"   ❌ WRONG!")
    
    # Test Case 2: Your Example 2
    print("\n📊 Test Case 2: Buy ₹100, Price ₹170")
    buy_price = 100
    current_price = 170
    original_stop_loss = 90
    
    new_stop_loss, steps = calculate_trailing_stop_loss(buy_price, current_price, original_stop_loss)
    
    print(f"   Buy Price: ₹{buy_price}")
    print(f"   Current Price: ₹{current_price}")
    print(f"   Profit: ₹{current_price - buy_price}")
    print(f"   Steps: {steps}")
    print(f"   Expected Stop Loss: ₹170")
    print(f"   Calculated Stop Loss: ₹{new_stop_loss}")
    print(f"   ✅ CORRECT!" if new_stop_loss == 170 else f"   ❌ WRONG!")
    
    # Test Case 3: Intermediate values
    print("\n📊 Test Case 3: Buy ₹100, Price ₹127 (1 step + partial)")
    buy_price = 100
    current_price = 127
    original_stop_loss = 90
    
    new_stop_loss, steps = calculate_trailing_stop_loss(buy_price, current_price, original_stop_loss)
    
    print(f"   Buy Price: ₹{buy_price}")
    print(f"   Current Price: ₹{current_price}")
    print(f"   Profit: ₹{current_price - buy_price}")
    print(f"   Steps: {steps} (only complete steps count)")
    print(f"   Expected Stop Loss: ₹110 (100 + 1×10)")
    print(f"   Calculated Stop Loss: ₹{new_stop_loss}")
    print(f"   ✅ CORRECT!" if new_stop_loss == 110 else f"   ❌ WRONG!")
    
    # Test Case 4: No trailing yet
    print("\n📊 Test Case 4: Buy ₹100, Price ₹108 (No trailing)")
    buy_price = 100
    current_price = 108
    original_stop_loss = 90
    
    new_stop_loss, steps = calculate_trailing_stop_loss(buy_price, current_price, original_stop_loss)
    
    print(f"   Buy Price: ₹{buy_price}")
    print(f"   Current Price: ₹{current_price}")
    print(f"   Profit: ₹{current_price - buy_price}")
    print(f"   Steps: {steps}")
    print(f"   Expected Stop Loss: ₹90 (original)")
    print(f"   Calculated Stop Loss: ₹{new_stop_loss}")
    print(f"   ✅ CORRECT!" if new_stop_loss == 90 else f"   ❌ WRONG!")

if __name__ == '__main__':
    test_trailing_logic()