#!/usr/bin/env python3
"""
Test Manual Stop Loss Override Issue
Tests why manual stop loss is getting reset and not showing in UI
"""

import sys
from datetime import datetime, timedelta
from app import update_trailing_stop_loss, get_ist_now

def test_manual_protection():
    """Test if manual stop loss protection works correctly"""
    print("🚀 Testing Manual Stop Loss Protection Logic")
    
    # Create a test position with manual stop loss
    position = {
        'strike': '55700',
        'type': 'CE',
        'buy_price': 542.0,
        'original_buy_price': 542.0,
        'current_price': 545.0,
        'highest_price': 545.0,
        'stop_loss_price': 532.0,  # Algorithm stop loss
        'manual_stop_loss_set': True,
        'manual_stop_loss_time': get_ist_now(),  # Just set now
        'minimum_stop_loss': 532.0,
        'auto_bought': False
    }
    
    print(f"📍 Initial Position:")
    print(f"   Buy Price: ₹{position['buy_price']}")
    print(f"   Current Price: ₹{position['current_price']}")
    print(f"   Stop Loss: ₹{position['stop_loss_price']}")
    print(f"   Manual SL Set: {position['manual_stop_loss_set']}")
    print(f"   Manual SL Time: {position['manual_stop_loss_time']}")
    
    # Test 1: Set manual stop loss to a higher value (profit target)
    print(f"\n==================================================")
    print(f"TEST 1: Manual Stop Loss Above Current Price")
    print(f"==================================================")
    
    position['stop_loss_price'] = 555.0  # Manual profit target
    position['manual_stop_loss_set'] = True
    position['manual_stop_loss_time'] = get_ist_now()
    
    print(f"🔧 Setting manual stop loss to ₹555.0...")
    print(f"   Before update_trailing_stop_loss:")
    print(f"   Stop Loss: ₹{position['stop_loss_price']}")
    print(f"   Manual SL Set: {position['manual_stop_loss_set']}")
    
    # Call the trailing stop loss function (this should respect manual setting)
    update_trailing_stop_loss(position, algorithm='simple')
    
    print(f"   After update_trailing_stop_loss:")
    print(f"   Stop Loss: ₹{position['stop_loss_price']}")
    print(f"   Manual SL Set: {position['manual_stop_loss_set']}")
    
    if position['stop_loss_price'] == 555.0:
        print(f"   ✅ Manual stop loss PRESERVED!")
    else:
        print(f"   ❌ Manual stop loss OVERRIDDEN! Expected ₹555.0, got ₹{position['stop_loss_price']}")
    
    # Test 2: Set manual stop loss to a lower value (stop loss)
    print(f"\n==================================================")
    print(f"TEST 2: Manual Stop Loss Below Current Price")
    print(f"==================================================")
    
    position['stop_loss_price'] = 530.0  # Manual stop loss
    position['manual_stop_loss_set'] = True
    position['manual_stop_loss_time'] = get_ist_now()
    
    print(f"🔧 Setting manual stop loss to ₹530.0...")
    print(f"   Before update_trailing_stop_loss:")
    print(f"   Stop Loss: ₹{position['stop_loss_price']}")
    print(f"   Manual SL Set: {position['manual_stop_loss_set']}")
    
    # Call the trailing stop loss function (this should respect manual setting)
    update_trailing_stop_loss(position, algorithm='simple')
    
    print(f"   After update_trailing_stop_loss:")
    print(f"   Stop Loss: ₹{position['stop_loss_price']}")
    print(f"   Manual SL Set: {position['manual_stop_loss_set']}")
    
    if position['stop_loss_price'] == 530.0:
        print(f"   ✅ Manual stop loss PRESERVED!")
    else:
        print(f"   ❌ Manual stop loss OVERRIDDEN! Expected ₹530.0, got ₹{position['stop_loss_price']}")
    
    # Test 3: Test expired manual stop loss (simulate 31 minutes later)
    print(f"\n==================================================")
    print(f"TEST 3: Expired Manual Stop Loss (31+ minutes)")
    print(f"==================================================")
    
    position['stop_loss_price'] = 540.0  # Manual stop loss
    position['manual_stop_loss_set'] = True
    # Set time 31 minutes ago
    position['manual_stop_loss_time'] = get_ist_now() - timedelta(minutes=31)
    
    print(f"🔧 Setting manual stop loss to ₹540.0 (31 minutes ago)...")
    print(f"   Before update_trailing_stop_loss:")
    print(f"   Stop Loss: ₹{position['stop_loss_price']}")
    print(f"   Manual SL Set: {position['manual_stop_loss_set']}")
    print(f"   Manual SL Time: {position['manual_stop_loss_time']} (31m ago)")
    
    # Call the trailing stop loss function (this should override expired manual setting)
    update_trailing_stop_loss(position, algorithm='simple')
    
    print(f"   After update_trailing_stop_loss:")
    print(f"   Stop Loss: ₹{position['stop_loss_price']}")
    print(f"   Manual SL Set: {position['manual_stop_loss_set']}")
    
    if not position['manual_stop_loss_set']:
        print(f"   ✅ Expired manual flag CLEARED!")
    else:
        print(f"   ❌ Expired manual flag NOT cleared!")
    
    print(f"\n🎉 Test completed!")

if __name__ == "__main__":
    test_manual_protection()