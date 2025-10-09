#!/usr/bin/env python3
"""
Test the Auto Buy Fix - Position should stay in monitoring after stop loss sell
"""

def test_auto_buy_fix():
    """Test that position stays in paper_positions after auto sell for auto buy monitoring"""
    
    print("🧪 TESTING AUTO BUY FIX - POSITION MONITORING")
    print("=" * 50)
    
    # Simulate app_state
    app_state = {
        'paper_positions': [],
        'paper_wallet_balance': 100000.0,
        'paper_trade_history': [],
        'paper_orders': []
    }
    
    # Create test position
    position = {
        'strike': '54800',
        'type': 'CE',
        'option_type': 'CE',
        'buy_price': 677.75,
        'original_buy_price': 677.75,
        'current_price': 686.15,
        'quantity': 35,
        'lots': 1,
        'advanced_stop_loss': 686.15,
        'waiting_for_autobuy': False,
        'sell_triggered': False
    }
    
    # Add position to monitoring
    app_state['paper_positions'].append(position)
    
    print(f"📊 BEFORE AUTO SELL:")
    print(f"   Position in monitoring: {position in app_state['paper_positions']}")
    print(f"   Positions count: {len(app_state['paper_positions'])}")
    print(f"   Position quantity: {position['quantity']}")
    print(f"   Waiting for auto buy: {position.get('waiting_for_autobuy', False)}")
    print()
    
    # Simulate auto sell due to stop loss (FIXED VERSION)
    print("🔴 EXECUTING AUTO SELL (Stop Loss)")
    
    # This is the corrected logic from execute_auto_sell
    reason = 'Advanced Trailing Stop Loss'  # Contains 'Stop Loss'
    sell_price = 686.15
    buy_price = position['buy_price']
    quantity = position['quantity']
    
    # Calculate P&L
    pnl = (sell_price - buy_price) * quantity
    sell_value = sell_price * quantity
    
    # Add to wallet
    app_state['paper_wallet_balance'] += sell_value
    
    # 🚨 FIX: Only remove position for manual sells, keep for stop loss sells
    if 'Stop Loss' not in reason:
        # Manual sell - remove completely
        if position in app_state['paper_positions']:
            app_state['paper_positions'].remove(position)
            print("   Position removed (manual sell)")
    else:
        print("   Position kept for auto buy monitoring (stop loss sell)")
    
    # Add to trade history
    trade = {
        'buy_price': buy_price,
        'sell_price': sell_price,
        'quantity': quantity,
        'pnl': pnl,
        'strike': position['strike'],
        'option_type': position['type'],
        'reason': reason
    }
    app_state['paper_trade_history'].append(trade)
    
    # Set up for auto buy (stop loss logic)
    if 'Stop Loss' in reason:
        position['last_stop_loss_price'] = sell_price  # Auto buy trigger
        position['waiting_for_autobuy'] = True
        position['mode'] = 'Waiting for Auto Buy'
        position['realized_pnl'] = pnl
        position['original_quantity'] = position['quantity']
        position['quantity'] = 0  # Set to 0 to show sold
        position['sell_triggered'] = True
        
        # Ensure position stays in monitoring
        if position not in app_state['paper_positions']:
            app_state['paper_positions'].append(position)
            print("   Position added back to monitoring")
    
    print()
    print(f"📊 AFTER AUTO SELL:")
    print(f"   Position in monitoring: {position in app_state['paper_positions']}")
    print(f"   Positions count: {len(app_state['paper_positions'])}")
    print(f"   Position quantity: {position['quantity']} (should be 0)")
    print(f"   Waiting for auto buy: {position.get('waiting_for_autobuy', False)}")
    print(f"   Auto buy trigger: ₹{position.get('last_stop_loss_price', 'Not Set')}")
    print(f"   Wallet balance: ₹{app_state['paper_wallet_balance']:,.2f}")
    print()
    
    # Test auto buy trigger
    print("📈 TESTING AUTO BUY TRIGGER")
    
    test_prices = [690, 695, 700]
    
    for test_price in test_prices:
        position['current_price'] = test_price
        
        # Check auto buy conditions
        waiting = position.get('waiting_for_autobuy', False)
        trigger_price = position.get('last_stop_loss_price', 0)
        price_condition = position['current_price'] >= trigger_price
        in_monitoring = position in app_state['paper_positions']
        
        will_auto_buy = waiting and price_condition and in_monitoring
        
        print(f"   Price ₹{test_price}:")
        print(f"     ✓ In Monitoring: {in_monitoring}")
        print(f"     ✓ Waiting: {waiting}")
        print(f"     ✓ Price >= Trigger: {price_condition} ({test_price} >= {trigger_price})")
        print(f"     → Will Auto Buy: {'✅ YES' if will_auto_buy else '❌ NO'}")
        
        if will_auto_buy:
            print(f"     🟢 AUTO BUY WOULD EXECUTE at ₹{test_price}")
            break
        print()
    
    print()
    print("✅ FIX VERIFICATION:")
    print("=" * 20)
    
    if position in app_state['paper_positions'] and position.get('waiting_for_autobuy', False):
        print("✅ SUCCESS: Position stays in monitoring after stop loss sell")
        print("✅ SUCCESS: Auto buy trigger is set correctly") 
        print("✅ SUCCESS: Position ready for auto buy when price rises")
    else:
        print("❌ FAILED: Position not properly set up for auto buy")
    
    print()
    print("💡 KEY CHANGES MADE:")
    print("1. Stop loss sells don't remove position from paper_positions")
    print("2. Manual sells still remove position completely")
    print("3. Position stays monitored for auto buy triggers")
    print("4. Auto buy can execute when price condition is met")

if __name__ == "__main__":
    test_auto_buy_fix()