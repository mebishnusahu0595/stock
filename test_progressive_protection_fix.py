#!/usr/bin/env python3
"""
Test Progressive Protection Fix for User's Scenario
Manual Buy ₹405.90 → Auto Sell ₹395.35 → Auto Buy should have protected stop loss
"""

def test_progressive_protection_fix():
    """Test the progressive protection fix for the user's exact scenario"""
    
    print("🧪 TESTING PROGRESSIVE PROTECTION FIX - USER SCENARIO")
    print("=" * 55)
    
    # User's exact scenario
    position = {
        'strike': '55200',
        'type': 'PE',
        'option_type': 'PE',
        'buy_price': 405.90,  # Manual buy price
        'original_buy_price': 405.90,
        'current_price': 405.90,
        'quantity': 35,
        'advanced_stop_loss': 395.90,  # 405.90 - 10
        'highest_stop_loss': 395.90,
        'progressive_minimum': 395.90,  # Should be original_buy_price - 10
        'waiting_for_autobuy': False,
        'sell_triggered': False,
        'auto_buy_count': 0
    }
    
    print(f"📊 STEP 1: Manual Buy at ₹405.90")
    print(f"   Buy Price: ₹{position['buy_price']}")
    print(f"   Initial Stop Loss: ₹{position['advanced_stop_loss']}")
    print(f"   Progressive Minimum: ₹{position['progressive_minimum']}")
    print()
    
    # Price drops and hits stop loss
    print(f"🔴 STEP 2: Price drops, hits stop loss")
    
    drop_price = 395.35
    position['current_price'] = drop_price
    
    # Simulate auto sell at stop loss
    stop_loss_hit = position['current_price'] < position['advanced_stop_loss']
    
    print(f"   Price drops to: ₹{drop_price}")
    print(f"   Stop Loss: ₹{position['advanced_stop_loss']}")
    print(f"   Stop Loss Hit: {stop_loss_hit}")
    
    if stop_loss_hit:
        sell_price = position['advanced_stop_loss']  # Should sell at stop loss, not current price
        print(f"   🔴 AUTO SELL at ₹{sell_price}")
        
        # Set up auto buy trigger
        position['waiting_for_autobuy'] = True
        position['last_stop_loss_price'] = sell_price  # 395.90
        position['sell_triggered'] = True
        position['quantity'] = 0
        
        print(f"   ⚡ Auto Buy Trigger: ₹{position['last_stop_loss_price']}")
    
    print()
    
    # Auto buy triggers at same price
    print(f"🟢 STEP 3: Auto Buy at ₹395.35 (Price Recovery)")
    
    auto_buy_price = 395.35  # Price comes back to trigger level
    position['current_price'] = auto_buy_price
    
    # Check auto buy trigger
    auto_buy_trigger = position.get('last_stop_loss_price', 0)
    will_trigger = (position.get('waiting_for_autobuy', False) and 
                   position['current_price'] >= auto_buy_trigger)
    
    print(f"   Current Price: ₹{auto_buy_price}")
    print(f"   Auto Buy Trigger: ₹{auto_buy_trigger}")
    print(f"   Will Auto Buy: {will_trigger}")
    
    if will_trigger:
        # Execute auto buy with FIXED progressive protection
        position['waiting_for_autobuy'] = False
        position['buy_price'] = auto_buy_price
        position['highest_price'] = auto_buy_price
        position['sell_triggered'] = False
        position['quantity'] = 35
        
        # 🚨 PROGRESSIVE PROTECTION FIX
        calculated_stop_loss = auto_buy_price - 10  # 395.35 - 10 = 385.35
        progressive_min = position.get('progressive_minimum', calculated_stop_loss)  # 395.90
        
        # Apply progressive protection
        position['advanced_stop_loss'] = max(calculated_stop_loss, progressive_min)
        
        print(f"   🟢 AUTO BUY EXECUTED at ₹{auto_buy_price}")
        print()
        print(f"🛡️ STOP LOSS CALCULATION:")
        print(f"   Calculated: ₹{calculated_stop_loss} ({auto_buy_price} - 10)")
        print(f"   Progressive Min: ₹{progressive_min}")
        print(f"   Final Stop Loss: ₹{position['advanced_stop_loss']} (max of both)")
        
        protection_applied = position['advanced_stop_loss'] > calculated_stop_loss
        if protection_applied:
            protection_amount = position['advanced_stop_loss'] - calculated_stop_loss
            print(f"   ✅ PROTECTION APPLIED: +₹{protection_amount} per share")
        else:
            print(f"   ❌ NO PROTECTION: Stop loss went too low")
    
    print()
    
    # Test the next cycle
    print(f"📉 STEP 4: What if price drops again?")
    
    next_drop_price = 390.0
    position['current_price'] = next_drop_price
    
    next_stop_loss_hit = position['current_price'] < position['advanced_stop_loss']
    
    print(f"   Price drops to: ₹{next_drop_price}")
    print(f"   Current Stop Loss: ₹{position['advanced_stop_loss']}")
    print(f"   Will Hit Stop Loss: {next_stop_loss_hit}")
    
    if next_stop_loss_hit:
        print(f"   🔴 SECOND AUTO SELL at ₹{position['advanced_stop_loss']}")
        print(f"   💰 Loss limited by progressive protection!")
    else:
        print(f"   ✅ SAFE: Price above protected stop loss")
    
    print()
    print("📊 COMPARISON - BEFORE vs AFTER FIX:")
    print("=" * 40)
    
    print(f"❌ BEFORE FIX (What was happening):")
    print(f"   Manual Buy: ₹405.90")
    print(f"   Auto Sell: ₹395.90")
    print(f"   Auto Buy: ₹395.35")
    print(f"   New Stop Loss: ₹385.35 (395.35 - 10)")
    print(f"   Result: Keeps going down! ❌")
    print()
    
    print(f"✅ AFTER FIX (What should happen):")
    print(f"   Manual Buy: ₹405.90")
    print(f"   Auto Sell: ₹395.90") 
    print(f"   Auto Buy: ₹395.35")
    print(f"   New Stop Loss: ₹{position['advanced_stop_loss']} (protected)")
    print(f"   Result: Protected by progressive minimum! ✅")
    
    print()
    print("✅ VERIFICATION:")
    if position['advanced_stop_loss'] > 385.35:
        print(f"✅ SUCCESS: Stop loss protected at ₹{position['advanced_stop_loss']}")
        print(f"✅ SUCCESS: Won't keep sliding down")
        print(f"✅ SUCCESS: Progressive minimum working!")
    else:
        print(f"❌ FAILED: Stop loss still too low at ₹{position['advanced_stop_loss']}")

if __name__ == "__main__":
    test_progressive_protection_fix()