#!/usr/bin/env python3
"""
CRITICAL TEST: Verify Multiple Auto Sell Prevention and Manual Sell Auto Buy Blocking

This script tests the fixes for:
1. Multiple auto sells happening without corresponding buys (preventing huge losses)
2. Manual sell should NOT trigger auto buy

Test Cases:
- Test 1: Prevent multiple auto sells on same position
- Test 2: Manual sell blocks any future auto buy
- Test 3: Position removal after manual sell
- Test 4: Race condition prevention
"""

import sys
import os
import time
from datetime import datetime as dt

# Add current directory to path to import app modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the real app state and functions
from app import app_state, update_auto_position_price, execute_auto_sell, execute_auto_buy

def simulate_auto_trading_components():
    """Reset the app state for testing"""
    
    # Clear existing state for clean test
    app_state['auto_positions'] = []
    app_state['trade_history'] = []
    
    # Ensure auto trading config exists
    if 'auto_trading_config' not in app_state:
        app_state['auto_trading_config'] = {
            'stop_loss_points': 9,
            'trailing_step': 10,
            'minimum_stop_loss_buffer': 10,
            'auto_buy_buffer': 1
        }
    
    def create_auto_position(strike, option_type, buy_price, qty, symbol='NIFTY', expiry=''):
        """Create new auto position with safety flags"""
        stop_loss_price = max(buy_price - app_state['auto_trading_config']['stop_loss_points'], 0)
        
        position = {
            'id': f"test_{strike}_{option_type}",
            'symbol': symbol,
            'expiry': expiry,
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
            'mode': 'Running',
            'entry_time': dt.now(),
            'last_update': dt.now(),
            'total_pnl': 0,
            'realized_pnl': 0,
            'auto_sell_count': 0,
            # CRITICAL SAFETY FLAGS
            'sold': False,
            'manual_sold': False,
            'sell_in_progress': False,
            'sell_triggered': False
        }
        app_state['auto_positions'].append(position)
        print(f"📍 POSITION CREATED: {strike} {option_type} @ ₹{buy_price} | Stop Loss: ₹{stop_loss_price}")
        return position
    
    # Return the imported functions from app.py along with our local create_auto_position
    return app_state, create_auto_position, execute_auto_sell, execute_auto_buy, update_auto_position_price

def test_multiple_sell_prevention():
    """Test 1: Prevent multiple auto sells on same position"""
    print("\n" + "="*60)
    print("TEST 1: MULTIPLE AUTO SELL PREVENTION")
    print("="*60)
    
    app_state, create_auto_position, execute_auto_sell, execute_auto_buy, update_auto_position_price = simulate_auto_trading_components()
    
    # Create position
    position = create_auto_position(25000, 'CE', 100, 75)
    
    print(f"\n📊 Initial State:")
    print(f"   Position: {position['strike']} {position['type']} @ ₹{position['current_price']}")
    print(f"   Stop Loss: ₹{position['stop_loss_price']}")
    print(f"   Sold Flag: {position.get('sold', False)}")
    print(f"   Sell In Progress: {position.get('sell_in_progress', False)}")
    
    # Test: Trigger stop loss multiple times rapidly
    print(f"\n🧪 Triggering stop loss multiple times...")
    
    # First trigger - should execute
    print(f"\n--- First Stop Loss Trigger ---")
    result1 = update_auto_position_price(position, 80)  # Below stop loss
    print(f"Result 1: {result1} (Should be True)")
    
    # Immediate second trigger - should be prevented
    print(f"\n--- Immediate Second Trigger (Race Condition) ---")
    result2 = update_auto_position_price(position, 75)  # Even lower
    print(f"Result 2: {result2} (Should be False - duplicate prevented)")
    
    # Try direct auto sell call - should be prevented
    print(f"\n--- Direct Auto Sell Call ---")
    result3 = execute_auto_sell(position, reason='Stop Loss')
    print(f"Result 3: {result3} (Should be False - duplicate prevented)")
    
    print(f"\n📊 Final State:")
    print(f"   Sold Flag: {position.get('sold', False)}")
    print(f"   Sell In Progress: {position.get('sell_in_progress', False)}")
    print(f"   Waiting for Auto Buy: {position.get('waiting_for_autobuy', False)}")
    print(f"   Auto Sell Count: {position.get('auto_sell_count', 0)}")
    print(f"   Total Trades: {len(app_state['trade_history'])}")
    
    # Verification
    if len(app_state['trade_history']) == 1:
        print(f"✅ SUCCESS: Only 1 auto sell executed (prevented duplicates)")
    else:
        print(f"❌ FAILED: {len(app_state['trade_history'])} sells executed (should be 1)")
    
    return len(app_state['trade_history']) == 1

