#!/usr/bin/env python3
"""
Debug Advanced Algorithm Auto Buy Issue
Scenario: Buy at ₹677 → Price trails to ₹687 → Sell at ₹686 → Price goes to ₹700+ but no auto buy
"""

def debug_advanced_auto_buy():
    """Debug the exact scenario user described"""
    
    print("🐛 DEBUGGING ADVANCED ALGORITHM AUTO BUY ISSUE")
    print("=" * 55)
    
    # Step 1: Manual buy at ₹677
    position = {
        'strike': '54800',
        'type': 'CE',
        'buy_price': 677.0,
        'original_buy_price': 677.0,
        'current_price': 677.0,
        'advanced_stop_loss': 667.0,  # 677 - 10
        'highest_stop_loss': 667.0,
        'progressive_minimum': 667.0,
        'quantity': 35,
        'waiting_for_autobuy': False,
        'sell_triggered': False,
        'auto_buy_count': 0
    }
    
    print(f"📊 STEP 1: Manual Buy at ₹677")
    print(f"   Buy Price: ₹{position['buy_price']}")
    print(f"   Stop Loss: ₹{position['advanced_stop_loss']}")
    print(f"   Progressive Min: ₹{position['progressive_minimum']}")
    print()
    
    # Step 2: Price goes to ₹687+ → Stop loss trails
    print(f"📈 STEP 2: Price rises to ₹687+ → Stop Loss Trails")
    
    price_687 = 687.0
    position['current_price'] = price_687
    
    # Advanced trailing logic
    profit = price_687 - position['buy_price']  # 687 - 677 = 10
    steps = int(profit // 10)  # 10 / 10 = 1 step
    new_stop_loss = position['buy_price'] + (steps * 10)  # 677 + (1 * 10) = 687
    
    if new_stop_loss > position['highest_stop_loss']:
        position['highest_stop_loss'] = new_stop_loss
        position['progressive_minimum'] = position['highest_stop_loss'] - 20  # 687 - 20 = 667
        position['advanced_stop_loss'] = new_stop_loss
    
    print(f"   Price: ₹{price_687}")
    print(f"   New Stop Loss: ₹{position['advanced_stop_loss']} (Trailed)")
    print(f"   Progressive Min: ₹{position['progressive_minimum']}")
    print()
    
    # Step 3: Price drops → Auto sell at stop loss
    print(f"🔴 STEP 3: Price drops → Auto Sell at Stop Loss")
    
    drop_price = 686.0  # Price drops to trigger stop loss
    position['current_price'] = drop_price
    
    # Check stop loss trigger
    stop_loss_hit = position['current_price'] < position['advanced_stop_loss']
    
    print(f"   Price drops to: ₹{drop_price}")
    print(f"   Stop Loss: ₹{position['advanced_stop_loss']}")
    print(f"   Stop Loss Hit? {stop_loss_hit}")
    
    if stop_loss_hit:
        # Simulate auto sell
        print(f"   🔴 AUTO SELL at ₹{position['advanced_stop_loss']}")
        
        # Set up auto buy trigger (this is the critical part)
        position['waiting_for_autobuy'] = True
        position['last_stop_loss_price'] = position['advanced_stop_loss']  # Should be ₹687
        position['sell_triggered'] = True
        position['quantity'] = 0
        
        print(f"   ⚡ Auto Buy Trigger: ₹{position['last_stop_loss_price']}")
        print(f"   📊 Waiting for Auto Buy: {position['waiting_for_autobuy']}")
    
    print()
    
    # Step 4: Price slowly rises to ₹700+ → Should auto buy
    print(f"📈 STEP 4: Price slowly rises to ₹700+ → Should Auto Buy")
    
    test_prices = [690, 695, 700, 705]
    
    for test_price in test_prices:
        position['current_price'] = test_price
        
        # Check auto buy conditions
        auto_buy_trigger = position.get('last_stop_loss_price', 0)
        waiting_for_autobuy = position.get('waiting_for_autobuy', False)
        price_condition = position['current_price'] >= auto_buy_trigger
        
        will_auto_buy = waiting_for_autobuy and price_condition
        
        print(f"   Price ₹{test_price}:")
        print(f"     Trigger: ₹{auto_buy_trigger}")
        print(f"     Waiting: {waiting_for_autobuy}")
        print(f"     Price >= Trigger: {price_condition} ({test_price} >= {auto_buy_trigger})")
        print(f"     Will Auto Buy: {'✅ YES' if will_auto_buy else '❌ NO'}")
        
        if will_auto_buy:
            # Simulate auto buy
            print(f"     🟢 AUTO BUY EXECUTED at ₹{test_price}")
            
            position['waiting_for_autobuy'] = False
            position['buy_price'] = test_price
            position['advanced_stop_loss'] = test_price - 10
            position['quantity'] = 35
            position['sell_triggered'] = False
            
            # Keep progressive minimum protection
            if position['advanced_stop_loss'] < position['progressive_minimum']:
                position['advanced_stop_loss'] = position['progressive_minimum']
                print(f"     🛡️ Stop Loss protected at ₹{position['progressive_minimum']}")
            
            print(f"     New Stop Loss: ₹{position['advanced_stop_loss']}")
            break
        
        print()
    
    print()
    print("🔍 DEBUGGING CHECKLIST:")
    print("=" * 25)
    print(f"✅ Auto Sell Executed: {position.get('sell_triggered', False)}")
    print(f"✅ Auto Buy Trigger Set: ₹{position.get('last_stop_loss_price', 'Not Set')}")
    print(f"✅ Waiting for Auto Buy: {position.get('waiting_for_autobuy', False)}")
    print(f"✅ Current Price: ₹{position['current_price']}")
    print(f"✅ Trigger Condition: {position['current_price']} >= {position.get('last_stop_loss_price', 0)}")
    
    if position.get('waiting_for_autobuy', False) and position['current_price'] >= position.get('last_stop_loss_price', 0):
        print("✅ ALL CONDITIONS MET - Auto buy should work!")
    else:
        print("❌ ISSUE FOUND - Check the conditions above")
    
    print()
    print("💡 POSSIBLE ISSUES:")
    print("1. waiting_for_autobuy not set to True")
    print("2. last_stop_loss_price not set correctly") 
    print("3. sell_triggered flag blocking auto buy")
    print("4. Position not being monitored by the algorithm")

if __name__ == "__main__":
    debug_advanced_auto_buy()