from flask import Flask, render_template, request, jsonify, session, redirect
from flask_socketio import SocketIO, emit
from datetime import datetime as dt
import datetime
from truedata import TD_live
from kiteconnect import KiteConnect
import logging
import os
import uuid
import pandas as pd
import numpy as np
import pytz
import requests
import json
import threading
import time
import sqlite3
import re
import traceback

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# --- Global Variables ---
SESSION_FILE = 'active_session.txt'
VALID_USERNAME = 'admin'
VALID_PASSWORD = 'admin123'

# Zerodha Kite Connect Configuration - REQUIRED FOR LIVE TRADING
KITE_CONFIG = {
    'api_key': 'w20swyclj9h2oevg',  # Your Zerodha API key
    'api_secret': 'z6tlef7md3k928xcz0bfbjfq1pcv8jjm',  # Your Zerodha API secret
    'access_token': 'JZHnaLXFb7XZEhLoswqcsrt65I9Ko3Dw',  # Will be set after login
    'request_token': '4qOrJQeUtAsB1G4uX6YEirP68NngXHwf'  # Will be set during login flow
}

# Initialize session state equivalent
app_state = {
    'positions': [],
    'trade_history': [],
    'price_history': {},
    'trend_analysis': {},
    'td_obj': None,
    'option_chain_obj': None,
    'last_key': None,
    'logged_in_sessions': {},
    'current_option_data': {},
    'kite': None,  # Zerodha Kite Connect object
    'zerodha_funds': 0.0,
    'zerodha_positions': [],
    'zerodha_orders': [],
    'zerodha_connected': False,
    # Auto Trading Configuration - ALWAYS ENABLED
    'auto_trading_enabled': True,
    'auto_trading_running': True,
    'auto_positions': [],  # Positions with auto buy/sell logic
    'auto_trading_config': {
        'stop_loss_points': 10,  # Exact 10 points stop loss - NO OVERSHOOTING
        'trailing_step': 10,     # Trailing stop loss step - moves in 10 rupee increments
        'max_positions': 5,      # Maximum auto positions
        'auto_buy_enabled': True,
        'stop_loss_enabled': True,
        'trailing_enabled': True,
        'minimum_stop_loss_buffer': 10,  # Minimum buffer below original buy price
        'auto_buy_buffer': 0     # NO BUFFER - Exact trigger point
    }
}

# Lot sizes by symbol
LOT_SIZES = {
    "NIFTY": 75,
    "BANKNIFTY": 35,
    "SENSEX": 20,
    "SBIN": 3400,
    "RELIANCE": 500
}

# Load Zerodha instrument CSV once
instruments_df = pd.read_csv("zerodha_instruments.csv")

# Utility: Convert YYMMDD (TrueData) to DDMMM (Zerodha)
def td_expiry_to_ddmmm(yymm):
    # yymm: '5731' -> 2025-07-31
    year = int('20' + yymm[:2])
    month = int(yymm[2])
    day = int(yymm[3:])
    dt_obj = datetime(year, month, day)
    ddmmm = dt_obj.strftime('%d%b').upper()  # '31JUL'
    return ddmmm, dt_obj.strftime('%Y-%m-%d')

# Main function: TrueData symbol to Zerodha tradingsymbol
def get_zerodha_symbol(td_symbol):
    # Example: NIFTY2573124500CE
    m = re.match(r'([A-Z]+)(\d{4})(\d+)(CE|PE)', td_symbol)
    if not m:
        return None, None, 'Invalid TrueData symbol format.'
    symbol, yymm, strike, opt_type = m.groups()
    ddmmm, expiry_str = td_expiry_to_ddmmm(yymm)
    strike_val = float(strike)
    # Zerodha tradingsymbol: SYMBOL+DDMMM+STRIKE+CE/PE
    search_symbol = f"{symbol}{ddmmm}{int(strike)}{opt_type}"
    # Find in CSV
    row = instruments_df[(instruments_df['tradingsymbol'] == search_symbol) &
                         (instruments_df['expiry'] == expiry_str) &
                         (instruments_df['strike'] == strike_val) &
                         (instruments_df['name'] == symbol)]
    if not row.empty:
        return row.iloc[0]['tradingsymbol'], row.iloc[0]['instrument_token'], None
    else:
        return None, None, f"Zerodha symbol not found for {td_symbol} (tried {search_symbol})"

def get_active_session():
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, 'r') as f:
            data = f.read().strip().split(',')
            if len(data) == 2:
                return {'username': data[0], 'token': data[1]}
    return None

def set_active_session(username, token):
    with open(SESSION_FILE, 'w') as f:
        f.write(f"{username},{token}")

def clear_active_session():
    if os.path.exists(SESSION_FILE):
        os.remove(SESSION_FILE)

def get_market_status():
    """Check if market is open or closed (Always uses IST timezone)"""
    ist = pytz.timezone('Asia/Kolkata')
    now_ist = dt.now(ist)
    current_time = now_ist.time()
    current_day = now_ist.weekday()
    
    # Market timings (IST)
    market_open = dt.strptime('09:15', '%H:%M').time()
    market_close = dt.strptime('15:30', '%H:%M').time()
    
    # Check if it's weekend
    if current_day >= 5:
        return {
            "status": "CLOSED",
            "reason": "Weekend",
            "message": "Market is closed on weekends",
            "next_open": "Monday 9:15 AM IST",
            "current_ist": now_ist.strftime("%H:%M:%S IST")
        }
    
    # Check if it's outside trading hours
    if current_time < market_open:
        return {
            "status": "CLOSED",
            "reason": "Pre-Market",
            "message": "Market opens at 9:15 AM IST",
            "next_open": f"Today at 9:15 AM IST",
            "current_ist": now_ist.strftime("%H:%M:%S IST")
        }
    elif current_time > market_close:
        return {
            "status": "CLOSED",
            "reason": "Post-Market", 
            "message": "Market closed at 3:30 PM IST",
            "next_open": "Tomorrow at 9:15 AM IST",
            "current_ist": now_ist.strftime("%H:%M:%S IST")
        }
    else:
        return {
            "status": "OPEN",
            "reason": "Trading Hours",
            "message": "Market is open for trading",
            "closes_at": "3:30 PM IST",
            "current_ist": now_ist.strftime("%H:%M:%S IST")
        }

def extract_option_type(symbol):
    if pd.isna(symbol):
        return 'UNK'
    symbol = str(symbol).upper()
    if 'CE' in symbol:
        return 'CE'
    elif 'PE' in symbol:
        return 'PE'
    else:
        return 'UNK'

def analyze_price_trend(price_history, current_price, strike, option_type):
    """Analyze price trend and predict profit/loss probability"""
    if len(price_history) < 3:
        return {"trend": "INSUFFICIENT_DATA", "confidence": 0, "prediction": "WAIT"}
    
    prices = list(price_history)
    
    if len(prices) >= 5:
        recent_trend = sum(prices[-3:]) / 3 - sum(prices[-6:-3]) / 3 if len(prices) >= 6 else prices[-1] - prices[0]
        
        # Calculate volatility
        price_changes = [abs(prices[i] - prices[i-1]) for i in range(1, len(prices))]
        volatility = sum(price_changes) / len(price_changes) if price_changes else 0
        
        # Trend strength
        if recent_trend > 2:
            trend = "STRONG_UP"
            confidence = min(90, 50 + (recent_trend * 5))
        elif recent_trend > 0.5:
            trend = "UP"
            confidence = min(75, 40 + (recent_trend * 10))
        elif recent_trend < -2:
            trend = "STRONG_DOWN"
            confidence = min(90, 50 + (abs(recent_trend) * 5))
        elif recent_trend < -0.5:
            trend = "DOWN"
            confidence = min(75, 40 + (abs(recent_trend) * 10))
        else:
            trend = "SIDEWAYS"
            confidence = 30
        
        # Predict profit/loss based on trend and option type
        if option_type == "CE":
            if trend in ["STRONG_UP", "UP"]:
                prediction = "PROFIT"
                confidence = min(confidence + 10, 95)
            elif trend in ["STRONG_DOWN", "DOWN"]:
                prediction = "LOSS"
                confidence = min(confidence + 5, 90)
            else:
                prediction = "NEUTRAL"
        else:
            if trend in ["STRONG_DOWN", "DOWN"]:
                prediction = "PROFIT"
                confidence = min(confidence + 10, 95)
            elif trend in ["STRONG_UP", "UP"]:
                prediction = "LOSS"
                confidence = min(confidence + 5, 90)
            else:
                prediction = "NEUTRAL"
        
        return {
            "trend": trend,
            "confidence": int(confidence),
            "prediction": prediction,
            "volatility": round(volatility, 2),
            "recent_change": round(recent_trend, 2)
        }
    
    return {"trend": "INSUFFICIENT_DATA", "confidence": 0, "prediction": "WAIT"}

def update_price_history(symbol, expiry, strike, option_type, current_price):
    """Update price history for trend analysis"""
    key = f"{symbol}_{expiry}_{strike}_{option_type}"
    current_time = dt.now()
    
    if key not in app_state['price_history']:
        app_state['price_history'][key] = []
    
    app_state['price_history'][key].append({
        'price': current_price,
        'time': current_time
    })
    
    # Keep only last 30 minutes of data
    max_points = 600
    if len(app_state['price_history'][key]) > max_points:
        app_state['price_history'][key] = app_state['price_history'][key][-max_points:]
    
    prices = [p['price'] for p in app_state['price_history'][key]]
    return analyze_price_trend(prices, current_price, strike, option_type)

# Auto Trading Logic Functions
def create_auto_position(strike, option_type, buy_price, qty, symbol='NIFTY', expiry=''):
    """Create new auto position with EXACT 10 point stop loss - STOPS NEVER MOVE DOWN"""
    # EXACTLY 10 points stop loss - WILL SELL AT OR BELOW THIS PRICE
    stop_loss_price = max(buy_price - app_state['auto_trading_config']['stop_loss_points'], 0)
    
    position = {
        'id': str(uuid.uuid4()),
        'symbol': symbol,
        'expiry': expiry,
        'strike': strike,
        'type': option_type,
        'qty': qty,
        'buy_price': buy_price,
        'original_buy_price': buy_price,  # Store original buy price for constant stop loss reference
        'current_price': buy_price,
        'highest_price': buy_price,
        'stop_loss_price': stop_loss_price,
        'minimum_stop_loss': stop_loss_price,  # Constant minimum stop loss level
        'auto_bought': False,
        'waiting_for_autobuy': False,
        'mode': 'Running',
        'entry_time': dt.now(),
        'last_update': dt.now(),
        'total_pnl': 0,
        'realized_pnl': 0,
        'auto_sell_count': 0,
        # CRITICAL SAFETY FLAGS: Initialize protection against multiple sells and unwanted auto buys
        'sold': False,
        'manual_sold': False,
        'sell_in_progress': False,
        'sell_triggered': False
    }
    app_state['auto_positions'].append(position)
    
    # Debug print to confirm stop loss is set correctly for manual buy
    print(f"📍 MANUAL BUY POSITION CREATED: {strike} {option_type} @ ₹{buy_price} | Stop Loss: ₹{stop_loss_price} (Will sell at or below this price)")
    
    return position

def remove_auto_position_by_strike(strike, option_type, symbol='NIFTY'):
    """Remove auto position by strike and option type to prevent auto buy after manual sell"""
    removed_count = 0
    for auto_pos in app_state['auto_positions'][:]:  # Create a copy to iterate safely
        if (float(auto_pos['strike']) == float(strike) and 
            auto_pos['type'] == option_type and
            auto_pos['symbol'] == symbol):
            app_state['auto_positions'].remove(auto_pos)
            removed_count += 1
            print(f"🗑️ REMOVED AUTO POSITION: {strike} {option_type} (Manual Sell)")
    return removed_count

def update_auto_position_price(position, new_price):
    """Update position price and handle auto trading logic"""
    # Convert new_price to float to handle string inputs
    try:
        new_price = float(new_price)
    except (ValueError, TypeError):
        print(f"[ERROR] Invalid price format: {new_price}, skipping update")
        return False
    
    old_price = float(position['current_price'])
    position['current_price'] = new_price
    position['last_update'] = dt.now()
    
    # Update highest price for trailing stop loss
    if new_price > float(position['highest_price']):
        position['highest_price'] = new_price
    
    # Update trailing stop loss first
    update_trailing_stop_loss(position)
    
    # Debug print for stop loss monitoring (only when price changes significantly or near stop loss)
    # Debug print for stop loss monitoring (only when price changes significantly or near stop loss)
    price_diff = abs(new_price - old_price)
    near_stop_loss = abs(new_price - position['stop_loss_price']) < 5  # Within 5 rupees of stop loss
    
    if price_diff > 2 or near_stop_loss:  # Only print when price changes by more than 2 rupees or near stop loss
        print(f"🔍 MONITORING: {position['strike']} {position['type']} | Current: ₹{new_price} | Stop Loss: ₹{position['stop_loss_price']} | Auto Bought: {position.get('auto_bought', False)}")
    
    # Check for stop loss trigger - CRITICAL: Use >= to catch any price at or below stop loss
    if (position['current_price'] <= position['stop_loss_price'] and 
        position['stop_loss_price'] > 0 and 
        not position.get('waiting_for_autobuy', False) and
        not position.get('sell_triggered', False)):  # SAFETY: Prevent duplicate sells
        # AUTO SELL - Stop Loss Hit (Price at or below stop loss)
        print(f"🚨 STOP LOSS TRIGGERED: {position['strike']} {position['type']} @ ₹{new_price} (Stop Loss: ₹{position['stop_loss_price']})")
        sell_executed = execute_auto_sell(position, reason='Stop Loss')
        if sell_executed:
            position['sell_triggered'] = True  # Set after trade is recorded
            return True
        return False
    
    return False

