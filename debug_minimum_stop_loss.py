"""
CRITICAL STOP LOSS ANALYSIS FOR USER CONCERN

Current Issue: User is concerned that stop loss might go below absolute minimum (e.g., below ₹90 for ₹100 buy)

CURRENT CODE PROBLEMS:
1. minimum_stop_loss field is set but NEVER USED in update_trailing_stop_loss()
2. Stop loss can theoretically go below buy_price - 10 points
3. No absolute minimum protection

EXAMPLE SCENARIO USER IS WORRIED ABOUT:
- Buy at ₹100
- Stop loss should NEVER go below ₹90 (₹100 - 10)
- But current code only uses max(new_stop_loss, current_stop_loss)
- Missing: max(calculated_stop_loss, minimum_stop_loss)

REQUIRED FIX:
Add minimum_stop_loss protection in update_trailing_stop_loss function
"""

# Test the current behavior
def test_current_stop_loss_logic():
    # Simulate Buy ₹100 position
    position = {
        'buy_price': 100,
        'original_buy_price': 100,
        'highest_price': 100,
        'stop_loss_price': 90,  # Initial: 100 - 10
        'minimum_stop_loss': 90,  # Should NEVER go below this
        'auto_bought': False
    }
    
    config = {
        'stop_loss_points': 10,
        'trailing_step': 10
    }
    
    print("🧪 TESTING CURRENT STOP LOSS LOGIC")
    print(f"📍 Initial Position: Buy ₹{position['buy_price']} | Stop Loss ₹{position['stop_loss_price']} | Min Stop Loss ₹{position['minimum_stop_loss']}")
    
    # Test 1: Price goes to ₹110 (profit = 10)
    position['highest_price'] = 110
    
    # Current logic (from app.py)
    trailing_step = config['trailing_step']
    stop_loss_point = config['stop_loss_points']
    original_buy_price = position['original_buy_price']
    current_stop_loss = position['stop_loss_price']
    
    highest_price = position['highest_price']
    profit = highest_price - original_buy_price
    
    if profit >= trailing_step:  # 10 >= 10
        profit_steps = int(profit // trailing_step)  # 1 step
        new_trailing_stop_loss = original_buy_price + (profit_steps * trailing_step)  # 100 + 10 = 110
        position['stop_loss_price'] = max(new_trailing_stop_loss, current_stop_loss)  # max(110, 90) = 110
    
    print(f"📈 Price ₹110: New Stop Loss ₹{position['stop_loss_price']} (GOOD - Above minimum ₹{position['minimum_stop_loss']})")
    
    # Test 2: What if there was a bug and stop loss tried to go to ₹80?
    # This shouldn't happen with current logic, but let's test the protection
    fake_bad_stop_loss = 80
    
    # CURRENT CODE ISSUE: No minimum_stop_loss protection!
    print(f"🚨 CURRENT ISSUE: If stop loss tried to go to ₹{fake_bad_stop_loss}, current code would NOT check minimum_stop_loss!")
    print(f"❌ Current max() only uses: max({fake_bad_stop_loss}, {current_stop_loss}) = {max(fake_bad_stop_loss, current_stop_loss)}")
    print(f"✅ SHOULD use: max({fake_bad_stop_loss}, {current_stop_loss}, {position['minimum_stop_loss']}) = {max(fake_bad_stop_loss, current_stop_loss, position['minimum_stop_loss'])}")

if __name__ == "__main__":
    test_current_stop_loss_logic()
