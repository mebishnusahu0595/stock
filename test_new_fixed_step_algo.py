#!/usr/bin/env python3
"""
Test script for NEW Advanced Algorithm with Fixed ₹10 Steps
USER REQUIREMENTS:
- Remove 2% logic
- Use fixed ₹10 steps: Stop Loss = Current High Price - ₹10
- Progressive minimum = highest_stop_loss - ₹20
- Auto buy at same sell price
- Never go below progressive minimum

EXAMPLE SCENARIO:
Buy ₹100 → SL ₹90
Price ₹120 → SL ₹110, Progressive Min ₹90 (110-20)
Sell ₹110 → Auto Buy ₹110 → SL ₹100 (110-10), but Progressive Min ₹90, so SL ₹100 ✅
Price ₹167 → SL ₹157, Progressive Min ₹137 (157-20)
Sell ₹157 → Auto Buy ₹157 → SL ₹147 (157-10), Progressive Min ₹137, so SL ₹147 ✅
Sell ₹147 → Auto Buy ₹147 → SL ₹137 (147-10), Progressive Min ₹137, so SL ₹137 ✅
"""

# Mock the required functions and state
class MockPosition:
    def __init__(self, **kwargs):
        self.data = kwargs
    
    def get(self, key, default=None):
        return self.data.get(key, default)
    
    def __getitem__(self, key):
        return self.data[key]
    
    def __setitem__(self, key, value):
        self.data[key] = value
    
    def __contains__(self, key):
        return key in self.data

# Mock datetime
from datetime import datetime as dt

# Mock execute functions
def execute_auto_sell(position, reason="Test"):
    print(f"🚨 AUTO SELL EXECUTED: {reason} at ₹{position['current_price']}")
    return True

def execute_auto_buy(position):
    print(f"🎯 AUTO BUY EXECUTED at ₹{position['current_price']}")
    return True

def update_advanced_algorithm(position, new_price):
    """NEW Advanced algorithm: Fixed ₹10 step trailing with progressive minimum protection"""
    print(f"\n[DEBUG] ADVANCED ALGORITHM CALLED | Price: {new_price}")
    old_price = float(position['current_price'])
    position['current_price'] = new_price
    position['last_update'] = dt.now()
    
    # Initialize required fields for advanced algorithm
    if 'original_buy_price' not in position:
        position['original_buy_price'] = position.get('buy_price', position.get('average_price', new_price))
    if 'highest_price' not in position:
        position['highest_price'] = position['original_buy_price']
    if 'advanced_stop_loss' not in position:
        position['advanced_stop_loss'] = position['original_buy_price'] - 10  # Initial stop loss (buy_price - 10)
    if 'minimum_stop_loss' not in position:
        position['minimum_stop_loss'] = position['original_buy_price'] - 10  # Minimum stop loss threshold
    if 'highest_stop_loss' not in position:
        position['highest_stop_loss'] = position['original_buy_price'] - 10  # Track highest stop loss ever reached
    if 'progressive_minimum' not in position:
        position['progressive_minimum'] = position['original_buy_price'] - 10  # Progressive minimum protection
    
    original_buy_price = position['original_buy_price']
    
    # Update highest price and trailing logic
    if new_price > position['highest_price']:
        position['highest_price'] = new_price
        
        # 🚨 NEW LOGIC: Fixed ₹10 step trailing (no percentage, no step calculation)
        # Simply: Stop Loss = Current High Price - ₹10
        new_stop_loss = position['highest_price'] - 10
        
        # Update highest stop loss if this is higher
        old_highest_sl = position.get('highest_stop_loss', 0)
        if new_stop_loss > position['highest_stop_loss']:
            position['highest_stop_loss'] = new_stop_loss
            # 🚨 USER REQUIREMENT: Progressive minimum = highest_stop_loss - ₹20
            position['progressive_minimum'] = position['highest_stop_loss'] - 20
            print(f"📈 NEW HIGHEST SL: ₹{old_highest_sl} → ₹{new_stop_loss} | Progressive Min: ₹{position['progressive_minimum']}")
        
        # Apply progressive minimum protection
        position['advanced_stop_loss'] = max(new_stop_loss, position.get('progressive_minimum', new_stop_loss))
        
        print(f"🔥 ADVANCED FIXED STEP TRAIL: High ₹{position['highest_price']} → Stop Loss ₹{new_stop_loss} (High - 10)")
        print(f"   FINAL STOP LOSS: ₹{position['advanced_stop_loss']} (max of calculated ₹{new_stop_loss} and progressive min ₹{position.get('progressive_minimum', new_stop_loss)})")
        
        if position['advanced_stop_loss'] > new_stop_loss:
            protection = position['advanced_stop_loss'] - new_stop_loss
            print(f"🛡️ PROGRESSIVE PROTECTION: Stop Loss protected by ₹{protection:.2f} (at ₹{position['advanced_stop_loss']})")
    
    # Update traditional stop_loss_price for display purposes
    position['stop_loss_price'] = position['advanced_stop_loss']
    
    # Debug print for monitoring
    print(f"🔍 MONITORING: Current: ₹{new_price} | Advanced SL: ₹{position['advanced_stop_loss']} | Progressive Min: ₹{position.get('progressive_minimum', 'N/A')}")
    
    # Check for stop loss trigger (use <= to trigger when price hits or goes below stop loss)
    if (position['current_price'] <= position['advanced_stop_loss'] and 
        position['advanced_stop_loss'] > 0 and 
        not position.get('waiting_for_autobuy', False) and
        not position.get('sell_triggered', False)):
        
        # AUTO SELL - Advanced Stop Loss Hit
        profit = position['current_price'] - original_buy_price
        reason = 'Advanced Trailing Stop Loss' if profit > 0 else 'Advanced Stop Loss'
        
        print(f"🚨 ADVANCED STOP LOSS TRIGGERED @ ₹{new_price} (Stop Loss: ₹{position['advanced_stop_loss']}, Profit: ₹{profit:.2f})")
        sell_executed = execute_auto_sell(position, reason=reason)
        if sell_executed:
            position['sell_triggered'] = True
            
            # 🚨 USER REQUIREMENT: Auto buy at SAME price where it was sold
            position['waiting_for_autobuy'] = True
            position['last_stop_loss_price'] = position['current_price']  # Auto buy at same price as sell
            position['mode'] = 'Waiting for Auto Buy (Advanced - Same Price)'
            
            return True
        return False
    
    # Check for auto buy trigger
    auto_buy_trigger = position.get('last_stop_loss_price', 0)
    if (position.get('waiting_for_autobuy', False) and 
        position['current_price'] >= auto_buy_trigger):
        
        print(f"🎯 ADVANCED AUTO BUY TRIGGER | Current: ₹{position['current_price']} | Trigger: ₹{auto_buy_trigger}")
        
        # Execute auto buy
        buy_executed = execute_auto_buy(position)
        if buy_executed:
            # 🚨 USER REQUIREMENT: After auto buy, set new parameters correctly
            auto_buy_price = position['current_price']
            position['buy_price'] = auto_buy_price  # Update buy price to auto buy price
            position['highest_price'] = auto_buy_price  # Reset highest price
            
            # Reset flags
            position['sell_triggered'] = False
            position['waiting_for_autobuy'] = False
            
            # 🚨 PROGRESSIVE PROTECTION: Calculate stop loss with protection
            calculated_stop_loss = auto_buy_price - 10  # Normal: auto buy price - 10
            progressive_min = position.get('progressive_minimum', calculated_stop_loss)
            
            # Apply progressive minimum protection
            position['advanced_stop_loss'] = max(calculated_stop_loss, progressive_min)
            
            print(f"🛡️ AUTO BUY STOP LOSS CALCULATION:")
            print(f"   Auto Buy Price: ₹{auto_buy_price}")
            print(f"   Calculated Stop Loss: ₹{calculated_stop_loss} ({auto_buy_price} - 10)")
            print(f"   Progressive Minimum: ₹{progressive_min}")
            print(f"   Final Stop Loss: ₹{position['advanced_stop_loss']} (max of both)")
            
            if position['advanced_stop_loss'] > calculated_stop_loss:
                print(f"🛡️ PROTECTION APPLIED: Stop Loss protected at ₹{position['advanced_stop_loss']} (₹{position['advanced_stop_loss'] - calculated_stop_loss} higher)")
            
            print(f"🎯 ADVANCED AUTO BUY COMPLETE: Buy ₹{auto_buy_price} | Stop Loss ₹{position['advanced_stop_loss']} | Progressive Min: ₹{position.get('progressive_minimum', 'N/A')}")
            return True
        return False
    
    return False