def fetch_live_option_data_for_auto_trading():
    """Automatically fetch live option data for auto trading purposes"""
    try:
        # Only fetch if we have an active option chain
        if not app_state['option_chain_obj']:
            return
        
        # Get fresh option chain data
        df_chain = app_state['option_chain_obj'].get_option_chain()
        if df_chain is None or df_chain.empty:
            return
        
        # Convert and process the data (similar to api_option_chain_data)
        def convert_df_to_records(df):
            if df.empty:
                return []
            # Convert numeric columns to float to ensure proper data types
            numeric_columns = ['ltp', 'bid', 'ask', 'strike', 'volume', 'oi']
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            return df.round(2).to_dict('records')

        def map_type(type_val):
            return 'CE' if str(type_val).upper() in ['CALL', 'CE', 'C'] else 'PE'

        def extract_option_type(symbol):
            return 'CE' if 'CALL' in str(symbol).upper() or symbol.endswith('CE') else 'PE'

        # Process the dataframe
        try:
            if 'type' in df_chain.columns:
                df_chain['option_type'] = df_chain['type'].apply(map_type)
            else:
                df_chain['option_type'] = df_chain.index.to_series().apply(extract_option_type)
        except Exception as e:
            print(f"Error processing option types: {e}")
            return

        # Convert strike column to numeric
        if 'strike' in df_chain.columns:
            df_chain['strike'] = pd.to_numeric(df_chain['strike'], errors='coerce')
        
        # Separate calls and puts
        calls = df_chain[df_chain['option_type'] == 'CE']
        puts = df_chain[df_chain['option_type'] == 'PE']

        # Get underlying value (same logic as main option chain API)
        underlying = None
        if 'underlying_value' in df_chain.columns:
            underlying = df_chain.iloc[0]['underlying_value']
        
        if underlying is None or underlying == 0:
            mid_index = len(df_chain) // 2
            underlying = df_chain.iloc[mid_index]['strike'] if not df_chain.empty else 25000  # Fallback to 25000
        
        # Find ATM strike using actual underlying price
        current_price = underlying
        if not calls.empty and 'strike' in calls.columns and current_price is not None:
            atm_strike = calls.iloc[(calls['strike'] - current_price).abs().argsort()[:1]]
        else:
            atm_strike = pd.DataFrame()

        # Update current option data for auto trading
        app_state['current_option_data'] = {
            'calls': convert_df_to_records(calls.head(10)),
            'puts': convert_df_to_records(puts.head(10)),
            'atm': convert_df_to_records(atm_strike),
            'underlying_price': float(current_price) if current_price else None,
            'total_options': len(df_chain),
            'ce_count': len(calls),
            'pe_count': len(puts)
        }

    except Exception as e:
        print(f"Error fetching live option data for auto trading: {e}")

def test_stop_loss_manually(position_id, test_price):
    """Test function to manually trigger stop loss for a position"""
    try:
        for position in app_state['auto_positions']:
            if position['id'] == position_id:
                print(f"🧪 TESTING STOP LOSS: {position['strike']} {position['type']} with test price ₹{test_price}")
                update_auto_position_price(position, test_price)
                return True
        print(f"Position with ID {position_id} not found")
        return False
    except Exception as e:
        print(f"Error testing stop loss: {e}")
        return False

def execute_auto_sell(position, reason='Stop Loss'):
    """Execute auto sell and set position to waiting for auto buy. Also place Zerodha sell order if connected."""
    
    # Prevent duplicate auto sells - check ONLY sell_triggered and sell_in_progress for auto sells
    # For auto sells (Stop Loss), we allow the first sell but prevent subsequent ones
    if reason == 'Stop Loss':
        if position.get('sell_triggered', False) or position.get('sell_in_progress', False):
            print(f"⚠️ DUPLICATE SELL PREVENTED: {position['strike']} {position['type']} already sold or in progress")
            return False
    else:
        # For manual sells, check all flags
        if position.get('sell_in_progress', False) or position.get('sell_triggered', False) or position.get('sold', False):
            print(f"⚠️ DUPLICATE SELL PREVENTED: {position['strike']} {position['type']} already sold or in progress")
            return False

    # Mark sell in progress to prevent race conditions
    position['sell_in_progress'] = True

    sell_price = position['current_price']
    pnl = (sell_price - position['buy_price']) * position['qty']

    # Place Zerodha sell order if connected
    if app_state.get('zerodha_connected') and app_state.get('kite'):
        try:
            symbol = position['symbol']
            strike = position['strike']
            option_type = position['type']
            expiry = position.get('expiry', '')
            # Handle expiry - ensure it's a string
            if isinstance(expiry, dict):
                expiry = expiry.get('value', '') if expiry else ''
            elif not isinstance(expiry, str):
                expiry = str(expiry) if expiry else ''
            # Convert expiry from YYYY-MM-DD to YYMMDD for TrueData format
            try:
                if '-' in expiry:  # Format: "2025-08-07"
                    year, month, day = expiry.split('-')
                    yy = year[-2:]  # Take last 2 digits of year
                    expiry_td = f"{yy}{month}{day}"  # "250807"
                else:
                    expiry_td = expiry
            except Exception as e:
                print(f"[ERROR] Failed to parse expiry date {expiry}: {e}")
                order_status = f"Expiry parse error: {e}"
                expiry_td = expiry
            # Build TrueData symbol and convert to Zerodha format
            td_symbol = f"{symbol}{expiry_td}{int(strike)}{option_type}"
            print(f"[DEBUG] AUTO SELL - Built TrueData symbol: {td_symbol}")
            tradingsymbol = td_to_zerodha_symbol(td_symbol)
            if tradingsymbol:
                print(f"[DEBUG] AUTO SELL - Placing order for: {tradingsymbol}")
                order_id = app_state['kite'].place_order(
                    variety=app_state['kite'].VARIETY_REGULAR,
                    exchange=app_state['kite'].EXCHANGE_NFO,
                    tradingsymbol=tradingsymbol,
                    transaction_type=app_state['kite'].TRANSACTION_TYPE_SELL,
                    quantity=position['qty'],
                    order_type=app_state['kite'].ORDER_TYPE_MARKET,
                    product=app_state['kite'].PRODUCT_MIS
                )
                order_status = f"✅ Order ID: {order_id}"
                print(f"[SUCCESS] AUTO SELL order placed: {order_id}")
            else:
                order_status = "❌ Zerodha symbol conversion failed"
                print(f"[ERROR] Could not convert TrueData symbol: {td_symbol}")
        except Exception as e:
            order_status = f"❌ Zerodha order error: {e}"
            print(f"[ERROR] AUTO SELL order failed: {e}")
    else:
        order_status = "⚠️ Zerodha not connected"

    # Record trade and increment sell count only for first auto sell
    app_state['trade_history'].append({
        'action': f'Auto Sell ({reason})',
        'type': position['type'],
        'strike': position['strike'],
        'qty': position['qty'],
        'price': sell_price,
        'pnl': pnl,
        'position_id': position['id'],
        'order_status': order_status,
        'time': dt.now().strftime('%Y-%m-%d %H:%M:%S')
    })

    # Only set to waiting for auto buy if this is a stop loss trigger, not manual sell
    if reason == 'Stop Loss':
        # Store the stop loss price for future auto buy trigger
        position['last_stop_loss_price'] = position['stop_loss_price']
        position['waiting_for_autobuy'] = True
        position['mode'] = 'Auto-Sell (Waiting for Auto-Buy)'
        position['realized_pnl'] = pnl
        position['total_pnl'] += pnl
        position['auto_sell_count'] += 1
        position['sell_in_progress'] = False
        # Set sell_triggered after trade recording and count increment to prevent duplicates
        position['sell_triggered'] = True
        # For auto sell, don't set sold=True as it should allow auto buy later
        print(f"🔴 AUTO SELL: {position['strike']} {position['type']} @ ₹{sell_price} | P&L: ₹{pnl:.2f} | Will auto-buy at ₹{position['last_stop_loss_price']} | {order_status}")
    else:
        position['manual_sold'] = True
        position['sell_in_progress'] = False
        position['sell_triggered'] = True
        position['sold'] = True  # Mark as sold for manual sell
        position['waiting_for_autobuy'] = False  # CRITICAL: Stop any auto buy attempts
        position['mode'] = 'Manual Sell - Position Closed'
        print(f"🔴 MANUAL SELL: {position['strike']} {position['type']} @ ₹{sell_price} | P&L: ₹{pnl:.2f} | Position will be removed")

    return True


def execute_manual_sell_auto_position(strike, option_type, symbol='NIFTY'):
    """Execute manual sell and completely remove auto position to prevent auto buy"""
    removed_positions = []
    
    for auto_pos in app_state['auto_positions'][:]:  # Create a copy to iterate safely
        if (float(auto_pos['strike']) == float(strike) and 
            auto_pos['type'] == option_type and
            auto_pos['symbol'] == symbol):
            
            # Calculate final P&L
            sell_price = auto_pos.get('current_price', auto_pos['buy_price'])
            pnl = (sell_price - auto_pos['buy_price']) * auto_pos['qty']
            
            # Record final trade
            app_state['trade_history'].append({
                'action': 'Manual Sell (Auto Position Removed)',
                'type': auto_pos['type'],
                'strike': auto_pos['strike'],
                'qty': auto_pos['qty'],
                'price': sell_price,
                'pnl': pnl,
                'position_id': auto_pos['id'],
                'order_status': '✅ Auto position removed',
                'time': dt.now().strftime('%Y-%m-%d %H:%M:%S')
            })
            
            # Remove position completely
            app_state['auto_positions'].remove(auto_pos)
            removed_positions.append(auto_pos)
            print(f"🗑️ COMPLETELY REMOVED AUTO POSITION: {strike} {option_type} (Manual Sell) - No Auto Buy Will Trigger")
    
    return len(removed_positions)


def execute_auto_buy(position):
    """Execute auto buy when price reaches minimum stop loss. Also place Zerodha buy order if connected."""
    
    # CRITICAL SAFETY CHECK: Prevent auto buy after manual sell
    if position.get('manual_sold', False) or position.get('sold', False):
        print(f"⚠️ AUTO BUY BLOCKED: {position['strike']} {position['type']} was manually sold - removing position")
        # Remove the position completely if it was manually sold
        if position in app_state['auto_positions']:
            app_state['auto_positions'].remove(position)
        return False
    
    buy_price = position['current_price']
    cost = position['qty'] * buy_price

    # Check if Zerodha is connected before placing order
    if app_state.get('zerodha_connected') and app_state.get('kite'):
        # Place Zerodha buy order if connected
        try:
            symbol = position['symbol']
            strike = position['strike']
            option_type = position['type']
            expiry = position.get('expiry', '')
            
            # Handle expiry - ensure it's a string
            if isinstance(expiry, dict):
                expiry = expiry.get('value', '') if expiry else ''
            elif not isinstance(expiry, str):
                expiry = str(expiry) if expiry else ''
            
            # Convert expiry from YYYY-MM-DD to YYMMDD for TrueData format
            try:
                if '-' in expiry:  # Format: "2025-08-07"
                    year, month, day = expiry.split('-')
                    yy = year[-2:]  # Take last 2 digits of year
                    expiry_td = f"{yy}{month}{day}"  # "250807"
                else:
                    expiry_td = expiry
            except Exception as e:
                print(f"[ERROR] Failed to parse expiry date {expiry}: {e}")
                order_status = f"Expiry parse error: {e}"
                expiry_td = expiry
            
            # Build TrueData symbol and convert to Zerodha format
            td_symbol = f"{symbol}{expiry_td}{int(strike)}{option_type}"
            print(f"[DEBUG] AUTO BUY - Built TrueData symbol: {td_symbol}")
            
            tradingsymbol = td_to_zerodha_symbol(td_symbol)
            if tradingsymbol:
                print(f"[DEBUG] AUTO BUY - Placing order for: {tradingsymbol}")
                order_id = app_state['kite'].place_order(
                    variety=app_state['kite'].VARIETY_REGULAR,
                    exchange=app_state['kite'].EXCHANGE_NFO,
                    tradingsymbol=tradingsymbol,
                    transaction_type=app_state['kite'].TRANSACTION_TYPE_BUY,
                    quantity=position['qty'],
                    order_type=app_state['kite'].ORDER_TYPE_MARKET,
                    product=app_state['kite'].PRODUCT_MIS
                )
                order_status = f"✅ Order ID: {order_id}"
                print(f"[SUCCESS] AUTO BUY order placed: {order_id}")
            else:
                order_status = "❌ Zerodha symbol conversion failed"
                print(f"[ERROR] Could not convert TrueData symbol: {td_symbol}")
        except Exception as e:
            order_status = f"❌ Zerodha order error: {e}"
            print(f"[ERROR] AUTO BUY order failed: {e}")
    else:
        order_status = "⚠️ Zerodha not connected"

    # Update position
    position['buy_price'] = buy_price
    position['highest_price'] = buy_price
    # Set stop loss to auto buy price (NO LOSS on auto buy)
    position['stop_loss_price'] = buy_price
    position['auto_bought'] = True
    position['mode'] = 'Running'
    position['waiting_for_autobuy'] = False
    
    # CRITICAL: Clear all sold flags after successful auto buy
    position['sold'] = False
    position['manual_sold'] = False
    position['sell_in_progress'] = False
    position['sell_triggered'] = False

    # Debug print to confirm stop loss is set correctly for auto buy
    print(f"📍 AUTO BUY EXECUTED: {position['strike']} {position['type']} @ ₹{buy_price} | Stop Loss: ₹{position['stop_loss_price']} (No loss on auto buy)")

    # Record trade
    app_state['trade_history'].append({
        'action': 'Auto Buy',
        'type': position['type'],
        'strike': position['strike'],
        'qty': position['qty'],
        'price': buy_price,
        'pnl': 0,
        'position_id': position['id'],
        'order_status': order_status,
        'time': dt.now().strftime('%Y-%m-%d %H:%M:%S')
    })

    print(f"🟢 AUTO BUY: {position['strike']} {position['type']} @ ₹{buy_price} | Constant Stop Loss: ₹{position['stop_loss_price']} | {order_status}")
    return True

