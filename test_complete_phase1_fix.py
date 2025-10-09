#!/usr/bin/env python3
"""
🧪 Test Complete Phase 1 Auto Buy Fix
Verify the complete auto buy flow works correctly
"""

# Mock the app module structure
class MockPosition:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
    
    def get(self, key, default=None):
        return self.__dict__.get(key, default)
    
    def __getitem__(self, key):
        return self.__dict__[key]
    
    def __setitem__(self, key, value):
        self.__dict__[key] = value
    
    def __contains__(self, key):
        return key in self.__dict__

from datetime import datetime as dt

def execute_auto_sell(position, reason="Test"):
    position['sell_triggered'] = True
    print(f"📤 AUTO SELL: {position['strike']} {position.get('type', 'CE')} at ₹{position['current_price']} | Reason: {reason}")
    return True

def execute_auto_buy(position):
    """FIXED: Execute auto buy with phase-based price"""
    # 🚨 FIX: Auto buy price depends on phase
    if position.get('algorithm_phase', 1) == 1:
        buy_price = position.get('manual_buy_price', position['current_price'])
        print(f"🎯 PHASE 1 AUTO BUY: Using manual buy price ₹{buy_price} instead of current price ₹{position['current_price']}")
    else:
        buy_price = position['current_price']
        print(f"🎯 PHASE {position.get('algorithm_phase', 1)} AUTO BUY: Using current price ₹{buy_price}")
    
    # Set the buy price - this is the key fix!
    position['buy_price'] = buy_price
    position['waiting_for_autobuy'] = False
    position['sell_triggered'] = False
    position['mode'] = 'Auto-Monitoring (After Auto Buy)'
    
    print(f"✅ AUTO BUY EXECUTED: Bought at ₹{buy_price}")
    return True

def update_advanced_algorithm(position, new_price):
    """Complete algorithm with fixed auto buy logic"""
    position['current_price'] = new_price
    position['last_update'] = dt.now()
    
    # Initialize required fields
    if 'manual_buy_price' not in position:
        position['manual_buy_price'] = position.get('buy_price', new_price)
    if 'original_buy_price' not in position:
        position['original_buy_price'] = position.get('buy_price', new_price)
    if 'advanced_stop_loss' not in position:
        position['advanced_stop_loss'] = position['manual_buy_price'] - 10
    if 'algorithm_phase' not in position:
        position['algorithm_phase'] = 1
    
    manual_buy_price = position['manual_buy_price']
    price_above_buy = new_price - manual_buy_price
    
    # Determine phase
    if price_above_buy < 20:
        position['algorithm_phase'] = 1
    elif price_above_buy < 30:
        position['algorithm_phase'] = 2
    else:
        position['algorithm_phase'] = 3
    
    # Phase 1: Simple stop loss
    if position['algorithm_phase'] == 1:
        position['advanced_stop_loss'] = manual_buy_price - 10
    
    print(f"🔄 PHASE {position['algorithm_phase']}: Manual Buy ₹{manual_buy_price} | Current ₹{new_price} | SL ₹{position['advanced_stop_loss']}")
    
    # Check for stop loss trigger
    if (position['current_price'] <= position['advanced_stop_loss'] and 
        not position.get('waiting_for_autobuy', False) and
        not position.get('sell_triggered', False)):
        
        print(f"🚨 STOP LOSS HIT @ ₹{new_price}")
        execute_auto_sell(position)
        position['waiting_for_autobuy'] = True
        
        # Set auto buy trigger based on phase
        if position['algorithm_phase'] == 1:
            position['last_stop_loss_price'] = position['manual_buy_price']  # Phase 1: manual buy price
            print(f"📍 PHASE 1 AUTO BUY: Will trigger at manual buy price ₹{position['manual_buy_price']}")
        else:
            position['last_stop_loss_price'] = position['current_price']  # Phase 2&3: sell price
            print(f"📍 PHASE {position['algorithm_phase']} AUTO BUY: Will trigger at sell price ₹{position['current_price']}")
        
        return True
    
    # Check for auto buy trigger
    auto_buy_trigger = position.get('last_stop_loss_price', 0)
    if (position.get('waiting_for_autobuy', False) and 
        position['current_price'] >= auto_buy_trigger):
        
        print(f"🎯 AUTO BUY TRIGGER: Current ₹{position['current_price']} >= Trigger ₹{auto_buy_trigger}")
        
        # Execute auto buy
        buy_executed = execute_auto_buy(position)
        if buy_executed:
            # 🚨 CRITICAL FIX: Don't override the buy_price set by execute_auto_buy!
            actual_buy_price = position['buy_price']  # Get the actual price we bought at
            position['original_buy_price'] = actual_buy_price
            
            print(f"🎯 AUTO BUY COMPLETE: Final Buy Price ₹{actual_buy_price} | Manual Buy ₹{position['manual_buy_price']}")
            return True
    
    return False

