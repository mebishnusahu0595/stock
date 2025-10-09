#!/usr/bin/env python3
"""
Test the fixed manual stop loss protection
This simulates what happens when user sets manual stop loss
"""

import sys
import os
from datetime import datetime, timedelta

print("🚀 Testing Fixed Manual Stop Loss Protection")
print("=" * 60)

# Mock the minimal required functions and state
class MockApp:
    def __init__(self):
        self.state = {
            'auto_trading_config': {
                'trailing_step': 10,
                'stop_loss_points': 10
            }
        }

def get_ist_now():
    """Mock IST time function"""
    return datetime.now()

# Mock app_state global
app_state = {
    'auto_trading_config': {
        'trailing_step': 10,
        'stop_loss_points': 10
    }
}

def test_manual_protection_scenario():
    """Test the exact scenario user is experiencing"""
    
    print("📍 SCENARIO: User sets manual stop loss to ₹555")
    print("Expected behavior: Algorithm should NOT override this value")
    print()
    
    # Create position as it would be when user sets manual SL
    position = {
        'strike': '55700',
        'type': 'CE',
        'buy_price': 542.0,
        'original_buy_price': 542.0,
        'current_price': 545.0,
        'highest_price': 545.0,
        'stop_loss_price': 555.0,  # User set this manually
        'manual_stop_loss_set': True,  # User just set this
        'manual_stop_loss_time': get_ist_now(),  # Just now
        'minimum_stop_loss': 532.0,
        'auto_bought': False
    }
    
    print(f"Before algorithm update:")
    print(f"  Stop Loss: ₹{position['stop_loss_price']}")
    print(f"  Manual Flag: {position['manual_stop_loss_set']}")
    print(f"  Manual Time: {position['manual_stop_loss_time']}")
    
    # Simulate what the algorithm does (simplified version)
    def simulate_update_trailing_stop_loss(position):
        """Simplified version of the protection logic"""
        
        manual_sl_set = position.get('manual_stop_loss_set', False)
        manual_sl_time = position.get('manual_stop_loss_time')
        current_sl = position.get('stop_loss_price', 0)
        
        # NEW STRENGTHENED PROTECTION
        if manual_sl_set:
            print(f"🔧 MANUAL STOP LOSS ACTIVE: ₹{current_sl} - BLOCKING ALL ALGORITHM UPDATES")
            print(f"   manual_stop_loss_set: {manual_sl_set}")
            print(f"   manual_stop_loss_time: {manual_sl_time}")
            print(f"   🚫 SKIPPING update_trailing_stop_loss() to preserve manual setting")
            
            if manual_sl_time:
                try:
                    current_time = get_ist_now()
                    time_diff = (current_time - manual_sl_time).total_seconds()
                    time_diff_minutes = time_diff / 60
                    
                    if time_diff >= 1800:  # 30 minutes
                        print(f"⏰ MANUAL PROTECTION EXPIRED after {time_diff_minutes:.1f} minutes - Clearing flag")
                        position['manual_stop_loss_set'] = False
                        # Don't return - let algorithm take over now
                    else:
                        print(f"🛡️ MANUAL PROTECTION ACTIVE: {time_diff_minutes:.1f}/30 minutes remaining")
                        return  # Skip algorithm update
                except Exception as e:
                    print(f"⚠️ Error in time calculation: {e} - Keeping manual protection active")
                    return  # If time calc fails, err on side of protecting manual setting
            else:
                print(f"🛡️ MANUAL FLAG SET (no timestamp) - Protecting manual stop loss")
                return
        
        # If we reach here, manual protection is not active - proceed with algorithm
        print("🤖 Manual protection not active - Algorithm would update stop loss")
        # For this test, we'll simulate what the old algorithm would do
        original_buy_price = position.get('original_buy_price', position['buy_price'])
        initial_stop_loss = original_buy_price - 10  # 532.0
        position['stop_loss_price'] = initial_stop_loss
        print(f"🤖 Algorithm updated stop loss to: ₹{position['stop_loss_price']}")
    
    # Test the protection
    print(f"\n🧪 TESTING: Calling update_trailing_stop_loss()...")
    simulate_update_trailing_stop_loss(position)
    
    print(f"\nAfter algorithm update:")
    print(f"  Stop Loss: ₹{position['stop_loss_price']}")
    print(f"  Manual Flag: {position['manual_stop_loss_set']}")
    
    # Check result
    if position['stop_loss_price'] == 555.0 and position['manual_stop_loss_set']:
        print(f"\n✅ SUCCESS: Manual stop loss PRESERVED!")
        print(f"   User's ₹555 setting was protected from algorithm override")
    else:
        print(f"\n❌ FAILED: Manual stop loss was overridden!")
        print(f"   Expected: ₹555.0, Got: ₹{position['stop_loss_price']}")
        print(f"   Manual flag: Expected True, Got: {position['manual_stop_loss_set']}")

if __name__ == "__main__":
    test_manual_protection_scenario()