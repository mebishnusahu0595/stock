#!/usr/bin/env python3
"""
Simple test to check the manual stop loss override issue
"""

import sys
import os

# Add the current directory to Python path to import functions
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_manual_sl_behavior():
    """Test what happens when manual SL is set and algorithm runs"""
    print("🔍 INVESTIGATING MANUAL STOP LOSS OVERRIDE ISSUE")
    print("=" * 60)
    
    print("The issue is that when user sets manual stop loss:")
    print("1. ✅ API call succeeds and sets stop_loss_price")
    print("2. ✅ Sets manual_stop_loss_set = True")
    print("3. ✅ Sets manual_stop_loss_time = now")
    print("4. ❌ But the UI doesn't show the updated value")
    print("5. ❌ And it gets reset back to algorithm value")
    
    print("\nPossible causes:")
    print("🔍 A) update_trailing_stop_loss() is called immediately after")
    print("🔍 B) Position data is not being sent to frontend correctly")
    print("🔍 C) Frontend is not updating the DOM with new stop loss")
    print("🔍 D) Time check in protection logic has timezone issues")
    
    print("\nLet's check where update_trailing_stop_loss is called...")
    print("📍 In update_simple_algorithm() line 397:")
    print("   update_trailing_stop_loss(position, algorithm='simple')")
    print("📍 This is called EVERY time price updates (every 500ms!)")
    
    print("\nThe protection logic in update_trailing_stop_loss:")
    print("💡 IF manual_stop_loss_set = True AND time < 30 minutes:")
    print("   → SKIP algorithm update (return early)")
    print("💡 ELSE:")
    print("   → Override with algorithm stop loss")
    
    print("\n🚨 SUSPECTED ISSUE:")
    print("The protection logic might not be working because:")
    print("1. Time difference calculation is wrong")
    print("2. get_ist_now() returns different timezone than expected")
    print("3. The manual flags are being cleared somewhere else")
    print("4. The position object reference is not the same")
    
    print("\n🔧 SOLUTION NEEDED:")
    print("We need to debug WHY the protection isn't working")
    print("Let's add more debugging to the update_trailing_stop_loss function")

if __name__ == "__main__":
    test_manual_sl_behavior()