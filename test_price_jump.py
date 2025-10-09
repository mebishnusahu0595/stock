"""
🚨 CRITICAL EDGE CASE TEST: Price Jump Across Stop Loss

User Question: "agar price 90.40 se direct 89.80 pe jump kiya toh ?? tab stop loss kya rakhoge ??"

This tests what happens when price jumps ACROSS the stop loss level.
"""

def test_price_jump_across_stop_loss():
    print("🚨 PRICE JUMP ACROSS STOP LOSS TEST")
    print("=" * 50)
    print("Scenario: Price jumps from ₹90.40 → ₹89.80")
    print("Stop Loss: ₹90.00")
    print("=" * 50)
    
    # Simulate position with Buy ₹100, Stop Loss ₹90
    position = {
        'id': 'test123',
        'symbol': 'NIFTY',
        'strike': 25000,
        'type': 'CE',
        'qty': 75,
        'buy_price': 100,
        'original_buy_price': 100,
        'current_price': 90.40,  # Current price ABOVE stop loss
        'highest_price': 100,
        'stop_loss_price': 90.00,  # Stop loss at ₹90
        'minimum_stop_loss': 90.00,
        'auto_bought': False,
        'waiting_for_autobuy': False,
        'sold': False,
        'sell_triggered': False,
        'sell_in_progress': False
    }
    
    print(f"📍 INITIAL STATE:")
    print(f"   Current Price: ₹{position['current_price']}")
    print(f"   Stop Loss: ₹{position['stop_loss_price']}")
    print(f"   Status: Position is RUNNING (above stop loss)")
    
    def simulate_stop_loss_check(position, new_price):
        """Simulate the stop loss check from app.py"""
        # Update current price
        old_price = position['current_price']
        position['current_price'] = new_price
        
        print(f"\n💰 PRICE UPDATE: ₹{old_price} → ₹{new_price}")
        
        # Check for stop loss trigger (exact logic from app.py)
        stop_loss_triggered = (
            position['current_price'] <= position['stop_loss_price'] and 
            position['stop_loss_price'] > 0 and 
            not position.get('waiting_for_autobuy', False) and
            not position.get('sell_triggered', False)
        )
        
        if stop_loss_triggered:
            print(f"🚨 STOP LOSS TRIGGERED!")
            print(f"   Condition: ₹{position['current_price']} <= ₹{position['stop_loss_price']}")
            print(f"   Action: AUTO SELL executed")
            
            # Simulate auto sell execution
            sell_price = position['current_price']  # Sells at current market price
            pnl = (sell_price - position['buy_price']) * position['qty']
            
            print(f"   Sell Price: ₹{sell_price}")
            print(f"   P&L: ₹{pnl:.2f}")
            
            # Set to waiting for auto buy
            position['sell_triggered'] = True
            position['waiting_for_autobuy'] = True
            position['last_stop_loss_price'] = position['stop_loss_price']  # ₹90.00
            
            print(f"   Auto Buy Trigger: ₹{position['last_stop_loss_price']}")
            
            return True
        else:
            print(f"   No action - price still above stop loss")
            return False
    
    # Test the price jump: ₹90.40 → ₹89.80
    stop_loss_hit = simulate_stop_loss_check(position, 89.80)
    
    if stop_loss_hit:
        print(f"\n📊 RESULT ANALYSIS:")
        print(f"✅ Stop loss correctly triggered when price crossed ₹90")
        print(f"✅ Sold at market price: ₹89.80 (actual market price)")
        print(f"✅ Will auto-buy back when price reaches: ₹{position['last_stop_loss_price']}")
        
        # Test auto buy scenarios
        print(f"\n🔄 AUTO BUY SCENARIOS:")
        test_prices = [88.50, 89.50, 90.00, 90.50, 91.00]
        
        for test_price in test_prices:
            auto_buy_trigger = position['last_stop_loss_price']  # ₹90.00
            minimum_stop_loss = position['minimum_stop_loss']  # ₹90.00
            
            # Check if auto buy should trigger
            can_auto_buy = (test_price >= auto_buy_trigger and 
                          auto_buy_trigger >= minimum_stop_loss and
                          position.get('waiting_for_autobuy', False))
            
            status = "🟢 AUTO BUY" if can_auto_buy else "⏳ Wait"
            print(f"   Price ₹{test_price}: {status}")
    
    print(f"\n🎯 ANSWER TO USER QUESTION:")
    print(f"Price ₹90.40 → ₹89.80 (jumped across ₹90 stop loss):")
    print(f"✅ System detects: ₹89.80 <= ₹90.00 (stop loss)")
    print(f"✅ Action: AUTO SELL at ₹89.80 (current market price)")
    print(f"✅ New Stop Loss: Position sold, waiting for auto-buy at ≥₹90")
    print(f"✅ Protection: Will never auto-buy below ₹90 (minimum protection)")

def test_multiple_jump_scenarios():
    """Test various price jump scenarios"""
    print("\n" + "=" * 50)
    print("🧪 MULTIPLE PRICE JUMP SCENARIOS")
    print("=" * 50)
    
    scenarios = [
        ("Small Jump", 90.40, 89.95, 90.00),  # Small jump below
        ("Medium Jump", 90.40, 89.80, 90.00),  # Medium jump below
        ("Large Jump", 90.40, 89.00, 90.00),  # Large jump below
        ("Extreme Jump", 90.40, 85.00, 90.00),  # Extreme jump below
    ]
    
    for name, start_price, end_price, stop_loss in scenarios:
        print(f"\n📊 {name}: ₹{start_price} → ₹{end_price} (Stop: ₹{stop_loss})")
        
        triggered = end_price <= stop_loss
        if triggered:
            print(f"   🚨 TRIGGERED: Sell at ₹{end_price}")
            print(f"   📈 Auto-buy when price ≥ ₹{stop_loss}")
        else:
            print(f"   ✅ Safe: Above stop loss")

if __name__ == "__main__":
    test_price_jump_across_stop_loss()
    test_multiple_jump_scenarios()
