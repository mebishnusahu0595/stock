#!/usr/bin/env python3
"""
🧪 TEST: Corrected Progressive Minimum Logic
===========================================

USER REQUIREMENT:
- Manual Buy price se ₹10 niche kabhi nahi jaana chahiye
- Progressive minimum sirf profit ke baad apply ho
- Normal trading mein manual buy - 10 minimum rahe

CORRECT EXAMPLE:
Manual Buy ₹424.15 → SL ₹414.15, Manual Min ₹414.15
Price ₹434.10 → SL ₹424.10, Progressive Min ₹404.10, but Manual Min ₹414.15
Final SL = max(424.10, max(404.10, 414.15)) = max(424.10, 414.15) = ₹424.10 ✅
Auto Buy ₹434.10 → SL ₹424.10, Manual Min ₹414.15 (never changes)
Final SL = max(424.10, 414.15) = ₹424.10 ✅
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
    """CORRECTED Advanced algorithm with proper manual minimum protection"""
    print(f"\n[DEBUG] ADVANCED ALGORITHM CALLED | Price: {new_price}")
    old_price = float(position['current_price'])
    position['current_price'] = new_price
    position['last_update'] = dt.now()
    
    # Initialize required fields for advanced algorithm
    if 'original_buy_price' not in position:
        position['original_buy_price'] = position.get('buy_price', position.get('average_price', new_price))
    if 'manual_buy_price' not in position:
        position['manual_buy_price'] = position.get('buy_price', position.get('average_price', new_price))  # Never changes - first manual buy
    if 'highest_price' not in position:
        position['highest_price'] = position['original_buy_price']
    if 'advanced_stop_loss' not in position:
        position['advanced_stop_loss'] = position['original_buy_price'] - 10  # Initial stop loss (buy_price - 10)
    if 'minimum_stop_loss' not in position:
        position['minimum_stop_loss'] = position['manual_buy_price'] - 10  # Absolute minimum based on manual buy
    if 'highest_stop_loss' not in position:
        position['highest_stop_loss'] = position['original_buy_price'] - 10  # Track highest stop loss ever reached
    if 'progressive_minimum' not in position:
        position['progressive_minimum'] = position['manual_buy_price'] - 10  # Start with manual buy - 10
    
    original_buy_price = position['original_buy_price']
    
    # Update highest price and trailing logic
    if new_price > position['highest_price']:
        position['highest_price'] = new_price
        
        # NEW LOGIC: Fixed ₹10 step trailing
        new_stop_loss = position['highest_price'] - 10
        
        # Update highest stop loss if this is higher
        old_highest_sl = position.get('highest_stop_loss', 0)
        if new_stop_loss > position['highest_stop_loss']:
            position['highest_stop_loss'] = new_stop_loss
            # USER REQUIREMENT FIXED: Progressive minimum = max(manual_buy-10, highest_SL-20)
            progressive_from_highest = position['highest_stop_loss'] - 20
            manual_minimum = position['manual_buy_price'] - 10
            position['progressive_minimum'] = max(manual_minimum, progressive_from_highest)
            print(f"📈 NEW HIGHEST SL: ₹{old_highest_sl} → ₹{new_stop_loss}")
            print(f"   Manual Min: ₹{manual_minimum} | Progressive: ₹{progressive_from_highest} | Final Min: ₹{position['progressive_minimum']}")
        
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
    print(f"🔍 MONITORING: Current: ₹{new_price} | Advanced SL: ₹{position['advanced_stop_loss']} | Manual Min: ₹{position.get('manual_buy_price', 0) - 10} | Progressive Min: ₹{position.get('progressive_minimum', 'N/A')}")
    
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
            
            # USER REQUIREMENT: Auto buy at SAME price where it was sold
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
            # CRITICAL FIX: After auto buy, update references correctly
            auto_buy_price = position['current_price']
            position['buy_price'] = auto_buy_price  # Update buy price to auto buy price
            position['original_buy_price'] = auto_buy_price  # Update original buy price for new cycle
            position['highest_price'] = auto_buy_price  # Reset highest price for new cycle
            # IMPORTANT: Keep manual_buy_price unchanged - it's the absolute reference
            
            # Reset flags
            position['sell_triggered'] = False
            position['waiting_for_autobuy'] = False
            
            # PROGRESSIVE PROTECTION: Calculate stop loss with protection
            calculated_stop_loss = auto_buy_price - 10  # Normal: auto buy price - 10
            progressive_min = position.get('progressive_minimum', calculated_stop_loss)
            manual_minimum = position['manual_buy_price'] - 10  # Never go below manual buy - 10
            
            # Apply both progressive minimum and manual minimum protection
            final_minimum = max(progressive_min, manual_minimum)
            position['advanced_stop_loss'] = max(calculated_stop_loss, final_minimum)
            
            print(f"🛡️ AUTO BUY STOP LOSS CALCULATION:")
            print(f"   Auto Buy Price: ₹{auto_buy_price}")
            print(f"   Calculated Stop Loss: ₹{calculated_stop_loss} ({auto_buy_price} - 10)")
            print(f"   Progressive Minimum: ₹{progressive_min}")
            print(f"   Manual Minimum: ₹{manual_minimum} (₹{position['manual_buy_price']} - 10)")
            print(f"   Final Minimum: ₹{final_minimum} (max of progressive and manual)")
            print(f"   Final Stop Loss: ₹{position['advanced_stop_loss']} (max of calculated and final minimum)")
            
            return True
        return False
    
    return False

def test_corrected_progressive_minimum():
    """Test the corrected progressive minimum logic"""
    print("=" * 80)
    print("🧪 TESTING CORRECTED PROGRESSIVE MINIMUM LOGIC")
    print("=" * 80)
    
    # Create position
    position = MockPosition(
        strike='55600',
        type='PE',
        buy_price=424.15,
        current_price=424.15,
        quantity=105
    )
    
    print(f"\n🚀 STEP 1: Manual Buy PE 55600 at ₹424.15")
    print(f"Expected: SL ₹414.15, Manual Min ₹414.15")
    update_advanced_algorithm(position, 424.15)
    
    print(f"\n🚀 STEP 2: Price rises to ₹434.10 (should trail SL)")
    print(f"Expected: SL ₹424.10, Progressive Min from highest = ₹404.10, but Manual Min = ₹414.15")
    print(f"Final Min = max(404.10, 414.15) = ₹414.15")
    print(f"Final SL = max(424.10, 414.15) = ₹424.10")
    update_advanced_algorithm(position, 434.10)
    
    print(f"\n🚀 STEP 3: Price hits ₹434.10 (should sell - profit booking)")
    result = update_advanced_algorithm(position, 434.10)
    
    if not result:
        # Manually trigger sell for testing (price at SL)
        print(f"\n🚀 STEP 3B: Price drops to ₹424.10 (should sell)")
        result = update_advanced_algorithm(position, 424.10)
    
    if result:
        print(f"\n🚀 STEP 4: Auto buy trigger at same price")
        result = update_advanced_algorithm(position, position['current_price'])
        
        if result:
            print(f"\n🚀 STEP 5: After auto buy - checking minimum protection")
            print(f"Manual Buy Price: ₹{position['manual_buy_price']} (never changes)")
            print(f"Current SL: ₹{position['advanced_stop_loss']}")
            print(f"Should never go below: ₹{position['manual_buy_price'] - 10}")
            
            if position['advanced_stop_loss'] >= position['manual_buy_price'] - 10:
                print("✅ CORRECT: Stop loss is above manual minimum")
            else:
                print(f"❌ ERROR: Stop loss ₹{position['advanced_stop_loss']} is below manual minimum ₹{position['manual_buy_price'] - 10}")

if __name__ == "__main__":
    test_corrected_progressive_minimum()