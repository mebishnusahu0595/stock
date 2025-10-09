#!/usr/bin/env python3
"""
Test Paper Trading Auto Sell/Buy Integration with Main App
यह test actual app के साथ paper trading की functionality check करता है
"""

import sys
import os
import time
from datetime import datetime as dt

def test_paper_trading_integration():
    """Test paper trading auto sell/buy with main app integration"""
    print("🧪 TESTING PAPER TRADING INTEGRATION WITH MAIN APP")
    print("=" * 70)
    
    try:
        # Import from main app
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from app import (
            app_state, 
            paper_buy_option, 
            execute_auto_sell, 
            execute_auto_buy,
            process_auto_trading,
            LOT_SIZES
        )
        
        # Ensure paper trading is enabled
        app_state['paper_trading_enabled'] = True
        app_state['auto_trading_enabled'] = True
        
        print(f"✅ Paper Trading Enabled: {app_state['paper_trading_enabled']}")
        print(f"✅ Auto Trading Enabled: {app_state['auto_trading_enabled']}")
        print(f"💰 Initial Wallet Balance: ₹{app_state['paper_wallet_balance']}")
        
        # Clear existing positions for clean test
        initial_positions = len(app_state['paper_positions'])
        app_state['paper_positions'] = []
        app_state['paper_trade_history'] = []
        
        print(f"🗑️ Cleared {initial_positions} existing positions for clean test")
        
        # Step 1: Create paper position through app function
        print("\n📈 Step 1: Creating paper position via app function")
        
        # Simulate buying NIFTY 25000 CE @ 100
        lot_size = LOT_SIZES.get('NIFTY', 75)
        success, position = paper_buy_option(
            strike=25000, 
            option_type='CE', 
            price=100, 
            quantity=1,  # 1 lot
            lot_size=lot_size
        )
        
        if success:
            print(f"✅ Position created successfully!")
            print(f"   Strike: {position['strike']} {position['option_type']}")
            print(f"   Buy Price: ₹{position['buy_price']}")
            print(f"   Quantity: {position['quantity']} ({position['lots']} lot)")
            print(f"   Stop Loss: ₹{position['stop_loss_price']}")
            print(f"   Total Cost: ₹{position['total_cost']}")
            print(f"   Wallet Balance: ₹{app_state['paper_wallet_balance']}")
        else:
            print("❌ Failed to create position")
            return
        
        # Step 2: Simulate market data for auto sell
        print("\n📉 Step 2: Simulating price drop for auto sell")
        
        # Mock option data - price drops to 88 (below stop loss of 90)
        app_state['current_option_data'] = {
            'calls': [
                {'strike': 25000, 'option_type': 'CE', 'ltp': 88}  # Below stop loss
            ],
            'puts': []
        }
        
        print(f"📊 Market Data: NIFTY 25000 CE @ ₹88 (Below stop loss ₹{position['stop_loss_price']})")
        print(f"🔍 Paper Positions before auto trading: {len(app_state['paper_positions'])}")
        
        # Run auto trading process
        print("\n🤖 Running auto trading process...")
        process_auto_trading()
        
        print(f"🔍 Paper Positions after auto trading: {len(app_state['paper_positions'])}")
        print(f"📈 Trade History: {len(app_state['paper_trade_history'])}")
        
        # Check if position is waiting for auto buy
        if app_state['paper_positions']:
            pos = app_state['paper_positions'][0]
            print(f"📊 Position Status:")
            print(f"   Waiting for auto buy: {pos.get('waiting_for_autobuy', False)}")
            print(f"   Mode: {pos.get('mode', 'Unknown')}")
            print(f"   Last stop loss price: {pos.get('last_stop_loss_price', 'N/A')}")
        
        # Step 3: Simulate price recovery for auto buy
        print("\n📈 Step 3: Simulating price recovery for auto buy")
        
        # Mock option data - price recovers to 102 (above auto buy trigger)
        app_state['current_option_data'] = {
            'calls': [
                {'strike': 25000, 'option_type': 'CE', 'ltp': 102}  # Above auto buy trigger
            ],
            'puts': []
        }
        
        print(f"📊 Market Data: NIFTY 25000 CE @ ₹102 (Should trigger auto buy)")
        
        # Run auto trading process again
        print("\n🤖 Running auto trading process for auto buy...")
        process_auto_trading()
        
        print(f"🔍 Paper Positions after auto buy: {len(app_state['paper_positions'])}")
        print(f"📈 Trade History: {len(app_state['paper_trade_history'])}")
        
        # Final analysis
        print("\n📊 FINAL ANALYSIS:")
        print("=" * 50)
        
        print(f"💰 Final Wallet Balance: ₹{app_state['paper_wallet_balance']}")
        print(f"📈 Total Trades: {len(app_state['paper_trade_history'])}")
        
        if app_state['paper_positions']:
            final_pos = app_state['paper_positions'][0]
            print(f"📊 Final Position:")
            print(f"   Strike: {final_pos['strike']} {final_pos.get('option_type', final_pos.get('type'))}")
            print(f"   Buy Price: ₹{final_pos.get('buy_price', 'N/A')}")
            print(f"   Current Price: ₹{final_pos.get('current_price', 'N/A')}")
            print(f"   Stop Loss: ₹{final_pos.get('stop_loss_price', 'N/A')}")
            print(f"   Mode: {final_pos.get('mode', 'Unknown')}")
            print(f"   Auto Buy Count: {final_pos.get('auto_buy_count', 0)}")
            print(f"   Auto Sell Count: {final_pos.get('auto_sell_count', 0)}")
        
        if app_state['paper_trade_history']:
            print(f"🔄 Trade History:")
            for i, trade in enumerate(app_state['paper_trade_history'], 1):
                print(f"   {i}. {trade.get('action', 'Unknown')} @ ₹{trade.get('sell_price', trade.get('price', 'N/A'))} | P&L: ₹{trade.get('pnl', 0)}")
        
        # Test result
        if (len(app_state['paper_trade_history']) >= 1 and 
            app_state['paper_positions'] and 
            app_state['paper_positions'][0].get('auto_buy_count', 0) > 0):
            print("\n✅ SUCCESS: Paper trading auto sell/buy cycle completed successfully!")
            print("🎯 Auto sell triggered, auto buy executed, position is back to monitoring")
        else:
            print("\n❌ FAILED: Auto trading cycle not completed properly")
            
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print("Make sure you're running this from the WEBstock directory")
    except Exception as e:
        print(f"❌ Test Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_paper_trading_integration()