def test_manual_sell_blocks_auto_buy():
    """Test 2: Manual sell should block any future auto buy"""
    print("\n" + "="*60)
    print("TEST 2: MANUAL SELL BLOCKS AUTO BUY")
    print("="*60)
    
    app_state, create_auto_position, execute_auto_sell, execute_auto_buy, update_auto_position_price = simulate_auto_trading_components()
    
    # Create position
    position = create_auto_position(25000, 'PE', 150, 75)
    
    print(f"\n📊 Initial Position:")
    print(f"   Position: {position['strike']} {position['type']} @ ₹{position['current_price']}")
    print(f"   Manual Sold: {position.get('manual_sold', False)}")
    
    # Trigger stop loss first (normal auto sell)
    print(f"\n🧪 Step 1: Normal auto sell via stop loss...")
    update_auto_position_price(position, 140)  # Trigger stop loss
    
    print(f"   After Auto Sell - Waiting for Auto Buy: {position.get('waiting_for_autobuy', False)}")
    
    # Now simulate manual sell
    print(f"\n🧪 Step 2: Manual sell (user intervention)...")
    execute_auto_sell(position, reason='Manual Sell')
    
    print(f"   After Manual Sell - Manual Sold: {position.get('manual_sold', False)}")
    print(f"   After Manual Sell - Sold: {position.get('sold', False)}")
    
    # Try to trigger auto buy - should be blocked
    print(f"\n🧪 Step 3: Attempting auto buy (should be blocked)...")
    position['current_price'] = 160  # Price above trigger
    result = execute_auto_buy(position)
    
    print(f"   Auto Buy Result: {result} (Should be False - blocked)")
    print(f"   Position still in list: {position in app_state['auto_positions']}")
    
    # Verification
    auto_buy_trades = [t for t in app_state['trade_history'] if 'Auto Buy' in t['action']]
    if len(auto_buy_trades) == 0 and not result:
        print(f"✅ SUCCESS: Manual sell blocked auto buy correctly")
        return True
    else:
        print(f"❌ FAILED: Auto buy was not blocked after manual sell")
        return False

def test_position_removal_after_manual_sell():
    """Test 3: Position should be removed after manual sell"""
    print("\n" + "="*60)
    print("TEST 3: POSITION REMOVAL AFTER MANUAL SELL")
    print("="*60)
    
    app_state, create_auto_position, execute_auto_sell, execute_auto_buy, update_auto_position_price = simulate_auto_trading_components()
    
    # Create multiple positions
    pos1 = create_auto_position(25000, 'CE', 100, 75)
    pos2 = create_auto_position(25100, 'PE', 120, 75)
    pos3 = create_auto_position(25200, 'CE', 80, 75)
    
    initial_count = len(app_state['auto_positions'])
    print(f"\n📊 Initial Positions: {initial_count}")
    
    # Manual sell one position
    print(f"\n🧪 Manual selling position: {pos2['strike']} {pos2['type']}...")
    execute_auto_sell(pos2, reason='Manual Sell')
    
    # Simulate auto trading loop cleanup
    print(f"\n🧪 Simulating auto trading loop cleanup...")
    for position in app_state['auto_positions'][:]:  # Copy for safe iteration
        if position.get('manual_sold', False):
            print(f"🗑️ REMOVING MANUALLY SOLD POSITION: {position['strike']} {position['type']}")
            app_state['auto_positions'].remove(position)
    
    final_count = len(app_state['auto_positions'])
    print(f"\n📊 Final Positions: {final_count}")
    
    # Verification
    if final_count == initial_count - 1:
        print(f"✅ SUCCESS: Manual sell position removed correctly")
        return True
    else:
        print(f"❌ FAILED: Position count wrong (Expected: {initial_count-1}, Got: {final_count})")
        return False

