#!/usr/bin/env python3
"""
Test Paper Trading Auto Sell/Buy Functionality
"""

import sys
import time
from datetime import datetime as dt

# Simulate app state and functions for testing
app_state = {
    'paper_trading_enabled': True,
    'auto_trading_enabled': True,
    'paper_positions': [],
    'paper_orders': [],
    'paper_trade_history': [],
    'paper_wallet_balance': 100000.0,
    'auto_trading_config': {
        'stop_loss_points': 10,
        'trailing_step': 10,
        'max_positions': 10,
        'auto_buy_enabled': True,
        'stop_loss_enabled': True,
        'trailing_enabled': True
    },
    'current_option_data': {
        'calls': [
            {'strike': 25000, 'option_type': 'CE', 'ltp': 85}
        ],
        'puts': [
            {'strike': 25000, 'option_type': 'PE', 'ltp': 140}
        ]
    }
}

LOT_SIZES = {'NIFTY': 75}

def paper_buy_option(strike, option_type, price, quantity, lot_size):
    """Execute paper buy order for testing"""
    total_qty = quantity * lot_size
    total_cost = total_qty * price
    
    # Check if enough balance
    if app_state['paper_wallet_balance'] < total_cost:
        return False, None
    
    # Deduct from wallet
    app_state['paper_wallet_balance'] -= total_cost
    
    # Create position
    position = {
        'id': f"paper_test_{len(app_state['paper_positions'])}_{int(time.time())}",
        'strike': strike,
        'option_type': option_type,
        'buy_price': price,
        'quantity': total_qty,
        'lots': quantity,
        'total_cost': total_cost,
        'timestamp': dt.now().isoformat(),
        'symbol': 'NIFTY',
        'expiry': '2025-08-14',
        'current_price': price,
        'pnl': 0.0,
        'pnl_percentage': 0.0,
        'stop_loss_price': price - 10,
        'original_buy_price': price,
        'highest_price': price,
        'minimum_stop_loss': price - 10,
        'auto_buy_count': 0,
        'auto_sell_count': 0,
        'total_pnl': 0.0,
        'mode': 'Auto-Monitoring',
        'waiting_for_autobuy': False,
        'sell_triggered': False,
        'manual_sold': False,
        'last_update': dt.now(),
        'entry_time': dt.now()
    }
    
    app_state['paper_positions'].append(position)
    return True, position

def execute_auto_sell(position, reason='Stop Loss'):
    """Execute auto sell for paper trading"""
    print(f"🔴 PAPER AUTO SELL: {position['strike']} {position['option_type']} @ ₹{position['current_price']}")
    
    sell_price = position['current_price']
    option_type = position.get('option_type', position.get('type'))
    buy_price = position.get('buy_price', position.get('average_price', 0))
    quantity = position.get('quantity', position.get('qty', 0))
    
    pnl = (sell_price - buy_price) * quantity
    sell_value = sell_price * quantity
    
    # Add to paper wallet
    app_state['paper_wallet_balance'] += sell_value
    
    # Remove position from paper positions
    if position in app_state['paper_positions']:
        app_state['paper_positions'].remove(position)
    
    # Add to paper trade history
    trade = {
        'buy_price': buy_price,
        'sell_price': sell_price,
        'price': sell_price,
        'quantity': quantity,
        'qty': quantity,
        'lots': position.get('lots', 1),
        'pnl': pnl,
        'pnl_percentage': (pnl / (buy_price * quantity)) * 100 if buy_price > 0 else 0,
        'strike': position['strike'],
        'option_type': option_type,
        'type': option_type,
        'action': 'Auto Sell',
        'timestamp': dt.now().isoformat(),
        'time': dt.now().strftime('%Y-%m-%d %H:%M:%S'),
        'reason': reason
    }
    app_state['paper_trade_history'].append(trade)
    
    # For stop loss in paper mode, set up for auto-buy
    if reason == 'Stop Loss':
        # Store the stop loss price for future auto buy trigger
        position['last_stop_loss_price'] = position.get('stop_loss_price', sell_price - 10)
        position['waiting_for_autobuy'] = True
        position['mode'] = 'Auto-Sell (Waiting for Auto-Buy)'
        position['realized_pnl'] = pnl
        position['total_pnl'] = position.get('total_pnl', 0) + pnl
        position['auto_sell_count'] = position.get('auto_sell_count', 0) + 1
        position['sell_triggered'] = True
        
        # Keep position in paper_positions for auto-buy monitoring
        if position not in app_state['paper_positions']:
            app_state['paper_positions'].append(position)
    
    print(f"📄 Paper Auto Sell: P&L: ₹{pnl:.2f}, Wallet: ₹{app_state['paper_wallet_balance']:.2f}")
    return True

