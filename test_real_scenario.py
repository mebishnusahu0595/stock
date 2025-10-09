#!/usr/bin/env python3
"""
Simple Auto Buy Test - Check if auto buy works in your exact scenario
"""

def test_real_scenario():
    """Test the exact scenario from user's trade history"""
    
    print("🧪 TESTING REAL SCENARIO - CE 54800")
    print("=" * 40)
    
    # Recreate position based on user's trade history
    position = {
        'strike': '54800',
        'type': 'CE',
        'option_type': 'CE',
        'buy_price': 677.75,  # From trade history: Manual Buy - CE 54800, Price: ₹677.75
        'original_buy_price': 677.75,
        'current_price': 677.75,
        'quantity': 35,
        'advanced_stop_loss': 667.75,  # 677.75 - 10
        'highest_stop_loss': 667.75,
        'progressive_minimum': 667.75,
        'waiting_for_autobuy': False,
        'sell_triggered': False,
        'auto_buy_count': 0
    }
    
    print(f"📊 Initial Position (Manual Buy):")
    print(f"   Strike: {position['strike']} {position['type']}")
    print(f"   Buy Price: ₹{position['buy_price']}")
    print(f"   Quantity: {position['quantity']}")
    print(f"   Initial Stop Loss: ₹{position['advanced_stop_loss']}")
    print()
    
    # Price moves up and trails stop loss to 686.15
    print("📈 STEP 1: Price moves up, stop loss trails to ₹686.15")
    
    # Simulate price at 696+ to get stop loss at 686.15
    trail_price = 696.15
    position['current_price'] = trail_price
    
    # Calculate trailing
    profit = trail_price - position['buy_price']  # 696.15 - 677.75 = 18.4
    steps = int(profit // 10)  # 18.4 / 10 = 1 step
    new_stop_loss = position['buy_price'] + (steps * 10)  # 677.75 + 10 = 687.75
    
    # But from trade history, it sold at 686.15, so let's use that
    position['advanced_stop_loss'] = 686.15
    position['highest_stop_loss'] = 686.15
    position['progressive_minimum'] = 686.15 - 20  # 666.15
    
    print(f"   Price reached: ₹{trail_price}")
    print(f"   Stop Loss trailed to: ₹{position['advanced_stop_loss']}")
    print(f"   Progressive Min: ₹{position['progressive_minimum']}")
    print()
    
    # Price drops and hits stop loss
    print("🔴 STEP 2: Price drops, hits stop loss at ₹686.15")
    
    sell_price = 686.15  # From trade history: Sell price ₹686.15
    position['current_price'] = 685.0  # Price below stop loss
    
    # Trigger auto sell
    print(f"   Price drops to: ₹{position['current_price']}")
    print(f"   Stop Loss: ₹{position['advanced_stop_loss']}")
    print(f"   Stop Loss Hit: {position['current_price'] < position['advanced_stop_loss']}")
    
    # Execute auto sell
    print(f"   🔴 AUTO SELL at ₹{sell_price} (From trade history)")
    
    # Set auto buy trigger
    position['waiting_for_autobuy'] = True
    position['last_stop_loss_price'] = sell_price  # 686.15
    position['sell_triggered'] = True
    position['quantity'] = 0
    
    print(f"   ⚡ Auto Buy Trigger set: ₹{position['last_stop_loss_price']}")
    print(f"   📊 Waiting for Auto Buy: {position['waiting_for_autobuy']}")
    print()
    
    # Price goes to 700+
    print("📈 STEP 3: Price goes to ₹700+ - Should Auto Buy")
    
    test_prices = [690, 695, 700, 705, 710]
    
    for test_price in test_prices:
        position['current_price'] = test_price
        
        # Check ALL auto buy conditions
        waiting = position.get('waiting_for_autobuy', False)
        trigger_price = position.get('last_stop_loss_price', 0)
        price_condition = position['current_price'] >= trigger_price
        sell_triggered = position.get('sell_triggered', False)
        
        # Additional checks that might block auto buy
        auto_buy_count = position.get('auto_buy_count', 0)
        cooldown_enabled = True  # Assuming cooldown is enabled
        in_cooldown = auto_buy_count >= 5 and cooldown_enabled
        
        will_trigger = waiting and price_condition and not in_cooldown
        
        print(f"   Price ₹{test_price}:")
        print(f"     ✓ Waiting for Auto Buy: {waiting}")
        print(f"     ✓ Price >= Trigger: {price_condition} ({test_price} >= {trigger_price})")
        print(f"     ✓ Sell Triggered: {sell_triggered}")
        print(f"     ✓ Auto Buy Count: {auto_buy_count}")
        print(f"     ✓ In Cooldown: {in_cooldown}")
        print(f"     → Will Auto Buy: {'✅ YES' if will_trigger else '❌ NO'}")
        
        if will_trigger:
            print(f"     🟢 AUTO BUY EXECUTED at ₹{test_price}")
            print(f"     📊 New Stop Loss: ₹{test_price - 10}")
            break
        print()
    
    print()
    print("🔍 DEBUGGING CHECKLIST:")
    print("=" * 25)
    print(f"✅ Position has waiting_for_autobuy: {position.get('waiting_for_autobuy', False)}")
    print(f"✅ Auto buy trigger set: ₹{position.get('last_stop_loss_price', 'Not Set')}")
    print(f"✅ Current price: ₹{position['current_price']}")
    print(f"✅ Auto buy count: {position.get('auto_buy_count', 0)}")
    
    print()
    print("💡 POSSIBLE ISSUES:")
    print("1. Position not being monitored (removed from paper_positions)")
    print("2. Auto buy cooldown activated (count >= 5)")
    print("3. sell_triggered flag not being reset properly")
    print("4. Algorithm not being called for this position")
    print("5. Position filtered out due to some condition")

if __name__ == "__main__":
    test_real_scenario()