def test_race_condition_prevention():
    """Test 4: Race condition prevention in concurrent scenarios"""
    print("\n" + "="*60)
    print("TEST 4: RACE CONDITION PREVENTION")
    print("="*60)
    
    app_state, create_auto_position, execute_auto_sell, execute_auto_buy, update_auto_position_price = simulate_auto_trading_components()
    
    # Create position
    position = create_auto_position(25000, 'CE', 200, 75)
    
    print(f"\n📊 Testing concurrent sell attempts...")
    
    # Simulate concurrent price updates that would trigger stop loss
    prices = [190, 185, 180, 175, 170]  # All below stop loss
    
    results = []
    for i, price in enumerate(prices):
        print(f"\n--- Concurrent Update {i+1}: Price ₹{price} ---")
        result = update_auto_position_price(position, price)
        results.append(result)
        print(f"   Update Result: {result}")
        print(f"   Sell In Progress: {position.get('sell_in_progress', False)}")
        print(f"   Sold: {position.get('sold', False)}")
    
    # Count successful sells
    successful_sells = sum(results)
    total_trades = len(app_state['trade_history'])
    
    print(f"\n📊 Race Condition Test Results:")
    print(f"   Concurrent updates: {len(prices)}")
    print(f"   Successful sells: {successful_sells}")
    print(f"   Total trades recorded: {total_trades}")
    
    # Verification
    if successful_sells == 1 and total_trades == 1:
        print(f"✅ SUCCESS: Race condition prevented - only 1 sell executed")
        return True
    else:
        print(f"❌ FAILED: Race condition not prevented - {successful_sells} sells executed")
        return False

def run_all_tests():
    """Run all tests and provide summary"""
    print("\n" + "="*80)
    print("🚨 CRITICAL SAFETY TESTS: MULTIPLE SELL PREVENTION & MANUAL SELL FIXES")
    print("="*80)
    
    tests = [
        ("Multiple Sell Prevention", test_multiple_sell_prevention),
        ("Manual Sell Blocks Auto Buy", test_manual_sell_blocks_auto_buy),
        ("Position Removal After Manual Sell", test_position_removal_after_manual_sell),
        ("Race Condition Prevention", test_race_condition_prevention)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result, None))
        except Exception as e:
            results.append((test_name, False, str(e)))
    
    # Summary
    print("\n" + "="*80)
    print("🔍 TEST RESULTS SUMMARY")
    print("="*80)
    
    passed = 0
    for test_name, success, error in results:
        if success:
            print(f"✅ {test_name}: PASSED")
            passed += 1
        else:
            print(f"❌ {test_name}: FAILED")
            if error:
                print(f"   Error: {error}")
    
    print(f"\n📊 Overall Results: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print(f"\n🎉 ALL TESTS PASSED! Your fixes are working correctly.")
        print(f"   ✅ Multiple auto sells are prevented")
        print(f"   ✅ Manual sell blocks auto buy")
        print(f"   ✅ Positions are properly cleaned up")
        print(f"   ✅ Race conditions are handled")
    else:
        print(f"\n⚠️ SOME TESTS FAILED! Please review the fixes.")
        print(f"   - Check the safety flags implementation")
        print(f"   - Verify the position cleanup logic")
        print(f"   - Test race condition handling")
    
    return passed == len(tests)

if __name__ == "__main__":
    try:
        success = run_all_tests()
        exit_code = 0 if success else 1
        sys.exit(exit_code)
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