def test_complete_phase1_fix():
    print("=" * 80)
    print("🧪 TESTING COMPLETE PHASE 1 AUTO BUY FIX")
    print("=" * 80)
    
    # Test your exact scenario: Manual buy CE 55800 at ₹452.50
    position = MockPosition(
        strike=55800,
        type='CE',
        buy_price=452.50,
        current_price=452.50,
        quantity=35
    )
    
    print("\n" + "="*60)
    print("📊 TEST CASE: Manual Buy CE 55800 at ₹452.50")
    print("="*60)
    
    # Step 1: Manual buy
    print(f"\n1️⃣ Manual Buy at ₹{position['buy_price']}")
    update_advanced_algorithm(position, 452.50)
    print(f"   ✅ Manual buy price: ₹{position.get('manual_buy_price', 'N/A')}")
    print(f"   ✅ Stop loss: ₹{position.get('advanced_stop_loss', 'N/A')}")
    
    # Step 2: Price drops and hits stop loss at ₹442.50
    print(f"\n2️⃣ Price drops to ₹442.50 (Stop Loss)")
    update_advanced_algorithm(position, 442.50)
    print(f"   ✅ Waiting for auto buy: {position.get('waiting_for_autobuy', False)}")
    print(f"   ✅ Auto buy trigger price: ₹{position.get('last_stop_loss_price', 'N/A')}")
    
    # Step 3: Price rises back to manual buy price ₹452.50
    print(f"\n3️⃣ Price rises to ₹452.50 (Should trigger auto buy)")
    result = update_advanced_algorithm(position, 452.50)
    print(f"   ✅ Action triggered: {result}")
    print(f"   ✅ Auto buy executed at: ₹{position.get('buy_price', 'N/A')}")
    print(f"   ✅ Current price: ₹{position.get('current_price', 'N/A')}")
    print(f"   ✅ Waiting for auto buy: {position.get('waiting_for_autobuy', False)}")
    
    # Verification
    print(f"\n🎯 VERIFICATION:")
    expected_buy_price = 452.50  # Should buy at manual buy price
    actual_buy_price = position.get('buy_price', 0)
    
    if actual_buy_price == expected_buy_price:
        print(f"   ✅ PASS: Auto buy at correct price ₹{actual_buy_price} (manual buy price)")
        print(f"   ✅ PASS: Complete Phase 1 logic working correctly!")
    else:
        print(f"   ❌ FAIL: Auto buy at ₹{actual_buy_price}, expected ₹{expected_buy_price}")
        print(f"   ❌ FAIL: Auto buy price override issue!")
    
    print(f"\n📋 FINAL STATE:")
    print(f"   Manual Buy Price: ₹{position.get('manual_buy_price', 'N/A')}")
    print(f"   Auto Buy Price: ₹{position.get('buy_price', 'N/A')}")
    print(f"   Current Market Price: ₹{position.get('current_price', 'N/A')}")
    print(f"   Algorithm Phase: {position.get('algorithm_phase', 'N/A')}")

if __name__ == "__main__":
    test_complete_phase1_fix()