def execute_auto_buy(position):
    """Execute auto buy for paper trading"""
    print(f"🟢 PAPER AUTO BUY: {position['strike']} {position.get('option_type', position.get('type'))} @ ₹{position['current_price']}")
    
    buy_price = position['current_price']
    option_type = position.get('option_type', position.get('type'))
    quantity = position.get('quantity', position.get('qty', 0))
    total_cost = quantity * buy_price
    
    # Check if enough balance
    if app_state['paper_wallet_balance'] < total_cost:
        print(f"📄 AUTO BUY FAILED: Insufficient balance. Required: ₹{total_cost:.2f}, Available: ₹{app_state['paper_wallet_balance']:.2f}")
        return False
    
    # Deduct from wallet
    app_state['paper_wallet_balance'] -= total_cost
    
    # Update the original position to continue monitoring
    position['waiting_for_autobuy'] = False
    position['mode'] = 'Auto-Monitoring'
    position['buy_price'] = buy_price
    position['current_price'] = buy_price
    position['stop_loss_price'] = buy_price - 10
    position['auto_buy_count'] = position.get('auto_buy_count', 0) + 1
    
    # Clear all sold flags after successful auto buy
    position['sold'] = False
    position['manual_sold'] = False
    position['sell_in_progress'] = False
    position['sell_triggered'] = False
    
    # Update paper position values for continued monitoring
    position['quantity'] = quantity
    position['total_cost'] = total_cost
    
    print(f"📄 Paper Auto Buy: Cost: ₹{total_cost:.2f}, Wallet: ₹{app_state['paper_wallet_balance']:.2f}")
    return True

def test_paper_auto_trading():
    """Test paper trading auto sell/buy cycle"""
    print("🧪 TESTING PAPER TRADING AUTO SELL/BUY CYCLE")
    print("=" * 60)
    
    # Step 1: Create initial position
    print("\n📈 Step 1: Creating initial paper position")
    success, position = paper_buy_option(25000, 'CE', 100, 1, 75)
    if not success:
        print("❌ Failed to create position")
        return
    
    print(f"✅ Position created: {position['strike']} {position['option_type']} @ ₹{position['buy_price']}")
    print(f"   Stop Loss: ₹{position['stop_loss_price']}")
    print(f"   Wallet Balance: ₹{app_state['paper_wallet_balance']}")
    print(f"   Paper Positions: {len(app_state['paper_positions'])}")
    
    # Step 2: Simulate price drop to trigger stop loss
    print("\n📉 Step 2: Simulating price drop to trigger stop loss")
    position['current_price'] = 88  # Below stop loss of 90
    
    # Check for stop loss trigger
    if (position['current_price'] <= position.get('stop_loss_price', 0) and 
        position.get('stop_loss_price', 0) > 0 and 
        not position.get('waiting_for_autobuy', False) and
        not position.get('sell_triggered', False)):
        
        print(f"🚨 STOP LOSS TRIGGERED: Price ₹{position['current_price']} <= Stop Loss ₹{position['stop_loss_price']}")
        auto_sold = execute_auto_sell(position, reason='Stop Loss')
        
        if auto_sold:
            print(f"✅ Auto sell executed successfully")
            print(f"   Waiting for auto buy: {position.get('waiting_for_autobuy', False)}")
            print(f"   Last stop loss price: {position.get('last_stop_loss_price', 'N/A')}")
            print(f"   Paper Positions: {len(app_state['paper_positions'])}")
        else:
            print("❌ Auto sell failed")
            return
    
    # Step 3: Simulate price recovery to trigger auto buy
    print("\n📈 Step 3: Simulating price recovery to trigger auto buy")
    position['current_price'] = 102  # Above trigger price (stop loss 88 + 10 = 98)
    
    if position.get('waiting_for_autobuy', False):
        last_stop_loss = position.get('last_stop_loss_price', position.get('stop_loss_price', 0))
        auto_buy_trigger_price = last_stop_loss + 10  # Buy 10 points ABOVE stop loss
        
        print(f"   Current Price: ₹{position['current_price']}")
        print(f"   Last Stop Loss: ₹{last_stop_loss}")
        print(f"   Auto Buy Trigger: ₹{auto_buy_trigger_price}")
        
        if position['current_price'] >= auto_buy_trigger_price:
            print(f"🟢 AUTO BUY TRIGGER: Price ₹{position['current_price']} >= Trigger ₹{auto_buy_trigger_price}")
            auto_bought = execute_auto_buy(position)
            
            if auto_bought:
                print(f"✅ Auto buy executed successfully")
                print(f"   New Stop Loss: ₹{position['stop_loss_price']}")
                print(f"   Mode: {position['mode']}")
                print(f"   Auto Buy Count: {position.get('auto_buy_count', 0)}")
                print(f"   Paper Positions: {len(app_state['paper_positions'])}")
            else:
                print("❌ Auto buy failed")
        else:
            print(f"⏳ WAITING: Price ₹{position['current_price']} < Trigger ₹{auto_buy_trigger_price}")
    
    # Summary
    print("\n📊 FINAL SUMMARY:")
    print(f"   Paper Positions: {len(app_state['paper_positions'])}")
    print(f"   Paper Trade History: {len(app_state['paper_trade_history'])}")
    print(f"   Wallet Balance: ₹{app_state['paper_wallet_balance']}")
    
    if app_state['paper_trade_history']:
        print(f"   Last Trade: {app_state['paper_trade_history'][-1]['action']} - P&L: ₹{app_state['paper_trade_history'][-1]['pnl']}")

if __name__ == '__main__':
    test_paper_auto_trading()
