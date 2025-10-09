#!/usr/bin/env python3
"""
Test script to debug manual stop loss issues
"""
import sys
import time
from datetime import datetime
import pytz

# Add the app directory to path
sys.path.append('.')

from app import app_state, get_ist_now, create_auto_position

def create_test_position():
    """Create a test position for debugging"""
    print("🔧 Creating test position...")
    
    # Create a test position
    position = create_auto_position(
        strike=55700,
        option_type='CE',
        buy_price=542.0,
        qty=75,
        symbol='NIFTY',
        expiry='25DEC2025'
    )
    
    # Set current price (simulate live price)
    position['current_price'] = 545.0
    position['last_price'] = 545.0
    position['highest_price'] = 565.0
    
    # Simulate it being in paper trading mode
    app_state['paper_trading_enabled'] = True
    app_state['paper_positions'] = [position]
    
    print(f"✅ Test position created:")
    print(f"   Strike: {position['strike']} {position['type']}")
    print(f"   Buy Price: ₹{position['buy_price']}")
    print(f"   Current Price: ₹{position['current_price']}")
    print(f"   Stop Loss: ₹{position['stop_loss_price']}")
    
    return position

def test_manual_stop_loss_update(position, new_sl):
    """Test manual stop loss update"""
    print(f"\n🔧 Testing manual stop loss update to ₹{new_sl}...")
    
    # Simulate manual stop loss update
    old_sl = position.get('stop_loss_price', 0)
    position['stop_loss_price'] = new_sl
    position['manual_stop_loss_set'] = True
    position['manual_stop_loss_time'] = get_ist_now()
    
    print(f"   Updated: ₹{old_sl} → ₹{new_sl}")
    print(f"   Manual flags set: manual_stop_loss_set=True")
    
    return position

def test_stop_loss_trigger(position, test_price):
    """Test stop loss trigger logic"""
    print(f"\n🔍 Testing stop loss trigger at price ₹{test_price}...")
    
    current_price = test_price
    stop_loss_price = position.get('stop_loss_price', 0)
    manual_sl_active = position.get('manual_stop_loss_set', False)
    buy_price = position.get('original_buy_price', position.get('buy_price', 0))
    
    print(f"   Current Price: ₹{current_price}")
    print(f"   Stop Loss: ₹{stop_loss_price}")
    print(f"   Buy Price: ₹{buy_price}")
    print(f"   Manual SL Active: {manual_sl_active}")
    
    # Test trigger conditions with FIXED logic
    trigger_condition = False
    if manual_sl_active:
        if stop_loss_price > buy_price:
            # Manual stop loss ABOVE buy price = PROFIT TARGET
            trigger_condition = current_price >= stop_loss_price
            print(f"   Manual PROFIT TARGET: {current_price} >= {stop_loss_price} = {trigger_condition}")
        else:
            # Manual stop loss BELOW buy price = STOP LOSS
            trigger_condition = current_price <= stop_loss_price
            print(f"   Manual STOP LOSS: {current_price} <= {stop_loss_price} = {trigger_condition}")
    else:
        # Algorithm stop loss: trigger when price goes below (strict)
        trigger_condition = current_price < stop_loss_price
        print(f"   Algorithm SL Trigger: {current_price} < {stop_loss_price} = {trigger_condition}")
    
    if (trigger_condition and
        stop_loss_price > 0 and 
        not position.get('waiting_for_autobuy', False) and
        not position.get('sell_triggered', False)):
        
        print("   🚨 STOP LOSS WOULD TRIGGER!")
        return True
    else:
        print("   ❌ Stop loss would NOT trigger")
        return False

def run_test():
    """Run the manual stop loss test"""
    print("🚀 Starting Manual Stop Loss Test\n")
    
    # Create test position
    position = create_test_position()
    
    # Test 1: Set manual stop loss above current price (profit target)
    print("\n" + "="*50)
    print("TEST 1: Manual Stop Loss Above Current Price")
    print("="*50)
    
    test_manual_stop_loss_update(position, 555.0)
    
    # Test trigger at various prices
    test_stop_loss_trigger(position, 545.0)  # Below SL - should not trigger
    test_stop_loss_trigger(position, 555.0)  # At SL - should trigger for manual
    test_stop_loss_trigger(position, 560.0)  # Above SL - should not trigger
    
    # Test 2: Set manual stop loss below current price (traditional stop loss)
    print("\n" + "="*50)
    print("TEST 2: Manual Stop Loss Below Current Price")
    print("="*50)
    
    # Reset position
    position['sell_triggered'] = False
    test_manual_stop_loss_update(position, 530.0)
    
    # Test trigger at various prices
    test_stop_loss_trigger(position, 545.0)  # Above SL - should not trigger
    test_stop_loss_trigger(position, 530.0)  # At SL - should trigger for manual
    test_stop_loss_trigger(position, 525.0)  # Below SL - should trigger
    
    # Test 3: Algorithm stop loss (no manual flag)
    print("\n" + "="*50)
    print("TEST 3: Algorithm Stop Loss (No Manual)")
    print("="*50)
    
    # Clear manual flags
    position['manual_stop_loss_set'] = False
    position['sell_triggered'] = False
    position['stop_loss_price'] = 540.0
    
    print(f"   Cleared manual flags, SL = ₹{position['stop_loss_price']}")
    
    # Test trigger at various prices
    test_stop_loss_trigger(position, 545.0)  # Above SL - should not trigger
    test_stop_loss_trigger(position, 540.0)  # At SL - should NOT trigger for algorithm
    test_stop_loss_trigger(position, 535.0)  # Below SL - should trigger
    
    print("\n🎉 Test completed!")

if __name__ == "__main__":
    run_test()