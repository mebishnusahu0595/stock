#!/usr/bin/env python3
"""
🧪 Test Phase 1 Trailing Stop Loss Fix
Test your exact scenario: Buy ₹458, Price ₹498, Stop Loss should trail up
"""

from datetime import datetime as dt

# Mock the app_state
app_state = {
    'trading_algorithm': 'advanced',
}

def update_advanced_algorithm(position, new_price):
    """Simplified advanced algorithm to test Phase 1 trailing"""
    position['current_price'] = new_price
    position['last_update'] = dt.now()
    
    # Initialize required fields
    if 'manual_buy_price' not in position:
        position['manual_buy_price'] = position.get('buy_price', new_price)
    if 'original_buy_price' not in position:
        position['original_buy_price'] = position.get('buy_price', new_price)
    if 'highest_price' not in position:
        position['highest_price'] = position['original_buy_price']
    if 'advanced_stop_loss' not in position:
        position['advanced_stop_loss'] = position['manual_buy_price'] - 10
    if 'algorithm_phase' not in position:
        position['algorithm_phase'] = 1
    if 'progressive_minimum' not in position:
        position['progressive_minimum'] = None
    
    manual_buy_price = position['manual_buy_price']
    price_above_buy = new_price - manual_buy_price
    
    # Determine phase
    if price_above_buy < 20:
        position['algorithm_phase'] = 1
    elif price_above_buy < 30:
        position['algorithm_phase'] = 2
    else:
        position['algorithm_phase'] = 3
    
    print(f"🔄 PHASE {position['algorithm_phase']}: Manual Buy ₹{manual_buy_price} | Current ₹{new_price} | Above Buy: +₹{price_above_buy:.2f}")
    
    # PHASE 1: Fixed trailing logic
    if position['algorithm_phase'] == 1:
        # Update highest price for trailing in Phase 1
        if new_price > position['highest_price']:
            position['highest_price'] = new_price
        
        # Phase 1 trailing logic
        profit = position['highest_price'] - manual_buy_price
        trailing_step = 10
        
        if profit >= 10:  # If profit >= 10, start trailing
            profit_steps = int(profit // trailing_step)
            trailing_stop_loss = manual_buy_price + (profit_steps * trailing_step)
            
            # Minimum protection: never go below manual_buy_price - 10
            minimum_sl = manual_buy_price - 10
            position['advanced_stop_loss'] = max(trailing_stop_loss, minimum_sl)
            
            print(f"📍 PHASE 1 TRAILING: Buy ₹{manual_buy_price} | High ₹{position['highest_price']} | Profit ₹{profit:.2f} | Steps {profit_steps}")
            print(f"   SL = ₹{manual_buy_price} + ({profit_steps}×10) = ₹{trailing_stop_loss} | Final SL ₹{position['advanced_stop_loss']}")
        else:
            position['advanced_stop_loss'] = manual_buy_price - 10
            print(f"📍 PHASE 1: Simple SL = ₹{manual_buy_price} - 10 = ₹{position['advanced_stop_loss']}")
        
        position['progressive_minimum'] = None
    
    # Update display stop loss
    position['stop_loss_price'] = position['advanced_stop_loss']
    
    return False

def test_phase1_trailing_fix():
    print("=" * 80)
    print("🧪 TESTING PHASE 1 TRAILING STOP LOSS FIX")
    print("=" * 80)
    
    # Your exact scenario: CE 55800 buy at ₹458, price reaches ₹498
    position = {
        'strike': 55800,
        'type': 'CE',
        'buy_price': 458.00,
        'current_price': 458.00,
        'quantity': 35
    }
    
    print("\n" + "="*60)
    print("📊 TEST CASE: Manual Buy CE 55800 at ₹458")
    print("="*60)
    
    # Test sequence
    test_prices = [458.00, 468.00, 478.00, 488.00, 498.00, 495.00]
    
    for i, price in enumerate(test_prices):
        print(f"\n🔄 Step {i+1}: Price = ₹{price}")
        update_advanced_algorithm(position, price)
        
        print(f"   Current Price: ₹{position['current_price']}")
        print(f"   Highest Price: ₹{position['highest_price']}")
        print(f"   Stop Loss: ₹{position.get('advanced_stop_loss', 'N/A')}")
        print(f"   Phase: {position.get('algorithm_phase', 'N/A')}")
    
    # Verification for your specific case
    print(f"\n🎯 VERIFICATION:")
    print(f"   Manual Buy: ₹458.00")
    print(f"   Current Price: ₹{position['current_price']}")
    print(f"   Highest Price: ₹{position['highest_price']}")
    print(f"   Stop Loss: ₹{position.get('advanced_stop_loss', 'N/A')}")
    
    expected_profit = 498.00 - 458.00  # ₹40 profit
    expected_steps = int(expected_profit // 10)  # 4 steps
    expected_sl = 458.00 + (expected_steps * 10)  # ₹458 + ₹40 = ₹498
    
    actual_sl = position.get('advanced_stop_loss', 0)
    
    if abs(actual_sl - expected_sl) < 1:  # Allow 1 rupee tolerance
        print(f"   ✅ PASS: Stop loss ₹{actual_sl} matches expected ₹{expected_sl}")
        print(f"   ✅ PASS: Phase 1 trailing working correctly!")
    else:
        print(f"   ❌ FAIL: Stop loss ₹{actual_sl}, expected ₹{expected_sl}")
        print(f"   ❌ FAIL: Phase 1 trailing not working")

if __name__ == "__main__":
    test_phase1_trailing_fix()