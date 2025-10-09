#!/usr/bin/env python3
"""
🧪 TEST: NEW 3-Phase Advanced Algorithm
======================================

USER REQUIREMENTS:
🚨 PHASE 1 (Buy to Buy+20): SL = Buy-10, Auto buy at SAME buy price
🚨 PHASE 2 (Buy+20 to Buy+30): Progressive Min activated, SL = High-10  
🚨 PHASE 3 (After Buy+30): Step-wise algorithm like Simple

EXAMPLE:
Phase 1: Buy ₹100, Price ₹110 → SL ₹90, Auto buy at ₹100 (not sell price!)
Phase 2: Price ₹120 → SL ₹110, Progressive Min ₹100, Auto buy ₹110 → SL ₹100
Phase 3: Price ₹130 → Step algorithm: SL = 100 + (3×10) = ₹130
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
    """NEW Advanced algorithm: 3-Phase Logic"""
    print(f"\n[DEBUG] NEW ADVANCED ALGORITHM CALLED | Price: {new_price}")
    old_price = float(position['current_price'])
    position['current_price'] = new_price
    position['last_update'] = dt.now()
    
    # Initialize required fields for NEW advanced algorithm
    if 'original_buy_price' not in position:
        position['original_buy_price'] = position.get('buy_price', position.get('average_price', new_price))
    if 'manual_buy_price' not in position:
        position['manual_buy_price'] = position.get('buy_price', position.get('average_price', new_price))  # Never changes
    if 'highest_price' not in position:
        position['highest_price'] = position['original_buy_price']
    if 'advanced_stop_loss' not in position:
        position['advanced_stop_loss'] = position['original_buy_price'] - 10  # Initial stop loss (buy_price - 10)
    if 'algorithm_phase' not in position:
        position['algorithm_phase'] = 1  # Phase 1: Initial phase
    if 'progressive_minimum' not in position:
        position['progressive_minimum'] = None  # Not activated initially
    if 'highest_stop_loss' not in position:
        position['highest_stop_loss'] = position['original_buy_price'] - 10
    
    original_buy_price = position['original_buy_price']
    manual_buy_price = position['manual_buy_price']
    current_phase = position['algorithm_phase']
    
    # Determine current phase based on price levels
    price_above_buy = new_price - manual_buy_price
    
    if price_above_buy < 20:
        position['algorithm_phase'] = 1  # Phase 1: Below Buy+20
    elif price_above_buy < 30:
        position['algorithm_phase'] = 2  # Phase 2: Buy+20 to Buy+30
    else:
        position['algorithm_phase'] = 3  # Phase 3: Above Buy+30
    
    print(f"🔄 PHASE {position['algorithm_phase']}: Manual Buy ₹{manual_buy_price} | Current ₹{new_price} | Above Buy: +₹{price_above_buy:.2f}")
    
    # PHASE 1: Initial Stop Loss Logic (Buy to Buy+20)
    if position['algorithm_phase'] == 1:
        # Simple stop loss = manual_buy_price - 10
        position['advanced_stop_loss'] = manual_buy_price - 10
        position['progressive_minimum'] = None  # Not activated
        print(f"📍 PHASE 1: Simple SL = ₹{manual_buy_price} - 10 = ₹{position['advanced_stop_loss']}")
    
    # PHASE 2: Progressive Minimum Activation (Buy+20 to Buy+30)
    elif position['algorithm_phase'] == 2:
        # Update highest price for trailing
        if new_price > position['highest_price']:
            position['highest_price'] = new_price
        
        # Activate progressive minimum if not already activated
        if position['progressive_minimum'] is None:
            position['progressive_minimum'] = manual_buy_price  # Activate at manual buy price
            print(f"🚨 PROGRESSIVE MINIMUM ACTIVATED: ₹{position['progressive_minimum']}")
        
        # Calculate stop loss = highest_price - 10
        calculated_stop_loss = position['highest_price'] - 10
        position['advanced_stop_loss'] = max(calculated_stop_loss, position['progressive_minimum'])
        
        print(f"📍 PHASE 2: High ₹{position['highest_price']} → SL ₹{calculated_stop_loss} | Progressive Min ₹{position['progressive_minimum']} → Final SL ₹{position['advanced_stop_loss']}")
    
    # PHASE 3: Step-wise Algorithm (After Buy+30)
    elif position['algorithm_phase'] == 3:
        # Update highest price for trailing
        if new_price > position['highest_price']:
            position['highest_price'] = new_price
        
        # Step-wise calculation like Simple Algorithm
        profit = position['highest_price'] - manual_buy_price
        trailing_step = 10  # Fixed ₹10 steps
        
        if profit >= 30:  # Only after Buy+30
            profit_steps = int(profit // trailing_step)  # Number of complete 10-rupee steps
            step_stop_loss = manual_buy_price + (profit_steps * trailing_step)
            
            # Apply progressive minimum protection
            if position['progressive_minimum'] is None:
                position['progressive_minimum'] = manual_buy_price
            
            position['advanced_stop_loss'] = max(step_stop_loss, position['progressive_minimum'])
            
            print(f"📍 PHASE 3: Profit ₹{profit:.2f} → Steps {profit_steps} → SL = ₹{manual_buy_price} + ({profit_steps}×10) = ₹{step_stop_loss}")
            print(f"   Progressive Min ₹{position['progressive_minimum']} → Final SL ₹{position['advanced_stop_loss']}")
    
    # Update traditional stop_loss_price for display purposes
    position['stop_loss_price'] = position['advanced_stop_loss']
    
    # Debug print for monitoring
    print(f"🔍 MONITORING: Phase {position['algorithm_phase']} | Current: ₹{new_price} | Advanced SL: ₹{position['advanced_stop_loss']} | Progressive Min: ₹{position.get('progressive_minimum', 'N/A')}")
    
    # Check for stop loss trigger using advanced stop loss
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
            
            # NEW USER REQUIREMENT: Auto buy behavior depends on phase
            position['waiting_for_autobuy'] = True
            
            if position['algorithm_phase'] == 1:
                # Phase 1: Auto buy at SAME manual buy price (not sell price!)
                position['last_stop_loss_price'] = position['manual_buy_price']
                print(f"📍 PHASE 1 AUTO BUY: Will buy at manual buy price ₹{position['manual_buy_price']} (not sell price ₹{position['current_price']})")
            else:
                # Phase 2 & 3: Auto buy at sell price (same as before)
                position['last_stop_loss_price'] = position['current_price']
                print(f"📍 PHASE {position['algorithm_phase']} AUTO BUY: Will buy at sell price ₹{position['current_price']}")
            
            position['mode'] = f'Waiting for Auto Buy (Advanced Phase {position["algorithm_phase"]})'
            return True
        return False
    
    # Check for auto buy trigger
    auto_buy_trigger = position.get('last_stop_loss_price', 0)
    if (position.get('waiting_for_autobuy', False) and 
        position['current_price'] >= auto_buy_trigger):
        
        print(f"🎯 ADVANCED AUTO BUY TRIGGER (Phase {position['algorithm_phase']}) | Current: ₹{position['current_price']} | Trigger: ₹{auto_buy_trigger}")
        
        # Execute auto buy
        buy_executed = execute_auto_buy(position)
        if buy_executed:
            # After auto buy, reset parameters based on phase
            auto_buy_price = position['current_price']
            position['buy_price'] = auto_buy_price
            position['original_buy_price'] = auto_buy_price
            
            # Reset flags
            position['sell_triggered'] = False
            position['waiting_for_autobuy'] = False
            
            # Phase-specific reset logic
            if position['algorithm_phase'] == 1:
                # Phase 1: Reset to highest price for new cycle, keep manual buy price
                position['highest_price'] = auto_buy_price
                # Don't change manual_buy_price - it stays the same
                
            else:
                # Phase 2 & 3: Normal reset
                position['highest_price'] = auto_buy_price
                # Keep progressive minimum and manual buy price unchanged
            
            print(f"🎯 ADVANCED AUTO BUY COMPLETE (Phase {position['algorithm_phase']}): Buy ₹{auto_buy_price} | Manual Buy ₹{position['manual_buy_price']} | New SL ₹{position['advanced_stop_loss']}")
            return True
        return False
    
    return False

def test_new_3_phase_algorithm():
    """Test the NEW 3-Phase Advanced Algorithm"""
    print("=" * 80)
    print("🧪 TESTING NEW 3-PHASE ADVANCED ALGORITHM")
    print("=" * 80)
    
    # Create position
    position = MockPosition(
        strike='TEST',
        type='CE',
        buy_price=100,
        current_price=100,
        quantity=1
    )
    
    test_scenarios = [
        (100, "Manual Buy"),
        (110, "Phase 1: Price increase"),
        (90, "Phase 1: SL hit (should sell)"),
        (100, "Phase 1: Auto buy trigger"),
        (120, "Phase 2: Activate progressive min"),
        (110, "Phase 2: SL hit (should sell)"),
        (110, "Phase 2: Auto buy trigger"),
        (130, "Phase 3: Step algorithm"),
        (140, "Phase 3: More steps"),
        (130, "Phase 3: SL hit"),
    ]
    
    for price, description in test_scenarios:
        print(f"\n{'='*60}")
        print(f"📊 SCENARIO: {description} - Price ₹{price}")
        print('='*60)
        
        result = update_advanced_algorithm(position, price)
        
        if result:
            print(f"✅ ACTION TRIGGERED")
        else:
            print("⏳ NO ACTION - Monitoring...")
        
        # Print current state
        print(f"\n📋 STATE:")
        print(f"   Phase: {position.get('algorithm_phase', 'N/A')}")
        print(f"   Manual Buy: ₹{position.get('manual_buy_price', 'N/A')}")
        print(f"   Current Price: ₹{position['current_price']}")
        print(f"   Stop Loss: ₹{position.get('advanced_stop_loss', 'N/A')}")
        print(f"   Progressive Min: ₹{position.get('progressive_minimum', 'N/A')}")
        print(f"   Waiting Auto Buy: {position.get('waiting_for_autobuy', False)}")

if __name__ == "__main__":
    test_new_3_phase_algorithm()