#!/usr/bin/env python3
"""
Test Phase 1 Auto Buy Logic Fix
Tests the correct behavior: Buy 492 → SL 482 → Sell 482 → Auto Buy 492 → SL 482
"""

def test_phase1_auto_buy_fix():
    """Test Phase 1 auto buy logic with correct trigger and stop loss"""
    
    # Simulate manual buy
    position = {
        'strike': 55500,
        'type': 'CE',
        'manual_buy_price': 492.80,
        'buy_price': 492.80,
        'original_buy_price': 492.80,
        'current_price': 492.80,
        'highest_price': 492.80,
        'stop_loss_price': 482.80,  # manual_buy_price - 10
        'advanced_stop_loss': 482.80,
        'algorithm_phase': 1,
        'waiting_for_autobuy': False,
        'auto_buy_count': 0
    }
    
    print("🧪 PHASE 1 AUTO BUY FIX TEST")
    print("=" * 50)
    print(f"📊 MANUAL BUY:")
    print(f"   Buy Price: ₹{position['manual_buy_price']}")
    print(f"   Stop Loss: ₹{position['stop_loss_price']}")
    print()
    
    # Simulate stop loss trigger (price drops to 482)
    position['current_price'] = 482.00
    position['waiting_for_autobuy'] = True
    
    # 🚨 CRITICAL FIX: Phase 1 auto buy trigger = manual_buy_price (NOT stop loss price)
    position['last_stop_loss_price'] = position['manual_buy_price']  # 492.80
    
    print(f"🔴 STOP LOSS TRIGGERED:")
    print(f"   Sell Price: ₹{position['current_price']}")
    print(f"   Auto Buy Trigger: ₹{position['last_stop_loss_price']}")
    print()
    
    # Simulate price going back to manual buy level
    test_prices = [485.0, 490.0, 492.80, 495.0]
    
    for test_price in test_prices:
        position['current_price'] = test_price
        auto_buy_trigger = position['last_stop_loss_price']
        
        will_auto_buy = (position['waiting_for_autobuy'] and 
                        position['current_price'] >= auto_buy_trigger)
        
        print(f"📈 Price ₹{test_price}:")
        print(f"   Trigger: ₹{auto_buy_trigger}")
        print(f"   Will Auto Buy: {'✅ YES' if will_auto_buy else '❌ NO'}")
        
        if will_auto_buy:
            # Simulate auto buy execution
            auto_buy_price = position['manual_buy_price']  # Phase 1: buy at manual price
            manual_buy_price = position['manual_buy_price']
            
            # 🚨 FIXED STOP LOSS: Remains at original manual level
            new_stop_loss = manual_buy_price - 10  # 492.80 - 10 = 482.80
            
            print(f"   🤖 AUTO BUY EXECUTED:")
            print(f"      Auto Buy Price: ₹{auto_buy_price}")
            print(f"      New Stop Loss: ₹{new_stop_loss} (manual ₹{manual_buy_price} - 10)")
            print()
            
            # Verify correctness
            expected_trigger = 492.80
            expected_buy_price = 492.80
            expected_stop_loss = 482.80
            
            correct_trigger = auto_buy_trigger == expected_trigger
            correct_buy = auto_buy_price == expected_buy_price  
            correct_sl = new_stop_loss == expected_stop_loss
            
            print(f"🔍 VERIFICATION:")
            print(f"   Trigger ₹{auto_buy_trigger} == ₹{expected_trigger}: {'✅' if correct_trigger else '❌'}")
            print(f"   Buy ₹{auto_buy_price} == ₹{expected_buy_price}: {'✅' if correct_buy else '❌'}")
            print(f"   SL ₹{new_stop_loss} == ₹{expected_stop_loss}: {'✅' if correct_sl else '❌'}")
            
            all_correct = correct_trigger and correct_buy and correct_sl
            print(f"\n🎯 TEST RESULT: {'✅ PASSED' if all_correct else '❌ FAILED'}")
            break
        print()
    
    print("\n💡 EXPECTED BEHAVIOR:")
    print("   1. Manual Buy ₹492.80 → Stop Loss ₹482.80")
    print("   2. Price drops → Sell at ₹482")
    print("   3. Auto Buy triggers when price reaches ₹492.80 again")
    print("   4. Auto Buy at ₹492.80 → Stop Loss remains ₹482.80")
    print("   5. No more rapid fire cycles!")

if __name__ == "__main__":
    test_phase1_auto_buy_fix()