def update_trailing_stop_loss(position):
    """STEP-BASED TRAILING STOP LOSS - MOVES IN 10 RUPEE STEPS ABOVE BUY PRICE"""
    trailing_step = app_state['auto_trading_config']['trailing_step']  # 10
    stop_loss_point = app_state['auto_trading_config']['stop_loss_points']  # 10
    
    # Get the original buy price 
    original_buy_price = position.get('original_buy_price', position['buy_price'])
    current_stop_loss = position.get('stop_loss_price', 0)
    
    if position.get('auto_bought'):
        # Auto buy: stop loss = auto buy price (no loss), then trails in 10 rupee steps
        auto_buy_price = position['buy_price']
        highest_after_auto_buy = position['highest_price']
        profit_from_auto_buy = highest_after_auto_buy - auto_buy_price
        
        if profit_from_auto_buy >= trailing_step:  # If profit >= 10
            # Calculate how many 10-rupee steps we've achieved
            profit_steps = int(profit_from_auto_buy // trailing_step)  # Number of complete 10-rupee steps
            # Stop loss = auto buy price + (steps * 10) - 10
            # Example: Auto buy ₹90, highest ₹115 → 2 steps → Stop loss = ₹90 + 10 = ₹100
            new_trailing_stop_loss = auto_buy_price + ((profit_steps - 1) * trailing_step)
            # NEVER let stop loss go down - only up or stay same
            position['stop_loss_price'] = max(new_trailing_stop_loss, current_stop_loss)
        else:
            # No profit yet, stop loss = auto buy price (no loss on auto buy)
            # But never go below current stop loss if it's higher
            position['stop_loss_price'] = max(auto_buy_price, current_stop_loss)
    else:
        # Manual buy: STEP-BASED TRAILING - Stop loss moves in 10 rupee steps above buy price
        highest_price = position['highest_price']
        profit = highest_price - original_buy_price
        
        if profit >= trailing_step:  # If profit >= 10
            # Calculate how many 10-rupee steps we've achieved from buy price
            profit_steps = int(profit // trailing_step)  # Number of complete 10-rupee steps
            # Stop loss = buy price + (steps * 10)
            # Example: Buy ₹120.70, Highest ₹131.50 → 1 step → Stop loss = ₹120.70 + 10 = ₹130.70
            # Example: Buy ₹120.70, Highest ₹145.00 → 2 steps → Stop loss = ₹120.70 + 20 = ₹140.70
            new_trailing_stop_loss = original_buy_price + (profit_steps * trailing_step)
            # CRITICAL: NEVER let stop loss go down - only up or stay same
            position['stop_loss_price'] = max(new_trailing_stop_loss, current_stop_loss)
            
            # Debug print for trailing stop loss calculation
            print(f"🎯 STEP TRAILING: Buy ₹{original_buy_price} | Highest ₹{highest_price} | Profit ₹{profit:.2f} | Steps: {profit_steps} | NEW Stop Loss ₹{position['stop_loss_price']:.2f}")
        else:
            # Default: EXACTLY 10 points below buy price
            # But if current stop loss is higher, keep it there
            default_stop_loss = original_buy_price - stop_loss_point
            position['stop_loss_price'] = max(default_stop_loss, current_stop_loss)

def process_auto_trading():
    """Main auto trading processing function"""
    if not app_state['auto_trading_enabled']:
        print("⚠️ Auto trading disabled")
        return
    
    try:
        # Debug: Check if we have any positions to monitor
        if not app_state['auto_positions']:
            # Only print this occasionally to avoid spam
            if not hasattr(process_auto_trading, 'last_no_positions_print'):
                process_auto_trading.last_no_positions_print = 0
            
            current_time = time.time()
            if current_time - process_auto_trading.last_no_positions_print > 10:  # Print every 10 seconds
                print("ℹ️ No auto positions to monitor")
                process_auto_trading.last_no_positions_print = current_time
            return
        
        # Automatically fetch fresh option data if we have positions to monitor
        fetch_live_option_data_for_auto_trading()
        
        # Process all option data for auto trading
        all_options = []
        if app_state['current_option_data']:
            if 'calls' in app_state['current_option_data']:
                all_options.extend(app_state['current_option_data']['calls'])
            if 'puts' in app_state['current_option_data']:
                all_options.extend(app_state['current_option_data']['puts'])
        
        # Debug: Check if we have option data
        if not all_options:
            print("⚠️ No option data available for auto trading")
            return
        
        # Update existing positions
        positions_checked = 0
        for position in app_state['auto_positions'][:]:  # Create copy to allow removal during iteration
            positions_checked += 1
            
            # CRITICAL SAFETY: Skip positions that have been manually sold
            if position.get('manual_sold', False):
                print(f"🗑️ REMOVING MANUALLY SOLD POSITION: {position['strike']} {position['type']}")
                app_state['auto_positions'].remove(position)
                continue
            
            # CRITICAL SAFETY: Skip positions currently being sold to prevent race conditions
            if position.get('sell_in_progress', False):
                print(f"⏳ SKIPPING POSITION IN SELL PROCESS: {position['strike']} {position['type']}")
                continue
            
            # Find matching option data
            matching_option = None
            for option in all_options:
                try:
                    option_strike = float(option.get('strike', 0))
                    position_strike = float(position['strike'])
                    option_type = str(option.get('option_type', ''))
                    position_type = str(position['type'])
                    
                    if (option_strike == position_strike and 
                        option_type == position_type):
                        matching_option = option
                        break
                except (ValueError, TypeError) as e:
                    print(f"[DEBUG] Error comparing option data: {e}")
                    continue
            
            if matching_option:
                try:
                    current_price = float(matching_option.get('ltp', 0))
                    
                    if position.get('waiting_for_autobuy', False):
                        # CRITICAL SAFETY: Double-check manual sell before auto buy
                        if position.get('manual_sold', False):
                            print(f"🛑 AUTO BUY CANCELLED: {position['strike']} {position['type']} was manually sold")
                            app_state['auto_positions'].remove(position)
                            continue
                        
                        # Auto buy trigger: Use the SAME stop loss price where it was sold
                        # This ensures auto buy happens at the exact price where stop loss was hit
                        last_stop_loss = position.get('last_stop_loss_price', position.get('stop_loss_price', 0))
                        auto_buy_trigger_price = last_stop_loss  # Buy back at same price where sold
                        
                        # Only trigger auto buy if current price reaches the trigger price
                        if current_price >= auto_buy_trigger_price:
                            print(f"🟢 AUTO BUY TRIGGER: Price ₹{current_price} >= Last Stop Loss ₹{auto_buy_trigger_price}")
                            execute_auto_buy(position)
                        else:
                            print(f"⏳ WAITING FOR AUTO BUY: Price ₹{current_price} < Trigger ₹{auto_buy_trigger_price}")
                    else:
                        # Update position and check for auto sell
                        auto_sold = update_auto_position_price(position, current_price)
                        if auto_sold:
                            print(f"🔴 AUTO SELL TRIGGERED: {position['strike']} {position['type']} @ ₹{current_price}")
                            continue
                except (ValueError, TypeError) as e:
                    print(f"[ERROR] Invalid price data in option: {matching_option}, error: {e}")
                    current_price = float(position.get('current_price', 0))
            else:
                # If no matching option data, use last known price but still check stop loss
                current_price = float(position.get('current_price', 0))
                print(f"⚠️ No matching option data for {position['strike']} {position['type']}, using last price: ₹{current_price}")
                
                # Still check stop loss with last known price
                if not position.get('waiting_for_autobuy', False):
                    auto_sold = update_auto_position_price(position, current_price)
                    if auto_sold:
                        print(f"🔴 AUTO SELL TRIGGERED (Last Price): {position['strike']} {position['type']} @ ₹{current_price}")
                        continue
        
        # Debug: Print processing summary occasionally
        if app_state['auto_positions']:
            if not hasattr(process_auto_trading, 'last_summary_print'):
                process_auto_trading.last_summary_print = 0
            
            current_time = time.time()
            if current_time - process_auto_trading.last_summary_print > 5:  # Print every 5 seconds
                print(f"🤖 Auto Trading: {positions_checked}/{len(app_state['auto_positions'])} positions checked | Options data: {len(all_options)} options")
                process_auto_trading.last_summary_print = current_time
        
    except Exception as e:
        print(f"❌ Auto Trading Error: {e}")
        traceback.print_exc()

def auto_trading_background_task():
    """Background task for auto trading"""
    print("🤖 Auto trading background task started")
    while True:
        try:
            if app_state['auto_trading_running']:
                process_auto_trading()
            else:
                # Sleep longer when auto trading is disabled
                time.sleep(2)
        except Exception as e:
            print(f"❌ Auto trading background error: {e}")
            import traceback
            traceback.print_exc()
        
        time.sleep(0.5)  # Check every 0.5 seconds for faster response

# Initialize TrueData client
def initialize_truedata():
    if app_state['td_obj'] is None:
        try:
            app_state['td_obj'] = TD_live(
                'tdwsp690', 'bishnu@690',
                live_port=8084,
                log_level=logging.WARNING,
                compression=False
            )
            print("TrueData client initialized successfully")
        except Exception as e:
            print(f"Failed to initialize TrueData client: {e}")

# Initialize Zerodha Kite Connect
def initialize_kite():
    """Initialize Kite Connect client - REQUIRED for all trading"""
    if not KITE_CONFIG['api_key'] or KITE_CONFIG['api_key'] == 'your_zerodha_api_key_here':
        print("❌ ERROR: Zerodha API key not configured! Please add your API key to KITE_CONFIG")
        return False
        
    if not KITE_CONFIG['api_secret'] or KITE_CONFIG['api_secret'] == 'your_zerodha_api_secret_here':
        print("❌ ERROR: Zerodha API secret not configured! Please add your API secret to KITE_CONFIG")
        return False
        
    try:
        app_state['kite'] = KiteConnect(api_key=KITE_CONFIG['api_key'])
        if KITE_CONFIG['access_token']:
            app_state['kite'].set_access_token(KITE_CONFIG['access_token'])
            app_state['zerodha_connected'] = True
            print("✅ Kite Connect initialized successfully with access token")
            return True
        else:
            print("⚠️ Kite Connect initialized but access token required for trading")
            return True
    except Exception as e:
        print(f"❌ Failed to initialize Kite Connect: {e}")
        return False

def check_zerodha_connection():
    """Check if Zerodha is properly connected for trading"""
    if not app_state['kite']:
        return False, "Kite Connect not initialized"
    
    if not KITE_CONFIG['access_token']:
        return False, "Access token required - please complete Zerodha login"
    
    try:
        # Test connection by getting user profile
        profile = app_state['kite'].profile()
        app_state['zerodha_connected'] = True
        return True, f"Connected as {profile.get('user_name', 'User')}"
    except Exception as e:
        app_state['zerodha_connected'] = False
        return False, f"Connection failed: {str(e)}"

@app.route('/')
def index():
    """Main dashboard route with Zerodha request_token handling"""
    # Check if this is a Zerodha callback with request_token
    request_token = request.args.get('request_token')
    status = request.args.get('status')
    
    if request_token:
        print(f"🔑 Zerodha redirect detected on root route with request_token: {request_token[:10]}...")
        
        try:
            # Create new KiteConnect instance
            kite = KiteConnect(api_key=KITE_CONFIG['api_key'])
            
            # Generate session
            data = kite.generate_session(request_token, api_secret=KITE_CONFIG['api_secret'])
            access_token = data['access_token']
            
            # Store tokens
            KITE_CONFIG['access_token'] = access_token
            KITE_CONFIG['request_token'] = request_token
            
            # Update app state
            app_state['kite'] = kite
            kite.set_access_token(access_token)
            app_state['zerodha_connected'] = True
            
            # Save to file for persistence
            try:
                with open('access_token.txt', 'w') as f:
                    f.write(access_token)
                print(f"✅ Access token saved to file: {access_token[:20]}...")
            except Exception as file_error:
                print(f"⚠️ Failed to save access token to file: {file_error}")
            
            # Verify connection
            try:
                profile = kite.profile()
                user_name = profile.get('user_name', 'Unknown')
                broker = profile.get('broker', 'Unknown')
                print(f"✅ Zerodha connection verified - User: {user_name}, Broker: {broker}")
                
                # Create success message for the template
                success_message = f"""
                ✅ Zerodha Login Successful!<br>
                👤 User: {user_name}<br>
                🏢 Broker: {broker}<br>
                🔑 Access Token: {access_token[:10]}...<br>
                🕒 Connected at: {dt.now().strftime('%Y-%m-%d %H:%M:%S')}
                """
                
                # Render template with success message
                return render_template('index.html', zerodha_success=success_message)
                
            except Exception as verify_error:
                print(f"⚠️ Access token verification failed: {verify_error}")
                # Still render normal template as token was generated
                return render_template('index.html', zerodha_success="✅ Access token generated but verification pending")
                
        except Exception as e:
            print(f"❌ Failed to process request_token: {e}")
            error_message = f"❌ Zerodha login failed: {str(e)}"
            return render_template('index.html', zerodha_error=error_message)
    
    # Normal dashboard access without request_token
    return render_template('index.html')

@app.route('/api/stop-loss/<symbol>', methods=['GET'])
def get_stop_loss_for_symbol(symbol):
    """Return current stop loss for a symbol from auto positions or Zerodha positions"""
    # First check auto trading positions (they have stop_loss_price)
    for pos in app_state.get('auto_positions', []):
        if pos.get('symbol') == symbol and 'stop_loss_price' in pos:
            return jsonify({
                'success': True,
                'symbol': symbol,
                'stop_loss': pos['stop_loss_price'],
                'source': 'auto_trading'
            })
    
    # Check if this is a Zerodha tradingsymbol format
    if app_state.get('zerodha_connected') and app_state.get('kite'):
        try:
            # Get Zerodha positions and check if any match the symbol
            positions = app_state['kite'].positions()
            net_positions = positions['net']
            
            for pos in net_positions:
                if pos['tradingsymbol'] == symbol and int(pos['quantity']) > 0:
                    # For Zerodha positions, we don't have stop loss data in the API
                    # Return a placeholder or calculate based on some logic
                    # You could implement your own stop loss logic here
                    return jsonify({
                        'success': True,
                        'symbol': symbol,
                        'stop_loss': None,  # No stop loss data available from Zerodha API
                        'source': 'zerodha',
                        'message': 'Stop loss not available for Zerodha positions via API'
                    })
        except Exception as e:
            print(f"Error checking Zerodha positions for stop loss: {e}")
    
    return jsonify({'success': False, 'symbol': symbol, 'stop_loss': None})

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if username == VALID_USERNAME and password == VALID_PASSWORD:
        session_token = str(uuid.uuid4())
        set_active_session(username, session_token)
        session['logged_in'] = True
        session['username'] = username
        session['session_token'] = session_token
        
        # Initialize TrueData after successful login
        initialize_truedata()
        
        # Initialize Kite Connect if configured
        initialize_kite()
        
        return jsonify({'success': True, 'token': session_token})
    else:
        return jsonify({'success': False, 'message': 'Invalid credentials'})

@app.route('/logout', methods=['POST'])
def logout():
    clear_active_session()
    session.clear()
    return jsonify({'success': True})

@app.route('/api/market-status')
def api_market_status():
    return jsonify(get_market_status())

# Zerodha Kite Connect API Routes
@app.route('/api/zerodha/login')
def api_zerodha_login():
    """Redirect to Zerodha login URL"""
    if not KITE_CONFIG['api_key'] or KITE_CONFIG['api_key'] == 'your_zerodha_api_key_here':
        return f"""
        <html>
        <head><title>Zerodha Login - Configuration Required</title></head>
        <body style="font-family: Arial; padding: 20px; background: #f5f5f5;">
            <div style="max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                <h2 style="color: #d32f2f;">❌ Zerodha API Configuration Required</h2>
                <p>Before you can connect to Zerodha, you need to configure your API credentials:</p>
                <ol>
                    <li>Get your API key and secret from <a href="https://developers.zerodha.trade/" target="_blank">Zerodha Developer Console</a></li>
                    <li>Add them to the <code>KITE_CONFIG</code> in your <code>app.py</code> file</li>
                    <li>Restart the application</li>
                    <li>Then try connecting to Zerodha again</li>
                </ol>
                <p><a href="/" style="background: #1976d2; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">← Back to Dashboard</a></p>
            </div>
        </body>
        </html>
        """
    
    try:
        kite = KiteConnect(api_key=KITE_CONFIG['api_key'])
        login_url = kite.login_url()
        return redirect(login_url)
    except Exception as e:
        return f"""
        <html>
        <head><title>Zerodha Login Error</title></head>
        <body style="font-family: Arial; padding: 20px; background: #f5f5f5;">
            <div style="max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                <h2 style="color: #d32f2f;">❌ Zerodha Login Error</h2>
                <p><strong>Error:</strong> {str(e)}</p>
                <p>Please check your API configuration and try again.</p>
                <p><a href="/" style="background: #1976d2; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">← Back to Dashboard</a></p>
            </div>
        </body>
        </html>
        """

@app.route('/api/zerodha/login-url')
def api_zerodha_login_url():
    """Get Zerodha login URL"""
    if not KITE_CONFIG['api_key']:
        return jsonify({'success': False, 'message': 'Zerodha API key not configured'})
    
    try:
        kite = KiteConnect(api_key=KITE_CONFIG['api_key'])
        login_url = kite.login_url()
        return jsonify({'success': True, 'login_url': login_url})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/zerodha/callback')
def api_zerodha_callback():
    """Handle Zerodha login callback with enhanced error handling"""
    request_token = request.args.get('request_token')
    
    if not request_token:
        return f"""
        <html>
        <head><title>Zerodha Login Failed</title></head>
        <body style="font-family: Arial; padding: 20px; background: #f5f5f5;">
            <div style="max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px;">
                <h2 style="color: #d32f2f;">❌ Zerodha Login Failed</h2>
                <p><strong>Error:</strong> Request token not received</p>
                <p><strong>Possible causes:</strong></p>
                <ul>
                    <li>Login was cancelled or timed out</li>
                    <li>2FA verification failed</li>
                    <li>Network connectivity issue</li>
                </ul>
                <p><strong>Solutions:</strong></p>
                <ol>
                    <li>Check your internet connection</li>
                    <li>Clear browser cache and cookies</li>
                    <li>Try logging in again</li>
                    <li>Make sure you complete 2FA verification</li>
                </ol>
                <p><a href="/api/zerodha/login" style="background: #1976d2; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">🔄 Try Again</a></p>
                <p><a href="/" style="background: #666; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">← Back to Dashboard</a></p>
            </div>
        </body>
        </html>
        """
    
    try:
        print(f"🔑 Processing Zerodha callback with request_token: {request_token[:10]}...")
        
        # Create new KiteConnect instance
        kite = KiteConnect(api_key=KITE_CONFIG['api_key'])
        
        # Generate session with detailed error handling
        try:
            data = kite.generate_session(request_token, api_secret=KITE_CONFIG['api_secret'])
            print(f"✅ Session generated successfully")
            print(f"📊 User ID: {data.get('user_id', 'Unknown')}")
            print(f"🔑 Access Token: {data['access_token'][:20]}...")
            
        except Exception as session_error:
            print(f"❌ Session generation failed: {session_error}")
            
            # Handle specific error types
            error_message = str(session_error).lower()
            
            if "invalid" in error_message and "session" in error_message:
                solution = """
                <h3>🔧 Session Expired Solution:</h3>
                <ol>
                    <li><strong>Clear browser data:</strong> Ctrl+Shift+Delete → Clear all cookies</li>
                    <li><strong>Close all browser tabs</strong> related to Zerodha</li>
                    <li><strong>Wait 2-3 minutes</strong> for session to fully clear</li>
                    <li><strong>Try fresh login</strong> with new browser session</li>
                </ol>
                """
            elif "expired" in error_message:
                solution = """
                <h3>⏰ Token Expired Solution:</h3>
                <ol>
                    <li><strong>Login process took too long</strong> (>5 minutes)</li>
                    <li><strong>Start fresh login</strong> and complete within 3 minutes</li>
                    <li><strong>Complete 2FA quickly</strong> when prompted</li>
                </ol>
                """
            elif "2fa" in error_message or "otp" in error_message:
                solution = """
                <h3>📱 2FA Issue Solution:</h3>
                <ol>
                    <li><strong>Check OTP app</strong> for correct code</li>
                    <li><strong>Ensure time sync</strong> on phone and computer</li>
                    <li><strong>Try backup OTP codes</strong> if available</li>
                </ol>
                """
            else:
                solution = f"""
                <h3>🔍 General Error Solution:</h3>
                <p><strong>Error details:</strong> {session_error}</p>
                <ol>
                    <li><strong>Check API credentials</strong> in app.py</li>
                    <li><strong>Verify Zerodha account</strong> is active</li>
                    <li><strong>Contact support</strong> if problem persists</li>
                </ol>
                """
            
            return f"""
            <html>
            <head><title>Zerodha Session Error</title></head>
            <body style="font-family: Arial; padding: 20px; background: #f5f5f5;">
                <div style="max-width: 700px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px;">
                    <h2 style="color: #d32f2f;">❌ Session Generation Failed</h2>
                    <p><strong>Error:</strong> {session_error}</p>
                    {solution}
                    <div style="margin-top: 30px; text-align: center;">
                        <a href="/api/zerodha/login" style="background: #4caf50; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; margin: 5px;">🔄 Try Fresh Login</a>
                        <a href="/" style="background: #666; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; margin: 5px;">← Back to Dashboard</a>
                    </div>
                </div>
            </body>
            </html>
            """
        
        # Store tokens securely
        KITE_CONFIG['access_token'] = data['access_token']
        KITE_CONFIG['request_token'] = request_token
        
        # Update app state
        app_state['kite'] = kite
        kite.set_access_token(data['access_token'])
        app_state['zerodha_connected'] = True
        
        # Verify connection by testing API
        try:
            profile = kite.profile()
            user_name = profile.get('user_name', profile.get('user_id', 'User'))
            print(f"✅ Connection verified for user: {user_name}")
            
            # Test funds access
            funds = kite.margins("equity")
            available_cash = funds['available']['cash']
            print(f"💰 Available cash: ₹{available_cash:,.2f}")
            
        except Exception as verify_error:
            print(f"⚠️ Connection verification failed: {verify_error}")
            user_name = "User"
            available_cash = 0
        
        # Success page with detailed info
        return f"""
        <html>
        <head>
            <title>Zerodha Login Successful</title>
            <script>
                // Auto-refresh parent window and close popup
                window.onload = function() {{
                    setTimeout(function() {{
                        if (window.opener) {{
                            window.opener.location.reload();
                        }}
                        window.close();
                    }}, 4000);
                }}
            </script>
        </head>
        <body style="font-family: Arial; padding: 20px; background: #f5f5f5;">
            <div style="max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                <h2 style="color: #4caf50;">✅ Zerodha Login Successful!</h2>
                
                <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 15px 0;">
                    <p><strong>👤 User:</strong> {user_name}</p>
                    <p><strong>🔑 Access Token:</strong> {data['access_token'][:25]}...</p>
                    <p><strong>💰 Available Cash:</strong> ₹{available_cash:,.2f}</p>
                    <p><strong>🕒 Connected At:</strong> {dt.now().strftime('%H:%M:%S')}</p>
                </div>
                
                <div style="background: #e8f5e8; padding: 15px; border-radius: 5px; margin: 15px 0;">
                    <h4 style="color: #2e7d32; margin-top: 0;">🚀 Ready for Live Trading!</h4>
                    <ul style="margin: 10px 0; color: #2e7d32;">
                        <li>✅ Real money trading enabled</li>
                        <li>✅ Auto trading system active</li>
                        <li>✅ Live option chain data</li>
                        <li>✅ Position tracking enabled</li>
                    </ul>
                </div>
                
                <p style="color: #666; font-size: 14px; text-align: center;">This window will close automatically in 4 seconds...</p>
                
                <div style="text-align: center; margin-top: 20px;">
                    <a href="/" style="background: #4caf50; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px;">Continue to Dashboard</a>
                </div>
            </div>
        </body>
        </html>
        """
        
    except Exception as e:
        error_details = str(e)
        print(f"❌ Callback processing failed: {error_details}")
        
        return f"""
        <html>
        <head><title>Zerodha Login Error</title></head>
        <body style="font-family: Arial; padding: 20px; background: #f5f5f5;">
            <div style="max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px;">
                <h2 style="color: #d32f2f;">❌ Login Processing Error</h2>
                <p><strong>Technical Error:</strong> {error_details}</p>
                
                <div style="background: #fff3cd; padding: 15px; border-radius: 5px; margin: 15px 0;">
                    <h4>🔧 Troubleshooting Steps:</h4>
                    <ol>
                        <li><strong>Check app.py configuration:</strong>
                            <ul>
                                <li>API Key: {KITE_CONFIG['api_key'][:10]}...</li>
                                <li>API Secret: {'✅ Configured' if KITE_CONFIG['api_secret'] else '❌ Missing'}</li>
                            </ul>
                        </li>
                        <li><strong>Verify network connection</strong></li>
                        <li><strong>Check Zerodha server status</strong></li>
                        <li><strong>Try fresh login after 2-3 minutes</strong></li>
                    </ol>
                </div>
                
                <div style="text-align: center; margin-top: 20px;">
                    <a href="/api/zerodha/login" style="background: #4caf50; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; margin: 5px;">🔄 Try Again</a>
                    <a href="/" style="background: #666; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; margin: 5px;">← Dashboard</a>
                </div>
            </div>
        </body>
        </html>
        """

# Add session recovery endpoint
@app.route('/api/zerodha/refresh-session', methods=['POST'])
def api_zerodha_refresh_session():
    """Refresh Zerodha session if expired"""
    try:
        if not KITE_CONFIG['access_token']:
            return jsonify({
                'success': False,
                'message': 'No access token available. Please login first.',
                'action': 'login_required'
            })
        
        # Test current session
        if app_state['kite']:
            try:
                profile = app_state['kite'].profile()
                return jsonify({
                    'success': True,
                    'message': f'Session active for {profile.get("user_name", "User")}',
                    'action': 'session_valid'
                })
            except Exception as e:
                if "session" in str(e).lower() or "invalid" in str(e).lower():
                    # Clear expired tokens
                    KITE_CONFIG['access_token'] = ''
                    app_state['zerodha_connected'] = False
                    app_state['kite'] = None
                    
                    return jsonify({
                        'success': False,
                        'message': 'Session expired. Please login again.',
                        'action': 'login_required'
                    })
                else:
                    return jsonify({
                        'success': False,
                        'message': f'Connection error: {str(e)}',
                        'action': 'retry'
                    })
        
        return jsonify({
            'success': False,
            'message': 'Kite Connect not initialized',
            'action': 'login_required'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Refresh failed: {str(e)}',
            'action': 'login_required'
        })

@app.route('/api/zerodha/funds')
def api_zerodha_funds():
    """Get Zerodha account funds"""
    if not app_state['kite']:
        return jsonify({'success': False, 'message': 'Zerodha not connected'})
    
    try:
        funds = app_state['kite'].margins("equity")
        app_state['zerodha_funds'] = funds['available']['cash']
        return jsonify({
            'success': True,
            'funds': funds['available'],
            'cash': funds['available']['cash'],
            'margins_used': funds['utilised'],
            'margins_available': funds['net']
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/zerodha/positions')
def api_zerodha_positions():
    """Get Zerodha positions"""
    if not app_state['kite']:
        return jsonify({'success': False, 'message': 'Zerodha not connected'})
    
    try:
        positions = app_state['kite'].positions()
        app_state['zerodha_positions'] = positions['net']
        return jsonify({
            'success': True,
            'net_positions': positions['net'],
            'day_positions': positions['day']
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/zerodha/orders')
def api_zerodha_orders():
    """Get Zerodha order book"""
    if not app_state['kite']:
        return jsonify({'success': False, 'message': 'Zerodha not connected'})
    
    try:
        orders = app_state['kite'].orders()
        app_state['zerodha_orders'] = orders
        return jsonify({'success': True, 'orders': orders})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/zerodha/place-order', methods=['POST'])
def api_zerodha_place_order():
    """Place order through Zerodha"""
    if not app_state['kite']:
        return jsonify({'success': False, 'message': 'Zerodha not connected'})
    
    data = request.get_json()
    try:
        order_id = app_state['kite'].place_order(
            variety=app_state['kite'].VARIETY_REGULAR,
            exchange=data.get('exchange', app_state['kite'].EXCHANGE_NSE),
            tradingsymbol=data.get('tradingsymbol'),
            transaction_type=data.get('transaction_type', 'BUY'),  # BUY or SELL
            quantity=data.get('quantity'),
            order_type=data.get('order_type', app_state['kite'].ORDER_TYPE_MARKET),
            product=data.get('product', app_state['kite'].PRODUCT_MIS),
            price=data.get('price', 0),
            trigger_price=data.get('trigger_price', 0)
        )
        return jsonify({'success': True, 'order_id': order_id})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/zerodha/status')
def api_zerodha_status():
    """Check Zerodha connection status"""
    print(f"[DEBUG] /api/zerodha/status called")
    print(f"[DEBUG] KITE_CONFIG['access_token']: {KITE_CONFIG['access_token'][:10]}..." if KITE_CONFIG['access_token'] else "[DEBUG] No access_token set")
    print(f"[DEBUG] app_state['kite']: {type(app_state['kite']).__name__ if app_state['kite'] else 'None'}")
    is_connected, message = check_zerodha_connection()
    status = {
        'connected': is_connected,
        'api_key_configured': bool(KITE_CONFIG['api_key']) and KITE_CONFIG['api_key'] != 'your_zerodha_api_key_here',
        'api_secret_configured': bool(KITE_CONFIG['api_secret']) and KITE_CONFIG['api_secret'] != 'your_zerodha_api_secret_here',
        'access_token_available': bool(KITE_CONFIG['access_token']),
        'message': message,
        'trading_enabled': is_connected
    }
    print(f"[DEBUG] Zerodha status response: {status}")
    return jsonify(status)

# Test route for manual token processing
@app.route('/test-token')
def test_token():
    token = "gPpTg4ZDz2mCI5ZETCBkIe4zkHz1nFlR"
    return f'''
    <h2>Test Zerodha Token</h2>
    <p>Your token: {token}</p>
    <p><a href="/?request_token={token}&status=success">Test with Root Route</a></p>
    <p><a href="/api/zerodha/callback?request_token={token}">Test with Callback Route</a></p>
    <p><a href="/">Back to Dashboard</a></p>
    '''

@app.route('/api/wallet-info')
def api_wallet_info():
    """Get wallet info from Zerodha account"""
    print(f"[DEBUG] /api/wallet-info called")
    print(f"[DEBUG] KITE_CONFIG['access_token']: {KITE_CONFIG['access_token'][:10]}..." if KITE_CONFIG['access_token'] else "[DEBUG] No access_token set")
    print(f"[DEBUG] app_state['kite']: {type(app_state['kite']).__name__ if app_state['kite'] else 'None'}")
    # Check Zerodha connection
    is_connected, message = check_zerodha_connection()
    if not is_connected:
        print(f"[DEBUG] Zerodha not connected: {message}")
        return jsonify({
            'success': False,
            'message': f'Zerodha not connected: {message}',
            'zerodha_connected': False,
            'total_positions': 0,
            'waiting_positions': 0
        })
    try:
        # Get funds from Zerodha - Enhanced debugging
        print(f"[DEBUG] Fetching funds from Zerodha...")
        funds = app_state['kite'].margins("equity")
        print(f"[DEBUG] Raw funds response: {funds}")
        
        # Try different cash fields
        available_cash = funds.get('available', {}).get('cash', 0)
        opening_balance = funds.get('available', {}).get('opening_balance', 0)
        live_balance = funds.get('available', {}).get('live_balance', 0)
        
        print(f"[DEBUG] Cash fields - available_cash: {available_cash}, opening_balance: {opening_balance}, live_balance: {live_balance}")
        
        # Use the highest available value
        balance_to_show = max(available_cash, opening_balance, live_balance)
        print(f"[DEBUG] Balance to show: {balance_to_show}")
        
        # Get positions from Zerodha
        print(f"[DEBUG] Fetching positions from Zerodha...")
        positions = app_state['kite'].positions()
        net_positions = positions['net']
        day_positions = positions['day']
        print(f"Net positions: {len(net_positions)}")
        print(f"Day positions: {len(day_positions)}")
        
        # Calculate portfolio metrics
        total_invested = sum([float(pos['average_price']) * int(pos['quantity']) 
                             for pos in net_positions if int(pos['quantity']) != 0])
        current_value = sum([float(pos['last_price']) * int(pos['quantity']) 
                            for pos in net_positions if int(pos['quantity']) != 0])
        unrealized_pnl = sum([float(pos['unrealised']) for pos in net_positions])
        realized_pnl = sum([float(pos['realised']) for pos in net_positions])
        total_positions = len([pos for pos in net_positions if int(pos['quantity']) != 0])
        # If you have a way to determine waiting positions, set it here. Otherwise, set to 0.
        waiting_positions = 0
        wallet_info = {
            'success': True,
            'balance': balance_to_show,
            'available_cash': available_cash,
            'opening_balance': opening_balance,
            'live_balance': live_balance,
            'invested': total_invested,
            'current_value': current_value,
            'unrealized_pnl': unrealized_pnl,
            'realized_pnl': realized_pnl,
            'total_positions': total_positions,
            'waiting_positions': waiting_positions,
            'net_pnl': realized_pnl + unrealized_pnl,
            'zerodha_connected': True,
            'zerodha_funds': funds
        }
        print(f"[DEBUG] Wallet info response: {wallet_info}")
        return jsonify(wallet_info)
    except Exception as e:
        print(f"[DEBUG] Error fetching Zerodha data: {e}")
        return jsonify({
            'success': False,
            'message': f'Error fetching Zerodha data: {str(e)}',
            'zerodha_connected': False,
            'total_positions': 0,
            'waiting_positions': 0
        })

@app.route('/api/symbols')
def api_symbols():
    return jsonify(list(LOT_SIZES.keys()))

@app.route('/api/expiry-list/<symbol>')
def api_expiry_list(symbol):
    """Fetch expiry dates for a given symbol using TrueData API"""
    expiry_url = f"https://history.truedata.in/getSymbolExpiryList?symbol={symbol}&response=csv"
    headers = {
        "accept": "application/json",
        "authorization": "Bearer 1msFWl8vjURgbrKUfs04wmNYo5RUdmh3fck3Vjd5BNQoAVO039mVwRoX-OIZxXvaZj4_C3SPQbUTr1uINnr_CKjDWIC5DPNY1D4xbAey67JYM3LYhpR6dNxYxooIntl3J2_BuBJc9WqyiO-tqtRS0nm2qiU_9yRLO0F8EW9iDC_XM3uamX8tShXPVALU_-kMLHTN4hrSk-jEJTXoCE8D9jwJjnV25Eaa7_Ka0_ktHhCukRZCXmGhs_CBgKazXObvtEohlH5UrEkV-seOb27tfw"
    }
    
    try:
        response = requests.get(expiry_url, headers=headers)
        print(f"TrueData API Response Status: {response.status_code}")
        
        if response.status_code == 200:
            expiry_list = response.text.strip().split('\n')[1:]  # skip header row
            expiry_list = [x.strip() for x in expiry_list if x.strip()]
            print(f"Raw expiry list: {expiry_list[:3]}")  # Show first 3 entries
            
            # Parse expiry dates to standardized format
            parsed_expiries = []
            for exp_str in expiry_list:
                try:
                    if '-' in exp_str:
                        parsed = dt.strptime(exp_str, '%Y-%m-%d').date()
                    elif len(exp_str) == 8:
                        parsed = dt.strptime(exp_str, '%Y%m%d').date()
                    else:
                        parsed = dt.strptime(exp_str, '%d-%b-%Y').date()
                    
                    # Convert to string format for frontend
                    parsed_expiries.append({
                        'value': parsed.strftime('%Y-%m-%d'),
                        'display': parsed.strftime('%d %b %Y')
                    })
                except Exception as parse_error:
                    print(f"Failed to parse expiry date '{exp_str}': {parse_error}")
                    continue
            
            # Sort by date
            parsed_expiries.sort(key=lambda x: x['value'])
            print(f"Parsed expiries count: {len(parsed_expiries)}")
            print(f"First parsed expiry: {parsed_expiries[0] if parsed_expiries else 'None'}")
            
            return jsonify(parsed_expiries)
        else:
            print(f"Error fetching expiry list: HTTP {response.status_code}")
            print(f"Response text: {response.text[:200]}")
            # Fallback to static expiry dates if API fails
            return get_fallback_expiry_dates()
    except Exception as e:
        print(f"Exception fetching expiry list: {str(e)}")
        # Fallback to static expiry dates if API fails
        return get_fallback_expiry_dates()

def get_fallback_expiry_dates():
    """Provide fallback expiry dates when TrueData API is not available"""
    import datetime
    today = datetime.date.today()
    
    # Generate next few Thursdays (typical expiry days)
    expiry_dates = []
    current_date = today
    
    # Find next Thursday
    while current_date.weekday() != 3:  # 3 = Thursday
        current_date += datetime.timedelta(days=1)
    
    # Add next 8 Thursdays
    for i in range(8):
        expiry_dates.append({
            'value': current_date.strftime('%Y-%m-%d'),
            'display': current_date.strftime('%d %b %Y')
        })
        current_date += datetime.timedelta(days=7)  # Next Thursday
    
    print(f"Using fallback expiry dates: {len(expiry_dates)} dates generated")
    return jsonify(expiry_dates)

@app.route('/api/start-option-chain', methods=['POST'])
def api_start_option_chain():
    data = request.get_json()
    symbol = data.get('symbol')
    expiry = data.get('expiry')
    
    if not symbol or not expiry:
        return jsonify({'success': False, 'message': 'Symbol and expiry required'})
    
    try:
        # Parse expiry date
        if '-' in expiry:
            expiry_datetime = dt.strptime(expiry, '%Y-%m-%d')
        elif len(expiry) == 8:
            expiry_datetime = dt.strptime(expiry, '%Y%m%d')
        else:
            expiry_datetime = dt.strptime(expiry, '%d-%b-%Y')
        
        key = f"{symbol}_{expiry}"
        
        # Stop previous option chain if exists
        if app_state['option_chain_obj'] and hasattr(app_state['option_chain_obj'], 'stop'):
            try:
                app_state['option_chain_obj'].stop()
            except Exception:
                pass
        
        # Initialize TrueData if not already done
        if app_state['td_obj'] is None:
            initialize_truedata()
        
        # Start new option chain
        if app_state['td_obj']:
            app_state['option_chain_obj'] = app_state['td_obj'].start_option_chain(
                symbol, expiry=expiry_datetime, chain_length=10, bid_ask=True, greek=True
            )
            app_state['last_key'] = key
            print(f"Option chain started for {symbol} expiry {expiry}")
            return jsonify({'success': True, 'message': f'Started option chain for {symbol}'})
        else:
            return jsonify({'success': False, 'message': 'TrueData client not initialized'})
    except Exception as e:
        print(f"Error starting option chain: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/option-chain-data')
def api_option_chain_data():
    if not app_state['option_chain_obj']:
        return jsonify({'success': False, 'message': 'No option chain active'})
    
    try:
        df_chain = app_state['option_chain_obj'].get_option_chain()
        if df_chain.empty:
            return jsonify({'success': False, 'message': 'No data available'})
        
        print(f"Option chain columns: {df_chain.columns.tolist()}")
        print(f"Option chain shape: {df_chain.shape}")
        print(f"Sample data:\n{df_chain.head(2)}")
        
        # Map TrueData column names to standard names
        column_mapping = {
            'ltp': 'ltp',
            'bid': 'bid',
            'ask': 'ask',
            'strike': 'strike',
            'type': 'option_type',
            'volume': 'volume',
            'oi': 'oi',
            'price_change': 'change',
            'price_change_perc': 'change_percent'
        }
        
        # Apply column mapping
        for old_col, new_col in column_mapping.items():
            if old_col in df_chain.columns and old_col != new_col:
                df_chain[new_col] = df_chain[old_col]
        
        # Process option type from 'type' column
        if 'type' in df_chain.columns:
            def map_type(val):
                v = str(val).upper()
                if 'CE' in v or 'CALL' in v:
                    return 'CE'
                elif 'PE' in v or 'PUT' in v:
                    return 'PE'
                else:
                    return 'UNK'
            df_chain['option_type'] = df_chain['type'].apply(map_type)
        else:
            # Fallback: extract from symbol index
            df_chain['option_type'] = df_chain.index.to_series().apply(extract_option_type)
        
        df_chain['strike'] = pd.to_numeric(df_chain['strike'], errors='coerce')
        df_chain = df_chain.infer_objects(copy=False).fillna(0)
        
        # Get underlying value
        underlying = None
        if 'underlying_value' in df_chain.columns:
            underlying = df_chain.iloc[0]['underlying_value']
        
        if underlying is None or underlying == 0:
            mid_index = len(df_chain) // 2
            underlying = df_chain.iloc[mid_index]['strike'] if not df_chain.empty else None
        
        # Find ATM strike
        atm_strike = None
        if underlying is not None:
            df_chain['strike_diff'] = abs(df_chain['strike'] - underlying)
            atm_strike = df_chain.loc[df_chain['strike_diff'].idxmin(), 'strike']
        
        # Split into calls and puts
        if atm_strike is not None:
            call_strikes = df_chain[df_chain['strike'] <= atm_strike]['strike'].unique()
            calls = df_chain[
                (df_chain['option_type'] == 'CE') & 
                (df_chain['strike'].isin(call_strikes))
            ].sort_values('strike', ascending=False)
            
            put_strikes = df_chain[df_chain['strike'] >= atm_strike]['strike'].unique()
            puts = df_chain[
                (df_chain['option_type'] == 'PE') & 
                (df_chain['strike'].isin(put_strikes))
            ].sort_values('strike')
            
            atm = df_chain[df_chain['strike'] == atm_strike]
        else:
            calls = df_chain[df_chain['option_type'] == 'CE'].sort_values('strike')
            puts = df_chain[df_chain['option_type'] == 'PE'].sort_values('strike')
            atm = pd.DataFrame()
        
        # Convert to JSON-serializable format with proper type conversion
        def convert_df_to_records(df):
            records = []
            for idx, row in df.iterrows():
                record = {}
                for col in df.columns:
                    val = row[col]
                    if pd.isna(val):
                        record[col] = 0
                    elif isinstance(val, (np.integer, np.floating)):
                        record[col] = float(val)
                    else:
                        record[col] = val
                
                # Ensure we have all required fields for frontend
                record['ltp'] = record.get('ltp', 0)
                record['bid'] = record.get('bid', 0)
                record['ask'] = record.get('ask', 0)
                record['strike'] = record.get('strike', 0)
                record['option_type'] = record.get('option_type', 'UNK')
                record['volume'] = record.get('volume', 0)
                record['oi'] = record.get('oi', 0)
                record['change'] = record.get('change', 0)
                record['change_percent'] = record.get('change_percent', 0)
                
                # Add symbol for frontend identification (use the index value)
                record['symbol'] = str(idx) if idx is not None else f"{record['strike']}{record['option_type']}"
                
                records.append(record)
            return records
        
        result = {
            'success': True,
            'underlying': float(underlying) if underlying else None,
            'atm_strike': float(atm_strike) if atm_strike else None,
            'calls': convert_df_to_records(calls.head(5)),
            'puts': convert_df_to_records(puts.head(5)),
            'atm': convert_df_to_records(atm),
            'total_options': len(df_chain),
            'ce_count': len(df_chain[df_chain['option_type'] == 'CE']),
            'pe_count': len(df_chain[df_chain['option_type'] == 'PE'])
        }
        
        # Store current data for other endpoints
        app_state['current_option_data'] = result
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/buy-option', methods=['POST'])
def api_buy_option():
    """Buy option through Zerodha (LIVE trading only)"""
    # Check Zerodha connection first
    is_connected = app_state['zerodha_connected']
    if not is_connected:
        return jsonify({
            'success': False, 
            'message': f'Cannot trade: Zerodha not connected. Please complete Zerodha login first.'
        })
    
    data = request.get_json()
    strike = float(data.get('strike'))
    option_type = data.get('option_type')
    price = float(data.get('price'))
    lots = int(data.get('lots', 1))
    symbol = data.get('symbol', 'NIFTY')
    expiry = data.get('expiry', '')
    
    # Handle expiry - ensure it's a string
    if isinstance(expiry, dict):
        expiry = expiry.get('value', '') if expiry else ''
    elif not isinstance(expiry, str):
        expiry = str(expiry) if expiry else ''
    
    # Convert expiry from YYYY-MM-DD to YYMMDD for TrueData format
    try:
        if '-' in expiry:  # Format: "2025-08-07"
            year, month, day = expiry.split('-')
            # Take last 2 digits of year
            yy = year[-2:]
            expiry_td = f"{yy}{month}{day}"  # "250807"
        else:
            expiry_td = expiry
    except Exception as e:
        print(f"[ERROR] Failed to parse expiry date {expiry}: {e}")
        return jsonify({
            "success": False,
            "message": f"❌ Invalid expiry date format: {expiry}",
            "error": f"Expected format: YYYY-MM-DD"
        }), 400
    
    # Build TrueData symbol and convert to Zerodha format
    td_symbol = f"{symbol}{expiry_td}{int(strike)}{option_type}"
    print(f"[DEBUG] Built TrueData symbol: {td_symbol}")
    
    tradingsymbol = td_to_zerodha_symbol(td_symbol)
    if not tradingsymbol:
        print(f"[ERROR] Could not convert TrueData symbol: {td_symbol}")
        return jsonify({
            "success": False,
            "message": f"❌ Trading Symbol conversion failed for: {td_symbol}. Please check expiry, strike, and option type.",
            "error": f"❌ Trading Symbol not found in Zerodha for {td_symbol}"
        }), 400
    
    lot_size = LOT_SIZES.get(symbol, 75)
    total_qty = lot_size * lots
    try:
        order_id = app_state['kite'].place_order(
            variety=app_state['kite'].VARIETY_REGULAR,
            exchange=app_state['kite'].EXCHANGE_NFO,
            tradingsymbol=tradingsymbol,
            transaction_type=app_state['kite'].TRANSACTION_TYPE_BUY,
            quantity=total_qty,
            order_type=app_state['kite'].ORDER_TYPE_MARKET,
            product=app_state['kite'].PRODUCT_MIS
        )
        
        # Record trade in local tracking
        app_state['trade_history'].append({
            'action': 'Buy (LIVE)',
            'type': option_type,
            'strike': strike,
            'qty': total_qty,
            'price': price,
            'pnl': 0,
            'order_id': order_id,
            'tradingsymbol': tradingsymbol,
            'time': dt.now().strftime('%Y-%m-%d %H:%M:%S')
        })

        
        # Add bought option to auto_trading positions for automatic stop loss
        position = create_auto_position(strike, option_type, price, total_qty, symbol, expiry)
        print(f"🤖 AUTO TRADING: Added position {strike} {option_type} with stop loss at ₹{position['stop_loss_price']}")
        
        return jsonify({
            'success': True,
            'message': f'✅ Order placed: {total_qty} {option_type} @ Market Price',
            'order_id': order_id,
            'tradingsymbol': tradingsymbol
        })
    except Exception as e:
        error_msg = str(e)
        print(f"[DEBUG] Order placement failed: {error_msg}")
        if "expired or does not exist" in error_msg:
            return jsonify({
                'success': False,
                'message': f'❌ Trading Symbol Error: {tradingsymbol} not found on Zerodha. This could mean:\n' +
                          f'• The expiry date {expiry} may not have options\n' +
                          f'• The strike {strike} may not be available\n' +
                          f'• The symbol format may be incorrect\n' +
                          f'Please check option chain for valid strikes and expiries.'
            })
        else:
            return jsonify({
                'success': False,
                'message': f'❌ Order failed: {error_msg}'
            })

@app.route('/api/sell-option', methods=['POST'])
def api_sell_option():
    """Sell option through Zerodha (LIVE trading only)"""
    # Check Zerodha connection first
    is_connected = app_state['zerodha_connected']
    if not is_connected:
        return jsonify({
            'success': False, 
            'message': f'Cannot trade: Zerodha not connected. Please complete Zerodha login first.'
        })
    
    data = request.get_json()
    strike = float(data.get('strike'))
    option_type = data.get('option_type')
    price = float(data.get('price'))
    symbol = data.get('symbol', 'NIFTY')
    expiry = data.get('expiry', '')
    
    # Handle expiry - ensure it's a string
    if isinstance(expiry, dict):
        expiry = expiry.get('value', '') if expiry else ''
    elif not isinstance(expiry, str):
        expiry = str(expiry) if expiry else ''
    
    # Convert expiry from YYYY-MM-DD to YYMMDD for TrueData format
    try:
        if '-' in expiry:  # Format: "2025-08-07"
            year, month, day = expiry.split('-')
            # Take last 2 digits of year
            yy = year[-2:]
            expiry_td = f"{yy}{month}{day}"  # "250807"
        else:
            expiry_td = expiry
    except Exception as e:
        print(f"[ERROR] Failed to parse expiry date {expiry}: {e}")
        return jsonify({
            "success": False,
            "message": f"❌ Invalid expiry date format: {expiry}",
            "error": f"Expected format: YYYY-MM-DD"
        }), 400
    
    # Build TrueData symbol and convert to Zerodha format
    td_symbol = f"{symbol}{expiry_td}{int(strike)}{option_type}"
    print(f"[DEBUG] Built TrueData symbol: {td_symbol}")
    
    tradingsymbol = td_to_zerodha_symbol(td_symbol)
    if not tradingsymbol:
        return jsonify({"error": f"❌ Trading Symbol not found in Zerodha for {td_symbol}"}), 400
    
    try:
        positions = app_state['kite'].positions()
        net_positions = positions['net']
        
        position_found = None
        for pos in net_positions:
            if (pos['tradingsymbol'] == tradingsymbol and int(pos['quantity']) > 0):
                position_found = pos
                break
        
        if not position_found:
            return jsonify({
                'success': False,
                'message': f'No position found for {tradingsymbol}'
            })
        
        quantity = int(position_found['quantity'])
        
        # Place sell order through Zerodha
        order_id = app_state['kite'].place_order(
            variety=app_state['kite'].VARIETY_REGULAR,
            exchange=app_state['kite'].EXCHANGE_NFO,
            tradingsymbol=tradingsymbol,
            transaction_type=app_state['kite'].TRANSACTION_TYPE_SELL,
            quantity=quantity,
            order_type=app_state['kite'].ORDER_TYPE_MARKET,
            product=app_state['kite'].PRODUCT_MIS
        )
        
        # Record trade in local tracking
        pnl = float(position_found['unrealised'])
        
        app_state['trade_history'].append({
            'action': 'Sell (LIVE)',
            'type': option_type,
            'strike': strike,
            'qty': quantity,
            'price': price,
            'pnl': pnl,
            'order_id': order_id,
            'tradingsymbol': tradingsymbol,
            'time': dt.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        
        # 🔥 IMPORTANT: Completely remove auto position to prevent auto buy after manual sell
        removed_count = execute_manual_sell_auto_position(strike, option_type, symbol)
        
        success_message = f'✅ Sell order placed: {quantity} {option_type} @ Market Price'
        if removed_count > 0:
            success_message += f' | Auto position completely removed - NO AUTO BUY will trigger'
        
        return jsonify({
            'success': True, 
            'message': success_message,
            'order_id': order_id,
            'pnl': pnl,
            'auto_positions_removed': removed_count
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'❌ Sell order failed: {str(e)}'
        })

@app.route('/api/positions')
def api_positions():
    """Get positions from Zerodha account"""
    # Check Zerodha connection
    is_connected, message = check_zerodha_connection()
    if not is_connected:
        return jsonify({
            'success': False,
            'message': f'Zerodha not connected: {message}',
            'positions': []
        })
    
    try:
        # Get positions from Zerodha
        positions = app_state['kite'].positions()
        net_positions = positions['net']
        print(f"[DEBUG] Raw net_positions: {net_positions}")
        # Show all positions, not just those with quantity > 0
        all_positions = []
        for pos in net_positions:
            print(f"[DEBUG] Checking position: {pos['tradingsymbol']} qty={pos['quantity']}")
            position_data = {
                'tradingsymbol': pos['tradingsymbol'],
                'quantity': int(pos['quantity']),
                'average_price': float(pos['average_price']),
                'last_price': float(pos['last_price']),
                'pnl': float(pos['unrealised']),
                'realized_pnl': float(pos['realised']),
                'instrument_token': pos['instrument_token'],
                'exchange': pos['exchange'],
                'product': pos['product']
            }
            all_positions.append(position_data)
        print(f"[DEBUG] Returning {len(all_positions)} positions.")
        return jsonify({
            'success': True,
            'positions': all_positions,
            'total_positions': len(all_positions)
        })
    except Exception as e:
        print(f"[DEBUG] Error fetching positions: {e}")
        return jsonify({
            'success': False,
            'message': f'Error fetching positions: {str(e)}',
            'positions': []
        })

@app.route('/api/trade-history')
def api_trade_history():
    return jsonify(app_state['trade_history'][-20:])  # Last 20 trades

@app.route('/api/clear-history', methods=['POST'])
def api_clear_history():
    app_state['trade_history'] = []
    return jsonify({'success': True})

@app.route('/api/sell-all-positions', methods=['POST'])
def api_sell_all_positions():
    """Sell all positions through Zerodha"""
    # Check Zerodha connection
    is_connected, message = check_zerodha_connection()
    if not is_connected:
        return jsonify({
            'success': False,
            'message': f'Cannot trade: {message}'
        })
    
    try:
        # Get current positions from Zerodha
        positions = app_state['kite'].positions()
        net_positions = positions['net']
        
        active_positions = [pos for pos in net_positions if int(pos['quantity']) > 0]
        
        if not active_positions:
            return jsonify({
                'success': False, 
                'message': 'No active positions to sell'
            })
        
        orders_placed = []
        total_pnl = 0
        
        # Place sell orders for all active positions
        for pos in active_positions:
            try:
                order_id = app_state['kite'].place_order(
                    variety=app_state['kite'].VARIETY_REGULAR,
                    exchange=pos['exchange'],
                    tradingsymbol=pos['tradingsymbol'],
                    transaction_type=app_state['kite'].TRANSACTION_TYPE_SELL,
                    quantity=int(pos['quantity']),
                    order_type=app_state['kite'].ORDER_TYPE_MARKET,
                    product=pos['product']
                )
                
                orders_placed.append({
                    'tradingsymbol': pos['tradingsymbol'],
                    'quantity': int(pos['quantity']),
                    'order_id': order_id
                })
                
                total_pnl += float(pos['unrealised'])
                
                # Record in trade history
                app_state['trade_history'].append({
                    'action': 'Sell All (LIVE)',
                    'tradingsymbol': pos['tradingsymbol'],
                    'qty': int(pos['quantity']),
                    'pnl': float(pos['unrealised']),
                    'order_id': order_id,
                    'time': dt.now().strftime('%Y-%m-%d %H:%M:%S')
                })
                
            except Exception as e:
                print(f"Failed to sell {pos['tradingsymbol']}: {e}")
        
        # 🔥 IMPORTANT: Clear all auto positions since we sold everything manually
        auto_positions_count = len(app_state['auto_positions'])
        if auto_positions_count > 0:
            app_state['auto_positions'] = []
            print(f"🗑️ CLEARED ALL AUTO POSITIONS: {auto_positions_count} positions removed (Sell All)")
        
        success_message = f'Placed {len(orders_placed)} sell orders'
        if auto_positions_count > 0:
            success_message += f' | Cleared {auto_positions_count} auto positions'
        
        return jsonify({
            'success': True, 
            'message': success_message,
            'orders': orders_placed,
            'estimated_pnl': total_pnl,
            'auto_positions_cleared': auto_positions_count
        })
        
    except Exception as e:
        return jsonify({
            'success': False, 
            'message': f'Error selling positions: {str(e)}'
        })

@app.route('/api/sell-individual-position', methods=['POST'])
def api_sell_individual_position():
    """Sell individual position through Zerodha by tradingsymbol"""
    # Check Zerodha connection
    is_connected, message = check_zerodha_connection()
    if not is_connected:
        return jsonify({
            'success': False,
            'message': f'Cannot trade: {message}'
        })
    
    data = request.get_json()
    tradingsymbol = data.get('tradingsymbol')
    
    if not tradingsymbol:
        return jsonify({
            'success': False,
            'message': 'Trading symbol is required'
        })
    
    try:
        # Get current positions from Zerodha
        positions = app_state['kite'].positions()
        net_positions = positions['net']
        
        # Find the specific position
        position_found = None
        for pos in net_positions:
            if pos['tradingsymbol'] == tradingsymbol and int(pos['quantity']) > 0:
                position_found = pos
                break
        
        if not position_found:
            return jsonify({
                'success': False,
                'message': f'No active position found for {tradingsymbol}'
            })
        
        quantity = int(position_found['quantity'])
        
        # Place sell order
        order_id = app_state['kite'].place_order(
            variety=app_state['kite'].VARIETY_REGULAR,
            exchange=position_found['exchange'],
            tradingsymbol=tradingsymbol,
            transaction_type=app_state['kite'].TRANSACTION_TYPE_SELL,
            quantity=quantity,
            order_type=app_state['kite'].ORDER_TYPE_MARKET,
            product=position_found['product']
        )
        
        pnl = float(position_found['unrealised'])
        
        # Record in trade history
        app_state['trade_history'].append({
            'action': 'Sell Individual (LIVE)',
            'tradingsymbol': tradingsymbol,
            'qty': quantity,
            'pnl': pnl,
            'order_id': order_id,
            'time': dt.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        
        # 🔥 Remove corresponding auto position completely if exists
        removed_count = 0
        for auto_pos in app_state['auto_positions'][:]:
            # Try to match by symbol components
            auto_symbol = f"{auto_pos['symbol']}{auto_pos.get('expiry', '')}{int(auto_pos['strike'])}{auto_pos['type']}"
            if tradingsymbol in auto_symbol or auto_symbol in tradingsymbol:
                # Use the complete removal function
                strike = auto_pos['strike']
                option_type = auto_pos['type']
                symbol = auto_pos['symbol']
                removed_count += execute_manual_sell_auto_position(strike, option_type, symbol)
                break  # Only remove one matching position
        
        success_message = f'✅ Sell order placed: {quantity} {tradingsymbol} @ Market'
        if removed_count > 0:
            success_message += f' | Auto position completely removed - NO AUTO BUY will trigger'
        
        return jsonify({
            'success': True,
            'message': success_message,
            'order_id': order_id,
            'pnl': pnl,
            'auto_positions_removed': removed_count
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error selling position: {str(e)}'
        })

# Auto Trading API Routes - AUTO TRADING IS ALWAYS ENABLED

@app.route('/api/auto-trading/remove-position', methods=['POST'])
def api_remove_auto_position_manual():
    """Manually remove auto position completely (no auto buy will trigger)"""
    try:
        data = request.get_json()
        strike = float(data.get('strike'))
        option_type = data.get('option_type')
        symbol = data.get('symbol', 'NIFTY')
        
        if not strike or not option_type:
            return jsonify({
                'success': False,
                'message': 'Strike and option_type are required'
            })
        
        removed_count = execute_manual_sell_auto_position(strike, option_type, symbol)
        
        if removed_count > 0:
            return jsonify({
                'success': True,
                'message': f'✅ Completely removed {removed_count} auto position(s) for {strike} {option_type}. NO AUTO BUY will trigger.',
                'removed_count': removed_count
            })
        else:
            return jsonify({
                'success': False,
                'message': f'No auto position found for {strike} {option_type}'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error removing auto position: {str(e)}'
        })

@app.route('/api/auto-trading/test-stop-loss', methods=['POST'])
def api_test_stop_loss():
    """Test stop loss functionality for a specific position"""
    try:
        data = request.get_json()
        position_id = data.get('position_id')
        test_price = float(data.get('test_price'))
        
        if not position_id or not test_price:
            return jsonify({
                'success': False,
                'message': 'Position ID and test price are required'
            })
        
        result = test_stop_loss_manually(position_id, test_price)
        if result:
            return jsonify({
                'success': True,
                'message': f'Stop loss test executed with price ₹{test_price}'
            })
        else:
            return jsonify({
                'success': False,
                'message': f'Position with ID {position_id} not found'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error testing stop loss: {str(e)}'
        })

@app.route('/api/auto-trading/status')
def api_auto_trading_status():
    """Get auto trading status"""
    return jsonify({
        'enabled': app_state['auto_trading_enabled'],
        'running': app_state['auto_trading_running'],
        'total_positions': len(app_state['auto_positions']),
        'active_positions': len([p for p in app_state['auto_positions'] if not p.get('waiting_for_autobuy', False)]),
        'waiting_positions': len([p for p in app_state['auto_positions'] if p.get('waiting_for_autobuy', False)]),
        'config': app_state['auto_trading_config']
    })

@app.route('/api/auto-trading/positions')
def api_auto_trading_positions():
    """Get auto trading positions"""
    positions_data = []
    for pos in app_state['auto_positions']:
        current_pnl = (pos['current_price'] - pos['buy_price']) * pos['qty'] if not pos.get('waiting_for_autobuy', False) else 0
        
        positions_data.append({
            'id': pos['id'],
            'symbol': pos['symbol'],
            'strike': pos['strike'],
            'type': pos['type'],
            'qty': pos['qty'],
            'buy_price': pos['buy_price'],
            'current_price': pos['current_price'],
            'highest_price': pos['highest_price'],
            'stop_loss_price': pos['stop_loss_price'],
            'current_pnl': current_pnl,
            'realized_pnl': pos['realized_pnl'],
            'total_pnl': pos['total_pnl'],
            'mode': pos['mode'],
            'auto_bought': pos.get('auto_bought', False),
            'waiting_for_autobuy': pos.get('waiting_for_autobuy', False),
            'auto_sell_count': pos.get('auto_sell_count', 0),
            'entry_time': pos.get('entry_time', None)
        })
    
    return jsonify({
        'success': True,
        'positions': positions_data
    })

@app.route('/api/auto-trading/add-position', methods=['POST'])
def api_add_auto_position():
    """Add new position to auto trading"""
    data = request.get_json()
    strike = float(data.get('strike'))
    option_type = data.get('option_type')
    buy_price = float(data.get('price', 0))
    lots = int(data.get('lots', 1))
    symbol = data.get('symbol', 'NIFTY')
    expiry = data.get('expiry', '')
    
    lot_size = LOT_SIZES.get(symbol, 75)
    total_qty = lot_size * lots
    total_cost = total_qty * buy_price
    
    # Check max positions limit
    if len(app_state['auto_positions']) >= app_state['auto_trading_config']['max_positions']:
        return jsonify({
            'success': False,
            'message': f'Maximum positions limit reached: {app_state["auto_trading_config"]["max_positions"]}'
        })
    
    # Check if Zerodha is connected
    if not app_state.get('zerodha_connected'):
        return jsonify({
            'success': False,
            'message': 'Zerodha not connected. Please connect to Zerodha first.'
        })
    
    # Create auto position
    position = create_auto_position(strike, option_type, buy_price, total_qty, symbol, expiry)
    
    # Record trade
    app_state['trade_history'].append({
        'action': 'Auto Position Added',
        'type': option_type,
        'strike': strike,
        'qty': total_qty,
        'price': buy_price,
        'pnl': 0,
        'position_id': position['id'],
        'time': dt.now().strftime('%Y-%m-%d %H:%M:%S')
    })
    
    return jsonify({
        'success': True,
        'message': f'✅ Auto position added: {total_qty} {option_type} @ ₹{buy_price}',
        'position_id': position['id']
    })

@app.route('/api/auto-trading/remove-position', methods=['POST'])
def api_remove_auto_position():
    """Remove position from auto trading"""
    data = request.get_json()
    position_id = data.get('position_id')
    
    position = next((p for p in app_state['auto_positions'] if p['id'] == position_id), None)
    if not position:
        return jsonify({'success': False, 'message': 'Position not found'})
    
    # If position is running, sell it first
    if not position.get('waiting_for_autobuy', False):
        pnl = (position['current_price'] - position['buy_price']) * position['qty']
        
        # Record trade
        app_state['trade_history'].append({
            'action': 'Auto Position Removed',
            'type': position['type'],
            'strike': position['strike'],
            'qty': position['qty'],
            'price': position['current_price'],
            'pnl': pnl,
            'position_id': position['id'],
            'time': dt.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    
    # Remove position
    app_state['auto_positions'].remove(position)
    
    return jsonify({
        'success': True,
        'message': f'Position removed: {position["strike"]} {position["type"]}'
    })

@app.route('/api/auto-trading/config', methods=['GET', 'POST'])
def api_auto_trading_config():
    """Get or update auto trading configuration"""
    if request.method == 'GET':
        return jsonify(app_state['auto_trading_config'])
    
    # POST - Update configuration
    data = request.get_json()
    
    if 'stop_loss_points' in data:
        app_state['auto_trading_config']['stop_loss_points'] = int(data['stop_loss_points'])
    
    if 'trailing_step' in data:
        app_state['auto_trading_config']['trailing_step'] = int(data['trailing_step'])
    
    if 'max_positions' in data:
        app_state['auto_trading_config']['max_positions'] = int(data['max_positions'])
    
    if 'auto_buy_enabled' in data:
        app_state['auto_trading_config']['auto_buy_enabled'] = bool(data['auto_buy_enabled'])
    
    if 'stop_loss_enabled' in data:
        app_state['auto_trading_config']['stop_loss_enabled'] = bool(data['stop_loss_enabled'])
    
    if 'trailing_enabled' in data:
        app_state['auto_trading_config']['trailing_enabled'] = bool(data['trailing_enabled'])
    
    return jsonify({
        'success': True,
        'message': 'Configuration updated',
        'config': app_state['auto_trading_config']
    })

@app.route('/api/auto-trading/clear-positions', methods=['POST'])
def api_clear_auto_positions():
    """Clear all auto trading positions"""
    # Clear positions
    app_state['auto_positions'] = []
    
    return jsonify({
        'success': True,
        'message': 'All auto positions cleared'
    })
    
# Real-time data updates via WebSocket
@socketio.on('connect')
def handle_connect():
    print('Client connected')
    emit('connected', {'data': 'Connected to server'})

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

def background_data_update():
    """Background thread to send real-time updates from Zerodha"""
    while True:
        try:
            with app.app_context():
                # Send market status update
                market_status = get_market_status()
                socketio.emit('market_status_update', market_status)
                
                # Send wallet info update (from Zerodha)
                with app.test_request_context():
                    wallet_info = api_wallet_info().get_json()
                    socketio.emit('wallet_update', wallet_info)
                
                # Send option chain update if active
                if app_state['option_chain_obj']:
                    with app.test_request_context():
                        option_data = api_option_chain_data().get_json()
                        if option_data.get('success'):
                            socketio.emit('option_chain_update', option_data)
                            
                            # Process auto trading if enabled
                            if app_state['auto_trading_enabled']:
                                process_auto_trading()
                
                # Send positions update (from Zerodha) with stop loss data
                with app.test_request_context():
                    positions_response = api_positions().get_json()
                    if positions_response.get('success'):
                        # Enhanced positions with stop loss data
                        enhanced_positions = []
                        for pos in positions_response.get('positions', []):
                            # Add stop loss data from auto positions
                            stop_loss_price = None
                            for auto_pos in app_state.get('auto_positions', []):
                                # Try to match position with auto position
                                auto_symbol = f"{auto_pos['symbol']}{auto_pos.get('expiry', '')}{int(auto_pos['strike'])}{auto_pos['type']}"
                                if pos['tradingsymbol'] in auto_symbol or auto_symbol in pos['tradingsymbol']:
                                    stop_loss_price = auto_pos.get('stop_loss_price', None)
                                    break
                            
                            pos['stop_loss'] = stop_loss_price
                            enhanced_positions.append(pos)
                        
                        socketio.emit('positions_update', {
                            'success': True,
                            'positions': enhanced_positions,
                            'total_positions': len(enhanced_positions),
                            'timestamp': dt.now().strftime('%H:%M:%S')
                        })
                    else:
                        socketio.emit('positions_update', positions_response)
                
                # Send auto trading positions update
                if app_state['auto_trading_enabled']:
                    with app.test_request_context():
                        auto_positions = api_auto_trading_positions().get_json()
                        socketio.emit('auto_positions_update', auto_positions)
                        
                        auto_status = api_auto_trading_status().get_json()
                        socketio.emit('auto_trading_status_update', auto_status)
                
                # Send orders update if Zerodha is connected
                if app_state['zerodha_connected']:
                    try:
                        orders = app_state['kite'].orders()
                        socketio.emit('orders_update', {'success': True, 'orders': orders})
                    except Exception as e:
                        print(f"Error fetching orders: {e}")
            
        except Exception as e:
            print(f"Error in background update: {e}")
        
        time.sleep(0.5)  # Update every 0.5 seconds for near real-time updates

@app.route('/api/auto-start-option-chain', methods=['POST'])
def api_auto_start_option_chain():
    """Auto-start option chain with default symbol and first available expiry"""
    try:
        symbol = 'NIFTY'  # Default symbol
        
        # Get first available expiry
        expiry_url = f"https://history.truedata.in/getSymbolExpiryList?symbol={symbol}&response=csv"
        headers = {
            "accept": "application/json",
            "authorization": "Bearer MLoowxCiiBf-2XjZnTo86I3JdfoSoAl48tFu3Il9JZH98XMzfTWSiDRFmOwGS9TLoM-ERnAd4K8nEoIiWQS9T6keBXQcHHguG9lfaR5MaxXQIwP9uLZVt08ChCrNKpSfq3lfxyujRBB9GKwPt-ti868Lt_KeSmUpwggd52d29s9jASH90VnMzP2CWAPm5PZ1rfmQ0684hzQUIza7n_SP--Z1pSEjACpUJhExz_9ond-fTn1YBrW6U75fACaRKj0iDGjdI8-gGn8TLksiTgfQzw"
        }
        
        response = requests.get(expiry_url, headers=headers)
        if response.status_code == 200:
            expiry_list = response.text.strip().split('\n')[1:]
            expiry_list = [x.strip() for x in expiry_list if x.strip()]
            if expiry_list:
                expiry = expiry_list[0]  # Get first expiry
                
                # Parse expiry date  
                if '-' in expiry:
                    expiry_datetime = dt.strptime(expiry, '%Y-%m-%d')
                elif len(expiry) == 8:
                    expiry_datetime = dt.strptime(expiry, '%Y%m%d')
                else:
                    expiry_datetime = dt.strptime(expiry, '%d-%b-%Y')
                
                key = f"{symbol}_{expiry}"
                
                # Stop previous option chain if exists
                if app_state['option_chain_obj'] and hasattr(app_state['option_chain_obj'], 'stop'):
                    try:
                        app_state['option_chain_obj'].stop()
                    except Exception:
                        pass
        
                # Start new option chain
                if app_state['td_obj']:
                    app_state['option_chain_obj'] = app_state['td_obj'].start_option_chain(
                        symbol, expiry=expiry_datetime, chain_length=10, bid_ask=True, greek=True
                    )
                    app_state['last_key'] = key
                    print(f"Option chain started for {symbol} expiry {expiry}")
                    return jsonify({'success': True, 'symbol': symbol, 'expiry': expiry})
        
        return jsonify({'success': False, 'message': 'No expiry dates available'})
    
    except Exception as e:
        print(f"Auto-start error: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/startup-check')
def api_startup_check():
    """Check if application is properly configured for live trading"""
    checks = {
        'api_key_configured': False,
        'api_secret_configured': False,
        'access_token_available': False,
        'kite_initialized': False,
        'truedata_initialized': False,
        'zerodha_connected': False,
        'auto_trading_ready': False,
        'ready_for_trading': False
    }
    
    messages = []
    
    # Check API Key
    if KITE_CONFIG['api_key'] and KITE_CONFIG['api_key'] != 'your_zerodha_api_key_here':
        checks['api_key_configured'] = True
        messages.append("✅ Zerodha API Key configured")
    else:
        messages.append("❌ Zerodha API Key not configured - Please add your API key to app.py")
    
    # Check API Secret
    if KITE_CONFIG['api_secret'] and KITE_CONFIG['api_secret'] != 'your_zerodha_api_secret_here':
        checks['api_secret_configured'] = True
        messages.append("✅ Zerodha API Secret configured")
    else:
        messages.append("❌ Zerodha API Secret not configured - Please add your API secret to app.py")
    
    # Check Access Token
    if KITE_CONFIG['access_token']:
        checks['access_token_available'] = True
        messages.append("✅ Access Token available")
    else:
        messages.append("⚠️ Access Token not available - Please complete Zerodha login")
    
    # Check Kite Initialization
    if app_state['kite']:
        checks['kite_initialized'] = True
        messages.append("✅ Kite Connect initialized")
    else:
        messages.append("❌ Kite Connect not initialized")
    
    # Check TrueData
    if app_state['td_obj']:
        checks['truedata_initialized'] = True
        messages.append("✅ TrueData initialized")
    else:
        messages.append("⚠️ TrueData not initialized - Market data may be limited")
    
    # Check Zerodha Connection
    is_connected, conn_message = check_zerodha_connection()
    if is_connected:
        checks['zerodha_connected'] = True
        messages.append(f"✅ Zerodha Connected: {conn_message}")
    else:
        messages.append(f"❌ Zerodha Connection Failed: {conn_message}")
    
    # Check Auto Trading Ready
    checks['auto_trading_ready'] = True
    messages.append("🤖 Auto Trading System Ready")
    messages.append(f" Active Auto Positions: {len(app_state['auto_positions'])}")
    
    # Overall trading readiness
    checks['ready_for_trading'] = (
        checks['api_key_configured'] and 
        checks['api_secret_configured'] and 
        checks['access_token_available'] and 
        checks['zerodha_connected']
    )
    
    if checks['ready_for_trading']:
        messages.append("🚀 READY FOR LIVE TRADING!")
        if checks['auto_trading_ready']:
            messages.append("🤖 AUTO TRADING FEATURES AVAILABLE!")
    else:
        messages.append("⚠️ Setup incomplete - Live trading disabled")
    
    return jsonify({
        'checks': checks,
        'messages': messages,
        'ready': checks['ready_for_trading'],
        'auto_trading_info': {
            'enabled': app_state['auto_trading_enabled'],
            'positions_count': len(app_state['auto_positions']),
            'config': app_state['auto_trading_config']
        }
    })

# --- TrueData to Zerodha Symbol Conversion ---
import re
from datetime import datetime

def td_to_zerodha_symbol(td_symbol):
    """
    Convert TrueData symbol to Zerodha format
    TrueData: NIFTY25080724550CE (SYMBOL+YY+MM+DD+STRIKE+TYPE)
    Zerodha: NIFTY258724550CE (SYMBOL+YY+M+D+STRIKE+TYPE) - Remove leading zeros from month and day
    """
    print(f"[DEBUG] Converting TrueData symbol: {td_symbol}")
    
    # Pattern for TrueData format: SYMBOL+YY+MM+DD+STRIKE+TYPE
    # Example: NIFTY25080724550CE -> NIFTY + 25 + 08 + 07 + 24550 + CE
    m = re.match(r'([A-Z]+)(\d{2})(\d{2})(\d{2})(\d+)(CE|PE)', td_symbol)
    if not m:
        print(f"[ERROR] TrueData regex did not match for: {td_symbol}")
        print(f"[ERROR] Expected format: SYMBOL+YY+MM+DD+STRIKE+TYPE (e.g., NIFTY25080724550CE)")
        return None

    symbol, year, month, day, strike, opt_type = m.groups()
    print(f"[DEBUG] Parsed: symbol={symbol}, year={year}, month={month}, day={day}, strike={strike}, type={opt_type}")

    # Zerodha format: Remove leading zero from month only, keep day and year as is
    month_no_zero = str(int(month))  # 08 -> 8, 09 -> 9
    # day stays with leading zero: 07 -> 07
    # year stays as is: 25 -> 25
    
    zerodha_symbol = f"{symbol}{year}{month_no_zero}{day}{strike}{opt_type}"
    print(f"[DEBUG] Converted {td_symbol} to Zerodha symbol: {zerodha_symbol}")
    return zerodha_symbol

# Example usage in order placement:
# td_symbol = 'NIFTY2573124700CE'
# zerodha_symbol = td_to_zerodha_symbol(td_symbol)
# kite.place_order(tradingsymbol=zerodha_symbol, ...)

# Main entry point
if __name__ == '__main__':
    print("🚀 Starting Zerodha Live Options Trading App...")
    print("📊 Features:")
    print("  ✅ Real-time option chain data") 
    print("  ✅ Live Zerodha trading integration")
    print("  ✅ Auto trading with stop loss")
    print("  ✅ Position management")
    print("  ✅ P&L tracking")
    print("🌐 Access: http://127.0.0.1:5000")
    print("⚡ Ready for live trading!")
    
    # Initialize Zerodha connection
    initialize_kite()
    
    # Start auto trading background thread
    auto_trading_thread = threading.Thread(target=auto_trading_background_task, daemon=True)
    auto_trading_thread.start()
    print("🤖 Auto trading background thread started")
    
    # Run the Flask app
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
