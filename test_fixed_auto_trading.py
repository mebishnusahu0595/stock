#!/usr/bin/env python3
"""
Test script to verify the FIXED auto trading logic maintains proper 10-point gaps
Based on the actual trade sequence provided by the user
"""

# Simulate the app_state for testing
app_state = {
    'auto_positions': [],
    'trade_history': [],
    'auto_trading_config': {
        'stop_loss_points': 10,
        'trailing_step': 10,
        'auto_buy_buffer': 0
    }
}

def create_test_position(strike, option_type, buy_price, qty=1):
    """Create a test position similar to the real create_auto_position"""
    stop_loss_price = buy_price - app_state['auto_trading_config']['stop_loss_points']
    
    position = {
        'id': f"test_{strike}_{option_type}",
        'symbol': 'NIFTY',
        'strike': strike,
        'type': option_type,
        'qty': qty,
        'buy_price': buy_price,
        'original_buy_price': buy_price,
        'current_price': buy_price,
        'highest_price': buy_price,
        'stop_loss_price': stop_loss_price,
        'minimum_stop_loss': stop_loss_price,
        'auto_bought': False,
        'waiting_for_autobuy': False,
        'sold': False,
        'manual_sold': False,
        'mode': 'Running'
    }
    return position

def update_trailing_stop_loss(position):
    """FIXED trailing stop loss logic"""
    trailing_step = app_state['auto_trading_config']['trailing_step']  # 10
    stop_loss_point = app_state['auto_trading_config']['stop_loss_points']  # 10
    
    # Get the original buy price 
    original_buy_price = position.get('original_buy_price', position['buy_price'])
    current_stop_loss = position.get('stop_loss_price', 0)
    # Get absolute minimum stop loss - NEVER go below this!
    minimum_stop_loss = position.get('minimum_stop_loss', original_buy_price - stop_loss_point)
    
    if position.get('auto_bought'):
        # FIXED AUTO BUY TRAILING: Always maintain 10-point stop loss below auto buy price
        auto_buy_price = position['buy_price']
        highest_after_auto_buy = position['highest_price']
        profit_from_auto_buy = highest_after_auto_buy - auto_buy_price
        
        if profit_from_auto_buy >= trailing_step:  # If profit >= 10
            # Calculate how many 10-rupee steps we've achieved
            profit_steps = int(profit_from_auto_buy // trailing_step)
            # Stop loss = auto buy price - 10 + (steps * 10)
            new_trailing_stop_loss = auto_buy_price - stop_loss_point + (profit_steps * trailing_step)
            position['stop_loss_price'] = max(new_trailing_stop_loss, current_stop_loss, minimum_stop_loss)
        else:
            # No profit yet, stop loss = auto buy price - 10 (maintain 10-point protection)
            initial_stop_loss = auto_buy_price - stop_loss_point
            position['stop_loss_price'] = max(initial_stop_loss, current_stop_loss, minimum_stop_loss)
    else:
        # Manual buy: FIXED 10-POINT TRAILING
        highest_price = position['highest_price']
        profit = highest_price - original_buy_price
        
        if profit >= trailing_step:  # If profit >= 10
            profit_steps = int(profit // trailing_step)
            # Stop loss = buy price - 10 + (steps * 10)
            new_trailing_stop_loss = original_buy_price - stop_loss_point + (profit_steps * trailing_step)
            position['stop_loss_price'] = max(new_trailing_stop_loss, current_stop_loss, minimum_stop_loss)

def simulate_auto_buy(position):
    """Simulate auto buy with FIXED logic"""
    # Auto buy trigger: 10 points ABOVE where it was sold
    last_stop_loss = position.get('last_stop_loss_price', position.get('stop_loss_price', 0))
    auto_buy_trigger_price = last_stop_loss + 10  # FIXED: Add 10 points gap
    
    # Simulate auto buy at trigger price
    position['buy_price'] = auto_buy_trigger_price
    position['current_price'] = auto_buy_trigger_price
    position['highest_price'] = auto_buy_trigger_price
    
    # FIXED: Set stop loss exactly 10 points below auto buy price
    stop_loss_points = app_state['auto_trading_config']['stop_loss_points']
    calculated_stop_loss = auto_buy_trigger_price - stop_loss_points
    minimum_stop_loss = position.get('minimum_stop_loss', 0)
    position['stop_loss_price'] = max(calculated_stop_loss, minimum_stop_loss)
    
    position['auto_bought'] = True
    position['waiting_for_autobuy'] = False
    
    return auto_buy_trigger_price

def test_trade_sequence():
    """Test the EXACT trade sequence from user's complaint"""
    print("=== TESTING FIXED AUTO TRADING LOGIC ===")
    print("Testing the exact trade sequence that was failing\n")
    
    # 1. Manual Buy -> 146.35
    print("1. Manual Buy -> 146.35")
    position = create_test_position(24500, 'CE', 146.35)
    print(f"   Position created: Buy ₹{position['buy_price']} | Stop Loss ₹{position['stop_loss_price']}")
    
    # 2. Price goes up to trigger first auto sell -> should be around 154.60 (not perfect 10 gap due to real market)
    print("\n2. Price rises to 154.60 - CHECK AUTO SELL")
    position['current_price'] = 154.60
    position['highest_price'] = 154.60
    update_trailing_stop_loss(position)
    
    print(f"   Current: ₹{position['current_price']} | Stop Loss: ₹{position['stop_loss_price']}")
    
    # Simulate auto sell at stop loss
    if position['current_price'] <= position['stop_loss_price']:
        print(f"   ❌ STOP LOSS HIT: Selling at ₹{position['current_price']}")
        # Record the stop loss price for auto buy calculation
        position['last_stop_loss_price'] = position['stop_loss_price']
        position['waiting_for_autobuy'] = True
        auto_sell_price = position['current_price']
    else:
        print(f"   ✅ No stop loss trigger yet")
        return
    
    # 3. Auto Buy -> Should be at stop loss + 10 = 154.60 + 10 = 164.60 (FIXED)
    print(f"\n3. AUTO BUY TRIGGER - FIXED LOGIC")
    auto_buy_price = simulate_auto_buy(position)
    print(f"   FIXED Auto Buy: ₹{auto_buy_price} (Last Stop Loss ₹{position['last_stop_loss_price']} + 10)")
    print(f"   New Stop Loss: ₹{position['stop_loss_price']} (Auto Buy ₹{auto_buy_price} - 10)")
    
    gap_1 = auto_buy_price - auto_sell_price
    print(f"   GAP ANALYSIS: Sell ₹{auto_sell_price} -> Buy ₹{auto_buy_price} = ₹{gap_1:.2f} gap")
    
    # 4. Price drops to trigger next auto sell
    print(f"\n4. Price drops to trigger AUTO SELL")
    sell_price_2 = position['stop_loss_price'] - 0.5  # Simulate slight overshoot
    position['current_price'] = sell_price_2
    
    print(f"   Current: ₹{position['current_price']} | Stop Loss: ₹{position['stop_loss_price']}")
    print(f"   ❌ STOP LOSS HIT: Selling at ₹{sell_price_2}")
    
    # Record for next auto buy
    position['last_stop_loss_price'] = position['stop_loss_price']
    position['waiting_for_autobuy'] = True
    
    # 5. Next Auto Buy
    print(f"\n5. NEXT AUTO BUY TRIGGER")
    auto_buy_price_2 = simulate_auto_buy(position)
    print(f"   FIXED Auto Buy #2: ₹{auto_buy_price_2} (Last Stop Loss ₹{position['last_stop_loss_price']} + 10)")
    print(f"   New Stop Loss: ₹{position['stop_loss_price']} (Auto Buy ₹{auto_buy_price_2} - 10)")
    
    gap_2 = auto_buy_price_2 - sell_price_2
    print(f"   GAP ANALYSIS: Sell ₹{sell_price_2} -> Buy ₹{auto_buy_price_2} = ₹{gap_2:.2f} gap")
    
    print(f"\n=== RESULTS ===")
    print(f"Manual Buy: ₹146.35")
    print(f"Auto Sell: ₹{auto_sell_price} (Gap from buy: ₹{auto_sell_price - 146.35:.2f})")
    print(f"Auto Buy: ₹{auto_buy_price} (Gap from sell: ₹{gap_1:.2f})")
    print(f"Auto Sell #2: ₹{sell_price_2}")
    print(f"Auto Buy #2: ₹{auto_buy_price_2} (Gap from sell: ₹{gap_2:.2f})")
    
    if gap_1 >= 9.5 and gap_2 >= 9.5:
        print(f"\n✅ SUCCESS: All gaps are approximately 10 points!")
    else:
        print(f"\n❌ ISSUE: Gaps are not 10 points")
    
def test_simple_10_point_logic():
    """Test simple 10-point gaps"""
    print("\n=== TESTING SIMPLE 10-POINT LOGIC ===")
    
    # Manual buy at 100
    position = create_test_position(24500, 'CE', 100.0)
    print(f"Manual Buy: ₹{position['buy_price']}")
    print(f"Initial Stop Loss: ₹{position['stop_loss_price']}")
    
    # Price goes to 110 - should trigger first trailing step
    position['current_price'] = 110.0
    position['highest_price'] = 110.0
    update_trailing_stop_loss(position)
    print(f"\nPrice rises to ₹110:")
    print(f"Stop Loss: ₹{position['stop_loss_price']} (should be ₹100)")
    
    # Price goes to 120 - should trigger second trailing step  
    position['current_price'] = 120.0
    position['highest_price'] = 120.0
    update_trailing_stop_loss(position)
    print(f"\nPrice rises to ₹120:")
    print(f"Stop Loss: ₹{position['stop_loss_price']} (should be ₹110)")
    
    # Auto sell at stop loss
    sell_price = 110.0
    position['last_stop_loss_price'] = 110.0
    position['waiting_for_autobuy'] = True
    
    # Auto buy should be at 110 + 10 = 120
    auto_buy_price = simulate_auto_buy(position)
    print(f"\nAuto Sell at: ₹{sell_price}")
    print(f"Auto Buy at: ₹{auto_buy_price} (should be ₹120)")
    print(f"Gap: ₹{auto_buy_price - sell_price} (should be ₹10)")

if __name__ == "__main__":
    test_trade_sequence()
    test_simple_10_point_logic()
