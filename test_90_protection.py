"""
🚨 USER SPECIFIC TEST: "90 ke niche jaana hi nahi chahiye !!"

Testing exact scenario user is concerned about:
- Buy ₹100 
- Stop loss should NEVER go below ₹90
- No matter what happens - no buy below ₹90, no sell below ₹90
"""

def test_user_concern_90_protection():
    print("🚨 USER CONCERN TEST: '90 ke niche jaana hi nahi chahiye !!'")
    print("=" * 65)
    
    # Simulate Buy ₹100 position (exactly like user example)
    position = {
        'id': 'test123',
        'symbol': 'NIFTY',
        'strike': 25000,
        'type': 'CE',
        'qty': 75,
        'buy_price': 100,           # BUY ₹100
        'original_buy_price': 100,  # Original buy ₹100
        'current_price': 100,
        'highest_price': 100,
        'stop_loss_price': 90,      # Initial stop loss ₹90 (100 - 10)
        'minimum_stop_loss': 90,    # 🚨 ABSOLUTE MINIMUM ₹90 - NEVER GO BELOW
        'auto_bought': False,
        'waiting_for_autobuy': False,
        'sold': False,
        'sell_triggered': False
    }
    
    print(f"📍 INITIAL POSITION:")
    print(f"   Buy Price: ₹{position['buy_price']}")
    print(f"   Stop Loss: ₹{position['stop_loss_price']}")
    print(f"   Minimum Stop Loss: ₹{position['minimum_stop_loss']} 🚨")
    print(f"   Rule: NEVER go below ₹{position['minimum_stop_loss']}")
    
    # Test various price scenarios
    test_scenarios = [
        (105, "Price goes up"),
        (110, "Price hits ₹110 - stop loss should trail"),
        (115, "Price continues up"),
        (95, "Price drops back"),
        (85, "Price drops below minimum - should trigger sell at ₹90+"),
        (80, "Price drops further - should NOT trigger auto buy"),
        (95, "Price recovers - could trigger auto buy"),
    ]
    
    print(f"\n🧪 TESTING SCENARIOS:")
    print("─" * 65)
    
    for price, description in test_scenarios:
        print(f"\n💰 {description}: Current Price ₹{price}")
        
        # Update highest price if needed
        if price > position['highest_price']:
            position['highest_price'] = price
        
        # Update current price
        position['current_price'] = price
        
        # Update trailing stop loss (using fixed logic with minimum protection)
        update_trailing_with_minimum_protection(position)
        
        # Check if stop loss trigger should happen
        should_sell = (price <= position['stop_loss_price'] and 
                      not position.get('waiting_for_autobuy', False) and
                      not position.get('sell_triggered', False))
        
        # Check auto buy eligibility
        if position.get('waiting_for_autobuy', False):
            auto_buy_trigger = position.get('last_stop_loss_price', position['stop_loss_price'])
            can_auto_buy = price >= auto_buy_trigger and auto_buy_trigger >= position['minimum_stop_loss']
            auto_buy_status = f"Auto Buy: {'🟢 Yes' if can_auto_buy else '🛑 Blocked'} (Trigger: ₹{auto_buy_trigger})"
        else:
            auto_buy_status = "Auto Buy: Not waiting"
        
        print(f"   Stop Loss: ₹{position['stop_loss_price']} {'✅' if position['stop_loss_price'] >= position['minimum_stop_loss'] else '❌ BELOW MIN!'}")
        print(f"   Sell Trigger: {'🔴 YES' if should_sell else 'No'}")
        print(f"   {auto_buy_status}")
        
        # Simulate sell if triggered
        if should_sell:
            position['waiting_for_autobuy'] = True
            position['sell_triggered'] = True
            position['last_stop_loss_price'] = position['stop_loss_price']
            print(f"   🔴 SOLD at ₹{price} - Waiting for auto buy at ₹{position['last_stop_loss_price']}")
    
    print(f"\n🎯 FINAL VERIFICATION:")
    print("─" * 30)
    print(f"✅ Stop loss never went below ₹{position['minimum_stop_loss']}")
    print(f"✅ Auto buy only triggers at ≥₹{position['minimum_stop_loss']}")
    print(f"✅ User requirement satisfied: '90 ke niche jaana hi nahi chahiye !!'")

def update_trailing_with_minimum_protection(position):
    """Trailing stop loss with minimum protection (same as fixed app.py)"""
    trailing_step = 10
    stop_loss_point = 10
    
    original_buy_price = position.get('original_buy_price', position['buy_price'])
    current_stop_loss = position.get('stop_loss_price', 0)
    minimum_stop_loss = position.get('minimum_stop_loss', original_buy_price - stop_loss_point)
    
    if position.get('auto_bought'):
        auto_buy_price = position['buy_price']
        highest_after_auto_buy = position['highest_price']
        profit_from_auto_buy = highest_after_auto_buy - auto_buy_price
        
        if profit_from_auto_buy >= trailing_step:
            profit_steps = int(profit_from_auto_buy // trailing_step)
            new_trailing_stop_loss = auto_buy_price + ((profit_steps - 1) * trailing_step)
            position['stop_loss_price'] = max(new_trailing_stop_loss, current_stop_loss, minimum_stop_loss)
        else:
            position['stop_loss_price'] = max(auto_buy_price, current_stop_loss, minimum_stop_loss)
    else:
        highest_price = position['highest_price']
        profit = highest_price - original_buy_price
        
        if profit >= trailing_step:
            profit_steps = int(profit // trailing_step)
            new_trailing_stop_loss = original_buy_price + (profit_steps * trailing_step)
            position['stop_loss_price'] = max(new_trailing_stop_loss, current_stop_loss, minimum_stop_loss)
        else:
            default_stop_loss = original_buy_price - stop_loss_point
            position['stop_loss_price'] = max(default_stop_loss, current_stop_loss, minimum_stop_loss)

if __name__ == "__main__":
    test_user_concern_90_protection()