def test_user_exact_scenario():
    """Test the exact scenario provided by user"""
    print("=" * 80)
    print("🧪 TESTING USER'S EXACT SCENARIO")
    print("=" * 80)
    
    # Create position
    position = MockPosition(
        strike='TEST',
        type='CE',
        buy_price=100,
        current_price=100,
        quantity=1
    )
    
    prices = [100, 120, 110, 110, 167, 157, 157, 147, 147]
    actions = [
        "Manual Buy",
        "Price increase (should trail SL)",
        "Price drop to SL (should sell)",
        "Auto buy trigger",
        "Price increase (should trail SL)",
        "Price drop to SL (should sell)",
        "Auto buy trigger",
        "Price drop to SL (should sell)",
        "Auto buy trigger"
    ]
    
    print(f"\n🚀 STARTING TEST: Manual Buy at ₹{prices[0]}")
    print(f"   Initial Stop Loss: ₹{prices[0] - 10} = ₹{90}")
    
    for i, (price, action) in enumerate(zip(prices, actions)):
        print(f"\n{'='*60}")
        print(f"STEP {i+1}: {action} - Price ₹{price}")
        print('='*60)
        
        result = update_advanced_algorithm(position, price)
        
        # Print current state
        print(f"\n📊 CURRENT STATE:")
        print(f"   Current Price: ₹{position['current_price']}")
        print(f"   Advanced Stop Loss: ₹{position.get('advanced_stop_loss', 'N/A')}")
        print(f"   Highest Stop Loss Ever: ₹{position.get('highest_stop_loss', 'N/A')}")
        print(f"   Progressive Minimum: ₹{position.get('progressive_minimum', 'N/A')}")
        print(f"   Waiting for Auto Buy: {position.get('waiting_for_autobuy', False)}")
        
        if result:
            print(f"✅ ACTION TRIGGERED: {'Sell' if not position.get('waiting_for_autobuy', False) else 'Buy'}")
        else:
            print("⏳ NO ACTION - Monitoring...")

if __name__ == "__main__":
    test_user_exact_scenario()