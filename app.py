

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
import sys

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Configure file logging
LOG_FILE = 'logging.txt'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, mode='a', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Custom print function to log to file
original_print = print
def print(*args, **kwargs):
    """Custom print function that logs to file and console"""
    message = ' '.join(str(arg) for arg in args)
    logger.info(message)
    original_print(*args, **kwargs)

# --- IST Time Helper Function ---
def get_ist_now():
    """Get current time in IST timezone"""
    ist = pytz.timezone('Asia/Kolkata')
    return dt.now(ist)

def get_ist_timestamp():
    """Get IST timestamp in ISO format"""
    return get_ist_now().isoformat()

def get_ist_time_formatted():
    """Get IST time in formatted string (YYYY-MM-DD HH:MM:SS IST)"""
    return get_ist_now().strftime('%Y-%m-%d %H:%M:%S IST')

# --- Global Variables ---
SESSION_FILE = 'active_session.txt'
VALID_USERNAME = 'admin'
VALID_PASSWORD = 'admin123'

# Zerodha Kite Connect Configuration - REQUIRED FOR LIVE TRADING
KITE_CONFIG = {
    'api_key': '9aiu7a2k8wu9kn56',  # Your Zerodha API key
    'api_secret': 'kdrz7wtjhow8etyixr2nq2hmf589vf4c',  
    'access_token': 'gVsZMCvfaoeQH2O1IrClxhCmcYMXYrQK',  
    'request_token': 'l8o4oHiHYJqwNVocDQdCuqS4tvqfsCeu'  
}

# --- Session Monitor Constants ---
SESSION_MONITOR_INTERVAL = 300  # seconds (5 minutes)
SESSION_MONITOR_RETRY_INTERVAL = 30  # seconds

# --- Paper Trading Constants ---
PAPER_TRADING_ENABLED = True  # Toggle between paper and real trading (DEFAULT: Paper Trading)
INITIAL_PAPER_WALLET_BALANCE = 10000000.0  # Starting balance for paper trading (₹1,00,000)

# Initialize session state equivalent
app_state = {
    'positions': [],
    'cooldown_enabled': True,  # Toggle for cooldown protection
    'trading_algorithm': 'advanced',  # 'simple' or 'advanced' - DEFAULT TO ADVANCED for Phase 1 fix
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
    # Paper Trading State
    'paper_trading_enabled': PAPER_TRADING_ENABLED,
    'paper_wallet_balance': INITIAL_PAPER_WALLET_BALANCE,
    'paper_positions': [],
    'paper_orders': [],
    'paper_trade_history': [],
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
        'auto_buy_buffer': 0,    # NO BUFFER
        # 🚨 EMERGENCY CIRCUIT BREAKER - Prevent infinite buy-sell loops
        'max_auto_cycles_per_position': 3,  # Max 3 auto buy-sell cycles per position
        'circuit_breaker_enabled': True,
        'max_loss_per_position': 5000,  # Stop after ₹5000 loss on single position
        'position_sync_enabled': True  # Sync with Zerodha positions
    }
}

# Lot sizes by symbol
LOT_SIZES = {
    "NIFTY": 75,
    "BANKNIFTY": 35,
    "MIDCPNIFTY": 140,
    "SENSEX": 20,
    "SBIN": 3400,
    "RELIANCE": 500
}

# Global instruments cache - will be loaded from Zerodha API
instruments_df = None
instruments_cache_time = None
INSTRUMENTS_CACHE_DURATION = 3600  # Cache for 1 hour (in seconds)
instruments_index = {}  # ⚡ Fast lookup index

def fetch_nfo_instruments():
    global instruments_df, instruments_cache_time, instruments_index
    
    # Check if cache is still valid
    if instruments_df is not None and instruments_cache_time is not None:
        time_elapsed = time.time() - instruments_cache_time
        if time_elapsed < INSTRUMENTS_CACHE_DURATION:
            return instruments_df
    
    # Fetch fresh instruments from Zerodha using pandas
    try:
        print("[⚡ FAST] Fetching instruments from Zerodha API...")
        
        # Official method: Fetch directly from Kite API URL using pandas
        instruments_df = pd.read_csv("https://api.kite.trade/instruments")
        
        # Filter for NFO (F&O) instruments only
        instruments_df = instruments_df[instruments_df['exchange'] == 'NFO'].copy()
        
        # ⚡ CREATE FAST LOOKUP INDEX
        instruments_index = {}
        for idx, row in instruments_df.iterrows():
            key = f"{row['name']}_{row['expiry']}_{row['strike']}_{row['instrument_type']}"
            instruments_index[key] = {
                'tradingsymbol': row['tradingsymbol'],
                'instrument_token': row['instrument_token']
            }
        
        instruments_cache_time = time.time()
        
        print(f"[⚡ FAST] Loaded {len(instruments_df)} instruments with index in {int((time.time() - instruments_cache_time)*1000)}ms")
        
        return instruments_df
            
    except Exception as e:
        print(f"[ERROR] Failed to fetch instruments from Zerodha API URL: {e}")
        traceback.print_exc()
        
        # Fallback: Try loading from local CSV if exists
        try:
            print("[INFO] Attempting fallback to local CSV file...")
            instruments_df = pd.read_csv("zerodha_instruments.csv")
            # Filter for NFO
            if 'exchange' in instruments_df.columns:
                instruments_df = instruments_df[instruments_df['exchange'] == 'NFO'].copy()
            instruments_cache_time = time.time()
            print(f"[INFO] Loaded {len(instruments_df)} instruments from CSV fallback")
            return instruments_df
        except Exception as fallback_error:
            print(f"[ERROR] CSV fallback also failed: {fallback_error}")
            return None

def find_instrument_by_criteria(symbol, expiry, strike, instrument_type):
    global instruments_df, instruments_index
    
    # Ensure instruments are loaded
    if instruments_df is None:
        fetch_nfo_instruments()
    
    if instruments_df is None:
        print("[ERROR] No instruments data available")
        return None, None
    
    try:
        # ⚡ FAST: Try index lookup first (O(1) instead of O(n))
        lookup_key = f"{symbol}_{expiry}_{strike}_{instrument_type}"
        if lookup_key in instruments_index:
            result = instruments_index[lookup_key]
            return result['tradingsymbol'], result['instrument_token']
        
        # Fallback: Traditional DataFrame filtering (slower)
        filtered = instruments_df[
            (instruments_df['name'] == symbol) &
            (instruments_df['expiry'] == expiry) &
            (instruments_df['strike'] == strike) &
            (instruments_df['instrument_type'] == instrument_type)
        ]
        
        if not filtered.empty:
            result = filtered.iloc[0]
            tradingsymbol = result['tradingsymbol']
            instrument_token = result['instrument_token']
            
            # Cache for next time
            instruments_index[lookup_key] = {
                'tradingsymbol': tradingsymbol,
                'instrument_token': instrument_token
            }
            
            return tradingsymbol, instrument_token
        else:
            return None, None
            
    except Exception as e:
        print(f"[ERROR] Error filtering instruments: {e}")
        traceback.print_exc()
        return None, None

def initialize_zerodha():
    try:
        if app_state.get('kite') is not None:
            print("[INFO] Zerodha already initialized")
            return True
        
        if not KITE_CONFIG.get('access_token'):
            print("[ERROR] No access token found in KITE_CONFIG")
            return False
        
        print("[INFO] Initializing Zerodha KiteConnect...")
        kite = KiteConnect(api_key=KITE_CONFIG['api_key'])
        kite.set_access_token(KITE_CONFIG['access_token'])
        
        # Test the connection
        try:
            profile = kite.profile()
            print(f"[SUCCESS] Zerodha connected successfully for user: {profile.get('user_name', 'Unknown')}")
            app_state['kite'] = kite
            app_state['zerodha_connected'] = True
            return True
        except Exception as e:
            print(f"[ERROR] Failed to verify Zerodha connection: {e}")
            app_state['zerodha_connected'] = False
            return False
            
    except Exception as e:
        print(f"[ERROR] Failed to initialize Zerodha: {e}")
        traceback.print_exc()
        app_state['zerodha_connected'] = False
        return False

# Utility: Convert YYMMDD (TrueData) to DDMMM (Zerodha)
def td_expiry_to_ddmmm(yymmdd):
    """
    Convert TrueData expiry format to Zerodha format
    Args:
        yymmdd: String in format YYMMDD (e.g., '251028' for 28-Oct-2025)
                or YYMDD (e.g., '5731' for 31-Jul-2025 - legacy format)
    Returns:
        tuple: (ddmmm_string, yyyy-mm-dd_string)
    """
    try:
        # Handle both 6-digit (YYMMDD) and 5-digit (YYMDD) formats
        if len(yymmdd) == 6:
            # New format: YYMMDD (e.g., '251028')
            year = int('20' + yymmdd[:2])
            month = int(yymmdd[2:4])
            day = int(yymmdd[4:6])
        elif len(yymmdd) == 5:
            # Legacy format: YYMDD (e.g., '25731' for July 31, 2025)
            year = int('20' + yymmdd[:2])
            month = int(yymmdd[2])
            day = int(yymmdd[3:5])
        else:
            raise ValueError(f"Invalid expiry format: {yymmdd} (expected 6-digit YYMMDD or 5-digit YYMDD)")
        
        dt_obj = datetime(year, month, day)
        ddmmm = dt_obj.strftime('%d%b').upper()  # '28OCT' or '31JUL'
        return ddmmm, dt_obj.strftime('%Y-%m-%d')
        
    except ValueError as e:
        print(f"[ERROR] Failed to parse expiry date '{yymmdd}': {e}")
        raise ValueError(f"Invalid expiry date format '{yymmdd}': {e}")

# Main function: TrueData symbol to Zerodha tradingsymbol
def get_zerodha_symbol(td_symbol):
    """
    Convert TrueData symbol to Zerodha tradingsymbol using the official method:
    1. Parse the TrueData symbol (e.g., NIFTY25102825800CE or NIFTY2573124500CE)
    2. Fetch NFO instruments from Zerodha API
    3. Filter by symbol, expiry, strike, and instrument_type
    
    Args:
        td_symbol: TrueData format symbol
                   Format 1: SYMBOL + YYMMDD + STRIKE + CE/PE (e.g., NIFTY25102825800CE)
                   Format 2: SYMBOL + YYMDD + STRIKE + CE/PE (e.g., NIFTY2573124500CE - legacy 5-digit)
    
    Returns:
        tuple: (tradingsymbol, instrument_token, error_message)
    """
    # Ensure instruments are loaded first
    global instruments_df
    if instruments_df is None or instruments_df.empty:
        print(f"[WARNING] Instruments not loaded, fetching now...")
        fetch_nfo_instruments()
        if instruments_df is None or instruments_df.empty:
            return None, None, f'Failed to load instruments from Zerodha API'
    
    # Strategy: Try to intelligently detect which format based on length and patterns
    # New format has 6-digit expiry (YYMMDD) which means month is 01-12 (positions 3-4)
    # Legacy format has 4-digit expiry (YYMDD) which means month is 1-9 (position 3)
    
    # Extract the base symbol first (all capital letters at start)
    symbol_match = re.match(r'^([A-Z]+)', td_symbol)
    if not symbol_match:
        return None, None, f'Invalid TrueData symbol format: {td_symbol}'
    
    symbol = symbol_match.group(1)
    remaining = td_symbol[len(symbol):]  # Everything after symbol name
    
    # Try to match: DIGITS + CE/PE at the end
    # We need to figure out where strike starts and expiry ends
    parts_match = re.match(r'^(\d+)(CE|PE)$', remaining)
    if not parts_match:
        return None, None, f'Invalid TrueData symbol format: {td_symbol}'
    
    all_digits, opt_type = parts_match.groups()
    
    # Now intelligently split all_digits into expiry + strike
    # If starts with 25 (year 2025), try 6-digit expiry first
    if len(all_digits) >= 6 and all_digits.startswith('25'):
        # Try new format: YYMMDD (6 digits)
        expiry_digits = all_digits[:6]
        strike = all_digits[6:]
        
        # Validate: month should be 01-12 (positions 2-3 of expiry_digits)
        try:
            month = int(expiry_digits[2:4])
            if 1 <= month <= 12 and len(strike) > 0:
                # This looks like valid new format
                pass
            else:
                # Fall back to legacy format (5 digits: YYMDD)
                expiry_digits = all_digits[:5]
                strike = all_digits[5:]
        except:
            # Fall back to legacy format (5 digits: YYMDD)
            expiry_digits = all_digits[:5]
            strike = all_digits[5:]
    else:
        # Legacy format: YYMDD (5 digits)
        if len(all_digits) >= 5:
            expiry_digits = all_digits[:5]
            strike = all_digits[5:]
        else:
            return None, None, f'Invalid TrueData symbol format: {td_symbol}'
    
    # Validate we have a strike
    if not strike:
        return None, None, f'No strike price found in: {td_symbol}'
    
    try:
        ddmmm, expiry_str = td_expiry_to_ddmmm(expiry_digits)
    except ValueError as e:
        return None, None, f'Failed to parse expiry from {td_symbol}: {e}'
    
    strike_val = float(strike)
    
    print(f"[DEBUG] Parsing TD symbol: {td_symbol}")
    print(f"[DEBUG] Extracted - Symbol: {symbol}, Expiry: {expiry_str}, Strike: {strike_val}, Type: {opt_type}")
    
    # Use the official method: Filter instruments from Zerodha API
    tradingsymbol, instrument_token = find_instrument_by_criteria(
        symbol=symbol,
        expiry=expiry_str,
        strike=strike_val,
        instrument_type=opt_type
    )
    
    if tradingsymbol and instrument_token:
        return tradingsymbol, instrument_token, None
    else:
        # Fallback: Try old method with constructed tradingsymbol
        print(f"[DEBUG] Trying fallback with constructed symbol...")
        search_symbol = f"{symbol}{ddmmm}{int(strike)}{opt_type}"
        
        # instruments_df already declared as global at function start
        if instruments_df is None:
            fetch_nfo_instruments()
        
        if instruments_df is not None:
            row = instruments_df[
                (instruments_df['tradingsymbol'] == search_symbol) &
                (instruments_df['expiry'] == expiry_str) &
                (instruments_df['strike'] == strike_val) &
                (instruments_df['name'] == symbol)
            ]
            
            if not row.empty:
                print(f"[SUCCESS] Fallback method found: {row.iloc[0]['tradingsymbol']}")
                return row.iloc[0]['tradingsymbol'], row.iloc[0]['instrument_token'], None
            
            # Enhanced error message showing available strikes
            error_msg = f"Zerodha symbol not found for {td_symbol} (tried {search_symbol})"
            
            # Show available strikes for this expiry and option type
            available = instruments_df[
                (instruments_df['name'] == symbol) &
                (instruments_df['expiry'] == expiry_str) &
                (instruments_df['instrument_type'] == opt_type)
            ]
            
            if not available.empty:
                strikes_list = sorted(available['strike'].unique())
                # Find strikes near the requested one
                nearby = [s for s in strikes_list if abs(s - strike_val) <= 500]
                if nearby:
                    error_msg += f"\n  Available strikes near {strike_val}: {nearby[:10]}"
                else:
                    error_msg += f"\n  Available strikes for {symbol} {expiry_str} {opt_type}: {strikes_list[:10]}"
            else:
                # Show available expiries
                expiries = sorted(instruments_df[
                    (instruments_df['name'] == symbol) &
                    (instruments_df['instrument_type'] == opt_type)
                ]['expiry'].unique())
                error_msg += f"\n  Available expiries for {symbol} {opt_type}: {expiries[:5]}"
            
            return None, None, error_msg
        
        return None, None, f"Zerodha symbol not found for {td_symbol} (tried {search_symbol}) - Instruments not loaded"

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
    
def update_price_history(symbol, expiry, strike, option_type, current_price):
    """Update price history for trend analysis"""
    key = f"{symbol}_{expiry}_{strike}_{option_type}"
    current_time = get_ist_now()
    
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
    # 🚨 VOLATILITY PROTECTION: Use appropriate stop loss buffer
    stop_loss_buffer = app_state['auto_trading_config']['stop_loss_points']  # Default: 10 points
    stop_loss_price = buy_price - stop_loss_buffer  # Manual buy: -buffer points
    
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
        'auto_bought': False,  # 🚨 CRITICAL: Mark as manual buy (NOT auto bought)
        'waiting_for_autobuy': False,
        'mode': 'Running',
        'entry_time': get_ist_now(),
        'last_update': get_ist_now(),
        'total_pnl': 0,
        'realized_pnl': 0,
        'auto_sell_count': 0,
        'auto_buy_count': 0,
        # CRITICAL SAFETY FLAGS: Initialize protection against multiple sells and unwanted auto buys
        'sold': False,
        'manual_sold': False,
        'sell_in_progress': False,
        'sell_triggered': False,
        'individual_cooldown_enabled': True  # Default: cooldown enabled for new positions
    }
    app_state['auto_positions'].append(position)
    
    # Debug print to confirm stop loss is set correctly for manual buy
    print(f"📍 MANUAL BUY POSITION CREATED: {strike} {option_type} @ ₹{buy_price} | Stop Loss: ₹{stop_loss_price} (Buy price - 10)")
    
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
    """Update position price and handle auto trading logic based on selected algorithm"""
    # Convert new_price to float to handle string inputs
    try:
        new_price = float(new_price)
    except (ValueError, TypeError):
        print(f"[ERROR] Invalid price format: {new_price}, skipping update")
        return False
    
    # Get current trading algorithm
    algorithm = app_state.get('trading_algorithm', 'advanced')
    
    if algorithm == 'simple':
        return update_simple_algorithm(position, new_price)
    elif algorithm == 'advanced':
        return update_advanced_algorithm(position, new_price)
    else:
        print(f"[ERROR] Unknown algorithm: {algorithm}")
        return update_simple_algorithm(position, new_price)

def update_simple_algorithm(position, new_price):
    """Original algorithm: Simple stop loss with auto buy at last stop loss"""
    print(f"[DEBUG] SIMPLE ALGORITHM CALLED for {position.get('strike', '?')} {position.get('type', '?')} | Price: {new_price}")
    old_price = float(position['current_price'])
    position['current_price'] = new_price
    position['last_update'] = get_ist_now()
    
    # Update highest price for trailing stop loss
    # Initialize highest_price if it doesn't exist (for paper trading positions)
    if 'highest_price' not in position:
        position['highest_price'] = position.get('buy_price', position.get('average_price', new_price))
    
    if new_price > float(position['highest_price']):
        position['highest_price'] = new_price
    
    # Update trailing stop loss first (SIMPLE ALGORITHM ONLY)
    update_trailing_stop_loss(position, algorithm='simple')
    
    # Debug print for stop loss monitoring (only when price changes significantly or near stop loss)
    price_diff = abs(new_price - old_price)
    near_stop_loss = abs(new_price - position['stop_loss_price']) < 5  # Within 5 rupees of stop loss
    
    if price_diff > 2 or near_stop_loss:  # Only print when price changes by more than 2 rupees or near stop loss
        print(f"🔍 SIMPLE MONITORING: {position['strike']} {position['type']} | Current: ₹{new_price} | Stop Loss: ₹{position['stop_loss_price']} | Auto Bought: {position.get('auto_bought', False)}")
    
    # Check for stop loss trigger - FIXED: Enhanced for both profit targets and stop losses
    manual_sl_active = position.get('manual_stop_loss_set', False)
    stop_loss_price = position['stop_loss_price']
    current_price = position['current_price']
    buy_price = position.get('original_buy_price', position.get('buy_price', 0))
    
    print(f"🔍 SIMPLE SL TRIGGER CHECK: Current ₹{current_price} vs SL ₹{stop_loss_price} | Manual SL Active: {manual_sl_active}")
    
    # 🎯 TRAILING SL: Manual SL must be armed before triggering
    trigger_condition = False
    if manual_sl_active:
        # Check if price crossed above manual SL (arm it)
        manual_sl_armed = position.get('manual_sl_armed', False)
        
        if not manual_sl_armed and current_price > stop_loss_price:
            position['manual_sl_armed'] = True
            print(f"   ✅ MANUAL SL ARMED: Price ₹{current_price} crossed above SL ₹{stop_loss_price}")
            trigger_condition = False
        # If armed and price crosses BELOW manual SL → SELL
        elif manual_sl_armed and current_price < stop_loss_price:
            trigger_condition = True
            print(f"   🎯 TRAILING SL TRIGGER: Price ₹{current_price} dropped below armed SL ₹{stop_loss_price}")
        else:
            trigger_condition = False
            status = "ARMED - waiting for drop" if manual_sl_armed else "UNARMED - waiting for price to cross above"
            print(f"   Manual SL ₹{stop_loss_price}: {status}")
    else:
        # Algorithm stop loss: traditional logic (only this should trigger sells)
        trigger_condition = current_price < stop_loss_price
        print(f"   Algorithm SL Trigger: {current_price} < {stop_loss_price} = {trigger_condition}")
        if trigger_condition:
            print(f"   🚨 STOP LOSS HIT! Current ₹{current_price} dropped below SL ₹{stop_loss_price}")
            print(f"   📤 Will execute AUTO SELL for {position.get('strike')} {position.get('type')}")
    
    if (trigger_condition and 
        stop_loss_price > 0 and 
        not position.get('waiting_for_autobuy', False) and
        not position.get('sell_triggered', False)):  # SAFETY: Prevent duplicate sells
        
        # Determine appropriate reason based on profit/loss
        is_profit = current_price > buy_price
        
        if is_profit:
            reason = 'Trailing Stop Loss (Profit Booking)'
        else:
            reason = 'Stop Loss'
        
        # AUTO SELL - Stop Loss Hit
        print(f"SIMPLE STOP LOSS TRIGGERED")
        print(f"   Position: {position['strike']} {position['type']}")
        print(f"   Current Price: ₹{new_price}")
        print(f"   Stop Loss Price: ₹{stop_loss_price}")
        print(f"   Reason: {reason}")
        print(f"   Paper Trading Enabled: {app_state.get('paper_trading_enabled', False)}")
        print(f"   About to call execute_auto_sell()...")
        
        sell_executed = execute_auto_sell(position, reason=reason)
        
        print(f"   execute_auto_sell returned: {sell_executed}")
        
        if sell_executed:
            position['sell_triggered'] = True  # Set after trade is recorded
            print(f"   ✅ SELL EXECUTED SUCCESSFULLY")
            return True
        else:
            print(f"   ❌ SELL EXECUTION FAILED")
        return False
    
    # Check for auto buy trigger - only if waiting for auto buy
    # 🚨 FIX: Use >= with 0.1 buffer to prevent oscillation
    auto_buy_trigger = position.get('last_stop_loss_price', 0)
    
    if (position.get('waiting_for_autobuy', False) and 
        position['current_price'] >= auto_buy_trigger):
        
        print(f"🎯 AUTO BUY TRIGGER CHECK: {position['strike']} {position['type']} | Current: ₹{position['current_price']} | Trigger: ₹{auto_buy_trigger} | Auto Buy Count: {position.get('auto_buy_count', 0)}")
        
        # Execute auto buy
        buy_executed = execute_auto_buy(position)
        if buy_executed:
            return True
        return False
    
    return False

def update_advanced_algorithm(position, new_price):
    """NEW Rule-Based Advanced Algorithm: Confirmation Entry System with Profit Protection
    
    🎯 CONFIRMATION RE-ENTRY WITH PROFIT PROTECTION:
    
    SCENARIO 1: Normal SL Hit and Re-entry
    ----------------------------------------
    Manual Buy: ₹100, SL: ₹90
    Price → ₹90 (SL hit) → Auto Sell
    Waiting for re-entry at ₹100
    Price → ₹100 → ✅ Auto Buy (re-entry successful)
    
    SCENARIO 2: Profit Protection - No Re-entry
    --------------------------------------------
    Manual Buy: ₹100, SL: ₹90
    Price → ₹90 (SL hit) → Auto Sell
    Waiting for re-entry at ₹100
    Price → ₹112 (₹100 + 10+ points) → 🚫 Auto Buy DISABLED (Profit Protection)
    Reason: Price went 10+ points above entry = Profit secured, no need to re-enter
    
    SCENARIO 3: Price Jumps After SL
    ---------------------------------
    Manual Buy: ₹100, SL: ₹90
    Price → ₹85 (below SL) → Auto Sell
    Price → ₹115 → 🚫 Auto Buy DISABLED (missed entry + profit zone)
    Price → ₹95 → Still no auto buy (already disabled)
    
    🎯 RULE 1: Entry ₹100, SL ₹90 → If SL hit, re-entry at ₹100
    🎯 RULE 2: Price ₹110 → SL remains ₹90 (no change)
    🎯 RULE 3: Price ₹120 → SL moves to ₹100 (cost price protection)
    🎯 RULE 4: Price ₹130 → SL moves to ₹110, Confirmation re-entry after SL
    🎯 RULE 5: Price ₹140 → SL moves to ₹120, Confirmation re-entry after SL
    
    EXAMPLE (Entry ₹100):
    Price ₹110: SL ₹90 (wait)
    Price ₹120: SL ₹100 (cost protection)
    Price ₹130: SL ₹110 (re-entry system active)
    Price ₹140: SL ₹120 (confirmation entries)
    """
    print(f"[DEBUG] NEW ADVANCED ALGORITHM CALLED for {position.get('strike', '?')} {position.get('type', '?')} | Price: {new_price}")
    old_price = float(position['current_price'])
    position['current_price'] = new_price
    position['last_update'] = get_ist_now()
    
    # Initialize required fields for RULE-BASED advanced algorithm
    if 'original_buy_price' not in position:
        position['original_buy_price'] = position.get('buy_price', position.get('average_price', new_price))
    if 'manual_buy_price' not in position:
        position['manual_buy_price'] = position.get('buy_price', position.get('average_price', new_price))  # Entry price anchor
    if 'highest_price' not in position:
        position['highest_price'] = position['original_buy_price']
    if 'advanced_stop_loss' not in position:
        position['advanced_stop_loss'] = position['original_buy_price'] - 10  # Initial stop loss (buy_price - 10)
    if 're_entry_enabled' not in position:
        position['re_entry_enabled'] = True  # Always enabled in rule-based system
    
    original_buy_price = position['original_buy_price']
    manual_buy_price = position['manual_buy_price']
    
    # 🎯 NEW RULE-BASED SYSTEM: Determine SL based on price levels
    entry_price = manual_buy_price  # This is our ₹100 reference
    current_price = new_price
    
    # Calculate stop loss based on rules
    if current_price < entry_price + 10:  # Below ₹110
        # RULE 1 & 2: SL remains at entry-10 (₹90)
        calculated_sl = entry_price - 10
        rule_active = "1-2: Initial SL"
        re_entry_active = True
        
    elif current_price < entry_price + 20:  # Below ₹120
        # RULE 2: Price ₹110, SL still ₹90
        calculated_sl = entry_price - 10
        rule_active = "2: Waiting at ₹90 SL"
        re_entry_active = True
        
    elif current_price < entry_price + 30:  # Below ₹130
        # RULE 3: Price ₹120, SL moves to ₹100 (cost price)
        calculated_sl = entry_price
        rule_active = "3: Cost Price Protection"
        re_entry_active = True
        
    elif current_price < entry_price + 40:  # Below ₹140
        # RULE 4: Price ₹130, SL moves to ₹110
        calculated_sl = entry_price + 10
        rule_active = "4: Confirmation Re-entry"
        re_entry_active = True
        
    else:  # ₹140+
        # RULE 5: Price ₹140+, SL moves to ₹120
        profit_above_140 = current_price - (entry_price + 40)
        additional_steps = int(profit_above_140 // 10)
        calculated_sl = entry_price + 20 + (additional_steps * 10)
        rule_active = "5: Advanced Trailing"
        re_entry_active = True
    
    # CRITICAL: Stop Loss can ONLY move UP, never DOWN!
    current_stop_loss = position.get('advanced_stop_loss', 0)
    
    # Check if manual stop loss was set and should be respected
    manual_sl_set = position.get('manual_stop_loss_set', False)
    manual_sl_time = position.get('manual_stop_loss_time')
    
    if manual_sl_set and manual_sl_time:
        # Check if manual setting is recent (within last 30 minutes) - extended protection time
        time_diff = (get_ist_now() - manual_sl_time).total_seconds()
        if time_diff < 1800:  # 30 minutes (was 5 minutes)
            manual_stop_loss = position.get('stop_loss_price', 0)
            # ALWAYS respect manual stop loss during protection period, regardless of algorithm
            print(f"🔧 RESPECTING MANUAL STOP LOSS: ₹{manual_stop_loss} (Set {int(time_diff/60)}m ago) - Algorithm wants ₹{calculated_sl}")
            calculated_sl = manual_stop_loss
            position['advanced_stop_loss'] = manual_stop_loss
            # Don't clear the manual flag - keep it active
        else:
            # Manual setting expired after 30 minutes, clear the flag
            print(f"⏰ MANUAL STOP LOSS EXPIRED after 30 minutes - Resuming algorithm control")
            position['manual_stop_loss_set'] = False
    
    if calculated_sl > current_stop_loss:
        # Stop loss is moving UP - ALLOWED ✅
        position['advanced_stop_loss'] = calculated_sl
        print(f"📈 STOP LOSS MOVED UP: ₹{current_stop_loss} → ₹{calculated_sl}")
    else:
        # Stop loss would move DOWN - BLOCKED ❌
        position['advanced_stop_loss'] = current_stop_loss
        calculated_sl = current_stop_loss  # Use existing higher stop loss
        print(f"🛡️ STOP LOSS PROTECTED: Keeping ₹{current_stop_loss} (Calculated: ₹{calculated_sl})")
    
    position['re_entry_enabled'] = re_entry_active
    
    print(f"🎯 RULE {rule_active}: Entry ₹{entry_price} | Current ₹{current_price} | SL ₹{position['advanced_stop_loss']} | Re-entry: {'✅' if re_entry_active else '❌'}")
    
    # 🔧 PROTECT MANUAL STOP LOSS: Only update if no manual override
    manual_sl_active = position.get('manual_stop_loss_set', False)
    if manual_sl_active:
        print(f"🛡️ MANUAL STOP LOSS PROTECTED: Keeping user-set ₹{position['stop_loss_price']} (not overriding with algorithm ₹{position['advanced_stop_loss']})")
    else:
        # Update traditional stop_loss_price for display purposes
        position['stop_loss_price'] = position['advanced_stop_loss']
    
    # 🚨 CRITICAL FIX: Below current stop loss should trigger immediate sell
    # Emergency stop loss triggers at current SL level, not fixed entry-10
    # 🎯 TRAILING SL: For manual SL, only trigger if ARMED
    manual_sl_active = position.get('manual_stop_loss_set', False)
    
    if manual_sl_active:
        # Check if price crossed above manual SL (arm it)
        manual_sl_value = position.get('stop_loss_price', 0)
        manual_sl_armed = position.get('manual_sl_armed', False)
        
        if not manual_sl_armed and current_price > manual_sl_value:
            position['manual_sl_armed'] = True
            print(f"✅ MANUAL SL ARMED: Price ₹{current_price} crossed above SL ₹{manual_sl_value}")
        
        # Emergency trigger only if armed AND price below manual SL
        if manual_sl_armed and current_price < manual_sl_value:
            emergency_sl = manual_sl_value
            print(f"🚨 TRAILING SL EMERGENCY: Armed SL ₹{emergency_sl} breached")
        else:
            # Not armed or price not below SL - no emergency
            emergency_sl = None
    else:
        # Use algorithm's calculated SL for emergency check
        emergency_sl = position.get('advanced_stop_loss', calculated_sl)
    
    # CHECK AUTO-BUY TRIGGER FIRST (before emergency stop loss check)
    # If waiting for auto-buy, check re-entry trigger
    if position.get('waiting_for_autobuy', False):
        auto_buy_trigger = position.get('last_stop_loss_price', 0)
        print(f"🔍 AUTO BUY CHECK: Current ₹{current_price} vs Trigger ₹{auto_buy_trigger} (Entry ₹{entry_price})")
        
        # NEW RULE: Disable auto-buy if price went 10+ points above entry (profit protection)
        # Example: Entry ₹100, if price reaches ₹110+, no more auto-buy (profit secured)
        profit_from_entry = current_price - entry_price
        if profit_from_entry >= 10:
            print(f" PROFIT PROTECTION: Price ₹{current_price} is ₹{profit_from_entry:.2f} above entry ₹{entry_price}")
            print(f" AUTO BUY DISABLED: Profit zone reached (≥10 points). No re-entry.")
            position['waiting_for_autobuy'] = False
            position['auto_buy_disabled_reason'] = f'Profit Protection: +₹{profit_from_entry:.2f}'
            position['mode'] = 'Profit Protection - No Re-entry'
            return False
        
        # Check if current price reached the trigger price (with small buffer for price fluctuation)
        if current_price >= auto_buy_trigger - 0.5:  # Allow 0.5 rupee buffer
            print(f"🎯 CONFIRMATION RE-ENTRY: Price ₹{current_price} reached trigger ₹{auto_buy_trigger}")
            buy_executed = execute_auto_buy(position)
            if buy_executed:
                position['sell_triggered'] = False
                position['waiting_for_autobuy'] = False
                position['manual_buy_price'] = position['buy_price']
                print(f"✅ RE-ENTRY COMPLETE: New entry at ₹{position['buy_price']}")
                return True
            else:
                print(f"❌ AUTO BUY FAILED: Could not execute buy order")
        else:
            print(f"⏳ WAITING: Current ₹{current_price} below trigger ₹{auto_buy_trigger}")
    
    # Emergency stop loss check (only if NOT waiting for auto-buy)
    if emergency_sl and current_price < emergency_sl:
        print(f"🚨 STOP LOSS BREACHED: Price ₹{current_price} < SL ₹{emergency_sl} - IMMEDIATE SELL TRIGGER!")
        
        # If not already sold or waiting for auto-buy, trigger immediate sell
        if (not position.get('waiting_for_autobuy', False) and 
            not position.get('sell_triggered', False)):
            
            profit = current_price - entry_price
            reason = 'Emergency Stop Loss - Below Stop Loss'
            
            print(f"🚨 EMERGENCY STOP LOSS TRIGGERED @ ₹{current_price} (Algorithm SL: ₹{emergency_sl}, Loss: ₹{abs(profit):.2f})")
            
            sell_executed = execute_auto_sell(position, reason=reason)
            if sell_executed:
                position['sell_triggered'] = True
                position['waiting_for_autobuy'] = True
                
                # 🎯 CONFIRMATION RE-ENTRY: Always re-enter at entry price
                position['last_stop_loss_price'] = entry_price
                position['mode'] = f'Waiting for Confirmation Re-entry at ₹{entry_price}'
                
                print(f"🎯 EMERGENCY SELL COMPLETE: Will re-enter at ₹{entry_price}")
                return True
        
        return False
    
    # 📊 RULE-BASED ALGORITHM MONITORING
    print(f"🔍 MONITORING: Entry ₹{entry_price} | Current ₹{current_price} | SL ₹{calculated_sl}")
    
    # 🚨 STOP LOSS TRIGGER - Enhanced for both profit targets and stop losses
    manual_sl_active = position.get('manual_stop_loss_set', False)
    manual_sl_value = position.get('stop_loss_price', 0)
    
    print(f"🔍 SL TRIGGER CHECK: Current ₹{current_price} vs SL ₹{calculated_sl} | Manual SL Active: {manual_sl_active} (₹{manual_sl_value})")
    
    # FIXED: Enhanced trigger logic for advanced algorithm
    trigger_condition = False
    if manual_sl_active:
        # 🎯 TRAILING STOP LOSS: Manual SL works as trailing stop
        # Step 1: Check if price has crossed ABOVE manual SL (arm it)
        manual_sl_armed = position.get('manual_sl_armed', False)
        
        if not manual_sl_armed and current_price > manual_sl_value:
            position['manual_sl_armed'] = True
            print(f"   ✅ MANUAL SL ARMED: Price ₹{current_price} crossed above SL ₹{manual_sl_value}")
            trigger_condition = False
        # Step 2: If armed and price crosses BELOW manual SL → SELL
        elif manual_sl_armed and current_price < manual_sl_value:
            trigger_condition = True
            print(f"   🎯 TRAILING SL TRIGGER: Price ₹{current_price} dropped below armed SL ₹{manual_sl_value}")
        else:
            trigger_condition = False
            status = "ARMED - waiting for drop" if manual_sl_armed else "UNARMED - waiting for price to cross above"
            print(f"   Manual SL ₹{manual_sl_value}: {status}")
    else:
        # Algorithm stop loss: use calculated_sl (only this should trigger sells)
        trigger_condition = current_price < calculated_sl
        print(f"   Algorithm SL Trigger: {current_price} < {calculated_sl} = {trigger_condition}")
    
    if (trigger_condition and 
        calculated_sl > 0 and 
        not position.get('waiting_for_autobuy', False) and
        not position.get('sell_triggered', False)):
        
        profit = current_price - entry_price
        reason = 'Rule-Based Trailing SL' if profit > 0 else 'Rule-Based Stop Loss'
        
        print(f"🚨 RULE STOP LOSS TRIGGERED @ ₹{current_price} (SL: ₹{calculated_sl}, Profit: ₹{profit:.2f}, Reason: {reason})")
        
        sell_executed = execute_auto_sell(position, reason=reason)
        if sell_executed:
            position['sell_triggered'] = True
            position['waiting_for_autobuy'] = True
            
            # 🎯 CONFIRMATION RE-ENTRY: Always re-enter at entry price (₹100)
            position['last_stop_loss_price'] = entry_price
            position['mode'] = f'Waiting for Confirmation Re-entry at ₹{entry_price}'
            
            print(f"🎯 CONFIRMATION RE-ENTRY SET: Will re-enter at ₹{entry_price}")
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
            # Create a copy to avoid the SettingWithCopyWarning
            df_copy = df.copy()
            for col in numeric_columns:
                if col in df_copy.columns:
                    df_copy.loc[:, col] = pd.to_numeric(df_copy[col], errors='coerce').fillna(0)
            return df_copy.round(2).to_dict('records')

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


def sync_positions_with_zerodha():
    """
    🛡️ CRITICAL CIRCUIT BREAKER: Sync app positions with Zerodha actual positions
    Prevents infinite buy-sell loops when user manually closes position in Zerodha app
    
    Returns: dict with tradingsymbol -> quantity mapping from Zerodha
    """
    if app_state.get('paper_trading_enabled', True):
        print(f"[SYNC] Paper trading mode - skipping Zerodha sync")
        return {}
    
    if not app_state.get('kite'):
        print(f"[SYNC] ⚠️ Kite not initialized - cannot sync positions")
        return {}
    
    try:
        print(f"[SYNC] 🔄 Fetching live positions from Zerodha...")
        positions = app_state['kite'].positions()
        
        # Extract net positions (actual holdings)
        net_positions = positions.get('net', [])
        
        # Build map of tradingsymbol -> quantity
        zerodha_positions = {}
        for pos in net_positions:
            symbol = pos.get('tradingsymbol', '')
            qty = pos.get('quantity', 0)
            if qty != 0:  # Only track non-zero positions
                zerodha_positions[symbol] = qty
                print(f"[SYNC] ✅ Zerodha position: {symbol} = {qty} qty")
        
        print(f"[SYNC] Total Zerodha positions: {len(zerodha_positions)}")
        return zerodha_positions
        
    except Exception as e:
        print(f"[SYNC] ❌ Error fetching Zerodha positions: {e}")
        return {}

def execute_auto_sell(position, reason='Stop Loss'):
    """Execute auto sell for both Paper Trading and Live Trading modes"""
    
    # 🚨 CRITICAL: STRONGEST DOUBLE SELL PREVENTION
    # Check multiple flags to absolutely prevent duplicate sells
    position_id = position.get('id', 'unknown')
    strike = position.get('strike', 'unknown')
    option_type = position.get('option_type', position.get('type', 'unknown'))
    
    # Check if already sold or in progress
    if position.get('sell_in_progress', False):
        print(f"⚠️ DUPLICATE SELL PREVENTED (IN PROGRESS): {strike} {option_type} (ID: {position_id})")
        return False
    
    if position.get('sell_triggered', False):
        print(f"⚠️ DUPLICATE SELL PREVENTED (ALREADY TRIGGERED): {strike} {option_type} (ID: {position_id})")
        return False
    
    if position.get('sold', False) or position.get('manual_sold', False):
        print(f"⚠️ DUPLICATE SELL PREVENTED (ALREADY SOLD): {strike} {option_type} (ID: {position_id})")
        return False
    
    # Check quantity - if 0, position already sold
    qty = position.get('qty', position.get('quantity', 0))
    if qty == 0:
        print(f"⚠️ SELL PREVENTED (ZERO QUANTITY): {strike} {option_type} (ID: {position_id})")
        return False

    # 🔒 IMMEDIATELY mark sell in progress to prevent race conditions
    position['sell_in_progress'] = True
    print(f"🔒 SELL LOCK ACQUIRED: {strike} {option_type} (ID: {position_id})")

    sell_price = position['current_price']
    
    # 🎯 TRAILING SL: For armed manual SL, use manual SL price
    manual_sl_armed = position.get('manual_sl_armed', False)
    manual_sl_active = position.get('manual_stop_loss_set', False)
    
    if 'Emergency Stop Loss' in reason or 'Stop Loss' in reason:
        if manual_sl_active and manual_sl_armed:
            # Trailing SL triggered - use manual SL price
            sell_price = position.get('stop_loss_price', sell_price)
            print(f"🎯 TRAILING SL SELL: Using armed manual SL ₹{sell_price}")
        elif manual_sl_active and not manual_sl_armed:
            # Manual SL not armed - use algorithm SL
            sell_price = position.get('advanced_stop_loss', position['current_price'])
            print(f"🛡️ ALGORITHM SL SELL: Using algorithm SL ₹{sell_price} (manual SL not armed)")
        elif 'Emergency Stop Loss' in reason:
            # No manual SL - use stop loss price
            sell_price = position.get('stop_loss_price', sell_price)
            print(f"🛡️ EMERGENCY SELL: Using stop loss price ₹{sell_price}")
    
    # For manual stop loss, also use the stop loss price for deterministic fills
    if 'Manual Stop Loss' in reason:
        sell_price = position.get('stop_loss_price', sell_price)
        print(f"🛡️ MANUAL SL SELL: Using stop loss price ₹{sell_price} instead of current price ₹{position['current_price']}")
    
    # Check if we're in paper trading mode
    if app_state['paper_trading_enabled']:
        # Paper Trading Mode - Execute virtual sell
        buy_price = position.get('buy_price', position.get('average_price', 0))
        quantity = position.get('quantity', position.get('qty', 0))
        
        pnl = (sell_price - buy_price) * quantity
        sell_value = sell_price * quantity
        
        # Add to paper wallet
        app_state['paper_wallet_balance'] += sell_value
        
        # 🚨 FIX: Only remove position for manual sells, keep for stop loss sells for auto buy monitoring
        if 'Stop Loss' not in reason:
            # Manual sell - remove completely
            if position in app_state['paper_positions']:
                app_state['paper_positions'].remove(position)
        
        # Add to paper trade history
        trade = {
            'buy_price': buy_price,
            'sell_price': sell_price,
            'price': sell_price,  # Add this for frontend compatibility
            'quantity': quantity,
            'qty': quantity,  # Add this for frontend compatibility
            'lots': position.get('lots', 1),
            'pnl': pnl,
            'pnl_percentage': (pnl / (buy_price * quantity)) * 100 if buy_price > 0 else 0,
            'strike': position['strike'],
            'option_type': option_type,
            'type': option_type,  # Add this for frontend compatibility
            'action': 'Sell',  # Add action field
            'timestamp': get_ist_timestamp(),
            'time': get_ist_time_formatted(),  # IST formatted time
            'reason': reason
        }
        app_state['paper_trade_history'].append(trade)
        
        # Emit real-time trade history update for auto sell
        socketio.emit('trade_history_update', {
            'trade': trade,
            'total_trades': len(app_state['paper_trade_history'])
        })
        
        # Add to paper orders
        order = {
            'id': f"paper_auto_sell_{len(app_state['paper_orders'])}_{int(time.time())}",
            'type': 'SELL',
            'strike': position['strike'],
            'option_type': option_type,
            'price': sell_price,
            'quantity': quantity,
            'lots': position.get('lots', 1),
            'total_value': sell_value,
            'pnl': pnl,
            'stop_loss_price': position.get('stop_loss_price', None),  # Always include stop loss for UI
            'timestamp': get_ist_timestamp(),
            'status': 'COMPLETE',
            'reason': reason
        }
        app_state['paper_orders'].append(order)
        
        print(f"📄 {reason.upper()}: {position.get('lots', 1)} lot(s) of {option_type} {position['strike']} @ ₹{sell_price:.2f} (P&L: ₹{pnl:.2f})")
        
        # For stop loss in paper mode, set up for auto-buy
        if 'Stop Loss' in reason:
            # 🆕 ADVANCED LOGIC: Auto-buy only on LOSS, Exit on profit/break-even
            buy_price = position.get('buy_price', position.get('average_price', 0))
            
            if sell_price < buy_price:
                # 📉 LOSS STOP LOSS: Auto setup for re-entry (recovery mode)
                position['last_stop_loss_price'] = sell_price  # Auto buy at same sell price
                position['waiting_for_autobuy'] = True
                position['mode'] = f'Auto-Sell (Waiting for Auto-Buy at ₹{position["last_stop_loss_price"]})'
                print(f"📉 LOSS STOP LOSS: Buy ₹{buy_price} → Sell ₹{sell_price} (Loss: ₹{buy_price - sell_price:.2f})")
                print(f"🎯 AUTO BUY SETUP: Will trigger when price reaches ₹{position['last_stop_loss_price']} (recovery mode)")
                
            else:
                # ✅ PROFIT/BREAK-EVEN STOP LOSS: COMPLETE EXIT (No Auto-Buy)
                profit_loss = sell_price - buy_price
                if profit_loss > 0:
                    print(f" PROFIT STOP LOSS: Buy ₹{buy_price} → Sell ₹{sell_price} (Profit: ₹{profit_loss:.2f})")
                    position['status'] = 'EXITED_PROFITABLE'
                    position['exit_reason'] = 'Profit Stop Loss - Complete Exit'
                else:
                    print(f" BREAK-EVEN STOP LOSS: Buy ₹{buy_price} → Sell ₹{sell_price} (No P&L)")
                    position['status'] = 'EXITED_BREAKEVEN'
                    position['exit_reason'] = 'Break-Even Stop Loss - Complete Exit'
                
                position['mode'] = f'POSITION EXITED (P&L: ₹{profit_loss:.2f})'
                position['waiting_for_autobuy'] = False  # No auto-buy on profit/break-even
                print(f"✅ POSITION EXITED: {option_type} {position['strike']} closed - No auto-buy")
            
            # Common stop loss processing
            position['realized_pnl'] = pnl
            position['total_pnl'] = position.get('total_pnl', 0) + pnl
            position['auto_sell_count'] = position.get('auto_sell_count', 0) + 1
            position['sell_triggered'] = True

            # 🚨 CRITICAL FIX: Store original quantity before resetting to zero
            position['original_quantity'] = position.get('quantity', position.get('qty', 0))
            position['pnl'] = 0.0  # Reset current P&L to zero
            position['pnl_percentage'] = 0.0  # Reset P&L percentage
            position['quantity'] = 0  # Set quantity to 0 to show position is sold
            position['current_price'] = sell_price  # Keep current price for reference

            print(f"📊 Position waiting: Strike {position['strike']} {option_type} | Quantity: {position['original_quantity']}")

            # 🚨 CRITICAL FIX: For stop loss sells, ensure position stays in paper_positions for monitoring
            if position not in app_state['paper_positions']:
                app_state['paper_positions'].append(position)
                print(f"📋 POSITION KEPT IN MONITORING: {position['strike']} {option_type} will be monitored")
        else:
            # For manual sell, completely remove the position
            position['sold'] = True
            position['manual_sold'] = True
            
            # Remove from monitoring for manual sells
            if position in app_state['paper_positions']:
                app_state['paper_positions'].remove(position)
                print(f"🗑️ POSITION REMOVED: {position['strike']} {option_type} (manual sell)")

        position['sell_in_progress'] = False
        return True
    
    # LIVE TRADING MODE - Execute Zerodha order
    print(f"🏦 LIVE TRADING AUTO SELL: {strike} {option_type} @ ₹{sell_price}")
    print(f"🔍 DEBUG - Position details: {position}")
    print(f"🔍 DEBUG - Kite connection status: {app_state.get('kite') is not None}")
    print(f"🔍 DEBUG - Paper trading enabled: {app_state.get('paper_trading_enabled', False)}")
    
    #  Verify position exists in Zerodha before auto-sell
    print(f"[ZERODHA VERIFICATION] Checking if position exists in Zerodha before auto-sell...")
    
    # Build tradingsymbol for verification
    symbol = position.get('symbol', '')
    expiry = position.get('expiry', '')
    
    # Handle expiry format
    if isinstance(expiry, dict):
        expiry = expiry.get('value', '') if expiry else ''
    elif not isinstance(expiry, str):
        expiry = str(expiry) if expiry else ''
    
    # Convert expiry to YYMMDD format
    try:
        if '-' in expiry:
            year, month, day = expiry.split('-')
            yy = year[-2:]
            expiry_td = f"{yy}{month}{day}"
        else:
            expiry_td = expiry
    except Exception as e:
        print(f"[ZERODHA VERIFICATION] Expiry parse error: {e}")
        expiry_td = expiry
    
    # Build TrueData symbol and convert to Zerodha
    td_symbol = f"{symbol}{expiry_td}{int(strike)}{option_type}"
    
    # 🔥 FIX: Use get_zerodha_symbol FIRST (more reliable)
    tradingsymbol, token, error = get_zerodha_symbol(td_symbol)
    if not tradingsymbol:
        # Fallback to td_to_zerodha_symbol
        tradingsymbol = td_to_zerodha_symbol(td_symbol)
    
    if not tradingsymbol:
        print(f"[ZERODHA VERIFICATION] Failed to convert symbol: {td_symbol}")
        position['sell_in_progress'] = False
        return False
    
    # Fetch current Zerodha positions
    try:
        positions_data = app_state['kite'].positions()
        zerodha_positions = positions_data.get('net', [])
        
        # Check if position exists in Zerodha
        position_exists = False
        zerodha_qty = 0
        
        for z_pos in zerodha_positions:
            if z_pos['tradingsymbol'] == tradingsymbol:
                zerodha_qty = int(z_pos.get('quantity', 0))
                if zerodha_qty > 0:
                    position_exists = True
                    print(f"[ZERODHA VERIFICATION] Position found in Zerodha: {tradingsymbol} = {zerodha_qty} qty")
                    break
        
        if not position_exists:
            print(f"[ZERODHA VERIFICATION]  POSITION NOT FOUND IN ZERODHA: {tradingsymbol}")
            print(f"[ZERODHA VERIFICATION] User may have manually closed this position in Zerodha app")
            print(f"[ZERODHA VERIFICATION] Auto-removing position from monitoring to prevent infinite loops")
            
            # Mark position as manually sold and remove from auto_positions
            position['manual_sold'] = True
            position['sold'] = True
            position['sell_in_progress'] = False
            position['zerodha_verification_failed'] = True
            position['removal_reason'] = 'Position not found in Zerodha - likely closed manually'
            
            if position in app_state['auto_positions']:
                app_state['auto_positions'].remove(position)
                print(f"[ZERODHA VERIFICATION] Removed position from auto_positions")
            
            # Record in trade history
            app_state['trade_history'].append({
                'action': 'Zerodha Verification Failed - Position Removed',
                'type': option_type,
                'strike': strike,
                'qty': 0,
                'price': sell_price,
                'pnl': 0,
                'position_id': position.get('id', 'unknown'),
                'order_status': 'REMOVED: Position not found in Zerodha',
                'time': dt.now().strftime('%Y-%m-%d %H:%M:%S')
            })
            
            return False
        
        # Verify quantity matches
        local_qty = position.get('qty', position.get('quantity', 0))
        if zerodha_qty != local_qty:
            print(f"[ZERODHA VERIFICATION] ⚠️ Quantity mismatch! Local: {local_qty}, Zerodha: {zerodha_qty}")
            print(f"[ZERODHA VERIFICATION] Adjusting local quantity to match Zerodha")
            position['qty'] = zerodha_qty
            position['quantity'] = zerodha_qty
        
    except Exception as e:
        print(f"[ZERODHA VERIFICATION] ❌ CRITICAL: Failed to verify position: {e}")
        print(f"[ZERODHA VERIFICATION] 🚫 BLOCKING AUTO-SELL: Cannot verify position exists in Zerodha")
        print(f"[ZERODHA VERIFICATION] This prevents selling positions that may not exist")
        
        # 🚨 CRITICAL: Block auto-sell if verification fails
        position['sell_in_progress'] = False
        position['zerodha_verification_error'] = str(e)
        
        # Record in trade history
        app_state['trade_history'].append({
            'action': 'Auto-Sell Blocked - Zerodha Verification Failed',
            'type': option_type,
            'strike': strike,
            'qty': 0,
            'price': sell_price,
            'pnl': 0,
            'position_id': position.get('id', 'unknown'),
            'order_status': f'BLOCKED: Verification error - {str(e)}',
            'time': dt.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        
        return False  # 🚨 BLOCK auto-sell if we can't verify position
    
    # ✅ VERIFICATION PASSED - Position exists in Zerodha, proceed with auto-sell
    print(f"[ZERODHA VERIFICATION] ✅✅✅ VERIFICATION PASSED - Position active in Zerodha")
    print(f"[ZERODHA VERIFICATION] Tradingsymbol: {tradingsymbol}, Quantity: {zerodha_qty}")
    print(f"[ZERODHA VERIFICATION] Proceeding with auto-sell execution...")
    
    qty = position.get('qty', position.get('quantity', 0))
    pnl = (sell_price - position['buy_price']) * qty
    
    print(f"🔍 DEBUG - Quantity: {qty}, Buy Price: {position['buy_price']}, PnL: {pnl}")
    
    # CRITICAL: Cancel protective SL order if exists (prevent double sell)
    protective_sl_order_id = position.get('protective_sl_order_id')
    if protective_sl_order_id and app_state.get('kite'):
        try:
            def cancel_protective_sl():
                app_state['kite'].cancel_order(
                    variety=app_state['kite'].VARIETY_REGULAR,
                    order_id=protective_sl_order_id
                )
                return True
            
            cancel_success, _, cancel_error = execute_with_session_retry(
                cancel_protective_sl,
                f"Cancel Protective SL {protective_sl_order_id}"
            )
            
            if cancel_success:
                print(f"🗑️ CANCELLED PROTECTIVE SL: {protective_sl_order_id} (before auto-sell)")
                position.pop('protective_sl_order_id', None)
            else:
                print(f"⚠️ Could not cancel protective SL {protective_sl_order_id}: {cancel_error}")
        except Exception as e:
            print(f"⚠️ Error canceling protective SL: {e}")

    # Place Zerodha sell order with automatic retry on session failure
    def place_auto_sell_order():
        """Inner function to place auto sell order"""
        print(f"🔍 DEBUG - Entering place_auto_sell_order()")
        print(f"🔍 DEBUG - Position data: strike={position['strike']}, type={position['type']}, qty={position['qty']}")
        
        symbol = position['symbol']
        strike = position['strike']
        option_type = position['type']
        expiry = position.get('expiry', '')
        
        print(f"🔍 DEBUG - Symbol components: symbol={symbol}, strike={strike}, type={option_type}, expiry={expiry}")
        
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
            raise Exception(f"Expiry parse error: {e}")
        
        # Build TrueData symbol and convert to Zerodha format
        td_symbol = f"{symbol}{expiry_td}{int(strike)}{option_type}"
        print(f"[DEBUG] AUTO SELL - Built TrueData symbol: {td_symbol}")
        print(f"[DEBUG] AUTO SELL - Expiry details: original={expiry}, parsed_td={expiry_td}")
        
        # 🔥 FIX: Use get_zerodha_symbol FIRST (more reliable) instead of td_to_zerodha_symbol
        print(f"[DEBUG] AUTO SELL - Converting using get_zerodha_symbol (primary method)...")
        tradingsymbol, token, error = get_zerodha_symbol(td_symbol)
        
        if not tradingsymbol:
            # Fallback to td_to_zerodha_symbol if get_zerodha_symbol fails
            print(f"[DEBUG] AUTO SELL - get_zerodha_symbol failed, trying td_to_zerodha_symbol as fallback...")
            tradingsymbol = td_to_zerodha_symbol(td_symbol)
            
            if not tradingsymbol:
                print(f"[ERROR] AUTO SELL - Both conversion methods failed for: {td_symbol}")
                print(f"[ERROR] AUTO SELL - Error: {error}")
                raise Exception(f"Zerodha symbol conversion failed: {error}")
        
        print(f"[DEBUG] AUTO SELL - Placing order for: {tradingsymbol}")
        
        # CRITICAL FIX: ALWAYS use MARKET order for auto sell (same as manual sell)
        # SL orders don't execute immediately - we want instant execution like manual sell
        order_type = app_state['kite'].ORDER_TYPE_MARKET
        print(f"🔍 DEBUG - Using MARKET order for immediate execution (same as manual sell)")
        print(f"🔍 DEBUG - Order type determined: MARKET")
        print(f"🔍 DEBUG - About to place order with params...")
        
        # Place the order with all required parameters
        order_params = {
            'variety': app_state['kite'].VARIETY_REGULAR,
            'exchange': app_state['kite'].EXCHANGE_NFO,
            'tradingsymbol': tradingsymbol,
            'transaction_type': app_state['kite'].TRANSACTION_TYPE_SELL,
            'quantity': position['qty'],
            'order_type': order_type,
            'product': app_state['kite'].PRODUCT_MIS,
            'validity': app_state['kite'].VALIDITY_DAY  # Required parameter
        }
        
        print(f"🔍 DEBUG - Order params: {order_params}")
        print(f"🔍 DEBUG - Calling kite.place_order()...")
        
        order_id = app_state['kite'].place_order(**order_params)
        
        print(f"[SUCCESS] ✅ AUTO SELL order placed: {order_id}")
        print(f"🔍 DEBUG - Order placement successful, returning order_id: {order_id}")
        return order_id
    
    # Execute with automatic session retry
    print(f"🔍 DEBUG - About to execute place_auto_sell_order with session retry...")
    success, order_id, error_msg = execute_with_session_retry(
        place_auto_sell_order, 
        f"Auto Sell {position['strike']} {position['type']}"
    )
    
    print(f"🔍 DEBUG - Session retry result: success={success}, order_id={order_id}, error={error_msg}")
    
    if success:
        order_status = f"✅ Order ID: {order_id}"
        print(f"[SUCCESS] ✅✅✅ AUTO SELL ORDER PLACED SUCCESSFULLY: {order_id}")
        print(f"[SUCCESS] Strike: {position['strike']}, Type: {position['type']}, Price: ₹{sell_price}")
    else:
        order_status = f"❌ {error_msg}"
        print(f"[ERROR] ❌❌❌ AUTO SELL FAILED after retries: {error_msg}")
        print(f"[ERROR] Strike: {position['strike']}, Type: {position['type']}, Price: ₹{sell_price}")

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

    # Only set to waiting for auto buy if this is a stop loss trigger, not manual sell or market close
    if 'Stop Loss' in reason and 'Market Close' not in reason:
        # 🆕 LIVE TRADING: Auto-buy only on LOSS, Exit on profit/break-even
        buy_price = position.get('buy_price', position.get('average_price', 0))
        
        if sell_price < buy_price:
            # 📉 LOSS STOP LOSS in LIVE TRADING: Auto setup for re-entry (recovery mode)
            position['last_stop_loss_price'] = sell_price  # Auto buy at same sell price
            position['waiting_for_autobuy'] = True
            position['mode'] = f'Live Auto-Sell (Waiting for Auto-Buy at ₹{sell_price})'
            print(f"📉 LIVE LOSS STOP LOSS: Buy ₹{buy_price} → Sell ₹{sell_price} (Loss: ₹{buy_price - sell_price:.2f})")
            print(f"🎯 LIVE AUTO BUY SETUP: Will trigger when price reaches ₹{position['last_stop_loss_price']} (recovery mode)")
            
        else:
            # ✅ PROFIT/BREAK-EVEN STOP LOSS in LIVE TRADING: COMPLETE EXIT
            profit_loss = sell_price - buy_price
            if profit_loss > 0:
                print(f"💰 LIVE PROFIT STOP LOSS: Buy ₹{buy_price} → Sell ₹{sell_price} (Profit: ₹{profit_loss:.2f})")
                position['status'] = 'LIVE_EXITED_PROFITABLE'
                position['exit_reason'] = 'Live Profit Stop Loss - Complete Exit'
            else:
                print(f"⚖️ LIVE BREAK-EVEN STOP LOSS: Buy ₹{buy_price} → Sell ₹{sell_price} (No P&L)")
                position['status'] = 'LIVE_EXITED_BREAKEVEN'
                position['exit_reason'] = 'Live Break-Even Stop Loss - Complete Exit'
            
            position['mode'] = f'LIVE EXITED (P&L: ₹{profit_loss:.2f})'
            position['waiting_for_autobuy'] = False  # No auto-buy on profit/break-even
            print(f"✅ LIVE POSITION EXITED: {position['type']} {position['strike']} closed - No auto-buy")
        
        # Common live trading stop loss processing
        position['realized_pnl'] = pnl
        position['total_pnl'] += pnl
        position['auto_sell_count'] += 1
        position['sell_in_progress'] = False
        # Set sell_triggered after trade recording and count increment to prevent duplicates
        position['sell_triggered'] = True
        # For auto sell, don't set sold=True as it should allow auto buy later
        
        #store quantity before sell
        if 'original_quantity' not in position or position.get('original_quantity', 0) == 0:
            position['original_quantity'] = qty  # Store the quantity we just sold
            print(f"STORED ORIGINAL QUANTITY: {qty} for auto-buy recovery")
       
        
        # Reset quantity to 0 to show position is sold in UI
        position['qty'] = 0
        position['quantity'] = 0
        
        print(f"📊 Live position status: Strike {position['strike']} {position['type']} | Qty: {position['qty']} | Waiting for auto-buy: {position.get('waiting_for_autobuy', False)}")
        print(f"🔴 LIVE AUTO SELL: {position['strike']} {position['type']} @ ₹{sell_price} | P&L: ₹{pnl:.2f} | {order_status}")
    else:
        # Manual sell or Market Close Exit - mark as sold and remove from monitoring
        position['manual_sold'] = True
        position['sell_in_progress'] = False
        position['sell_triggered'] = True
        position['sold'] = True  # Mark as sold for manual selld
        position['waiting_for_autobuy'] = False  # CRITICAL: Stop any auto buy attempts
        position['qty'] = 0  # Reset quantity
        position['quantity'] = 0
        
        if 'Market Close' in reason:
            position['mode'] = 'Market Close Exit - Position Closed'
            print(f"⏰ MARKET CLOSE EXIT: {position['strike']} {position['type']} @ ₹{sell_price} | P&L: ₹{pnl:.2f}")
        else:
            position['mode'] = 'Manual Sell - Position Closed'
            print(f"🔴 MANUAL SELL: {position['strike']} {position['type']} @ ₹{sell_price} | P&L: ₹{pnl:.2f} | Position will be removed")
        
        # 🚨 CRITICAL FIX: Remove position from auto_positions list for non-stop-loss sells
        if position in app_state['auto_positions']:
            app_state['auto_positions'].remove(position)
            print(f"🗑️ REMOVED from auto_positions: {position['strike']} {position['type']} (manual/market close sell)")

    return True


def execute_manual_sell_auto_position(strike, option_type, symbol='NIFTY'):
    """Execute manual sell and completely remove auto position to prevent auto buy"""
    removed_positions = []
    
    for auto_pos in app_state['auto_positions'][:]:  # Create a copy to iterate safely
        if (float(auto_pos['strike']) == float(strike) and 
            auto_pos['type'] == option_type and
            auto_pos['symbol'] == symbol):
            
            # CRITICAL: Check if already sold or in progress
            if auto_pos.get('sell_in_progress', False) or auto_pos.get('sold', False) or auto_pos.get('manual_sold', False):
                print(f"⚠️ DUPLICATE MANUAL SELL PREVENTED: {strike} {option_type} already sold or in progress")
                continue
            
            # Mark sell in progress immediately to prevent race conditions
            auto_pos['sell_in_progress'] = True
            
            # 🛡️ ZERODHA: Cancel protective SL order if exists
            protective_sl_order_id = auto_pos.get('protective_sl_order_id')
            if protective_sl_order_id and app_state.get('kite') and not app_state.get('paper_trading_enabled', False):
                try:
                    def cancel_protective_sl():
                        app_state['kite'].cancel_order(
                            variety=app_state['kite'].VARIETY_REGULAR,
                            order_id=protective_sl_order_id
                        )
                        return True
                    
                    cancel_success, _, cancel_error = execute_with_session_retry(
                        cancel_protective_sl,
                        f"Cancel Protective SL {protective_sl_order_id}"
                    )
                    
                    if cancel_success:
                        print(f"🗑️ CANCELLED PROTECTIVE SL: {protective_sl_order_id} (manual sell)")
                        auto_pos.pop('protective_sl_order_id', None)
                    else:
                        print(f"⚠️ Could not cancel protective SL: {cancel_error}")
                except Exception as e:
                    print(f"⚠️ Error canceling protective SL: {e}")
            
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
                'order_status': 'Auto position removed',
                'time': dt.now().strftime('%Y-%m-%d %H:%M:%S')
            })
            
            # Remove position completely
            app_state['auto_positions'].remove(auto_pos)
            removed_positions.append(auto_pos)
            print(f"🗑️ COMPLETELY REMOVED AUTO POSITION: {strike} {option_type} (Manual Sell) - No Auto Buy Will Trigger")
    
    return len(removed_positions)


def execute_auto_buy(position):
    """Execute auto buy for both Paper Trading and Live Trading modes"""
    
    # EMERGENCY CIRCUIT BREAKER - Step 1: Check if circuit breaker is enabled
    circuit_breaker_enabled = app_state['auto_trading_config'].get('circuit_breaker_enabled', True)
    
    if circuit_breaker_enabled:
        # STEP 1: POSITION SYNC - Verify position exists in Zerodha (Live Trading only)
        if not app_state.get('paper_trading_enabled', True) and app_state['auto_trading_config'].get('position_sync_enabled', True):
            print(f"[CIRCUIT BREAKER] 🔍 Syncing with Zerodha before auto-buy...")
            zerodha_positions = sync_positions_with_zerodha()
            
            # Build tradingsymbol from position for verification
            symbol = position.get('symbol', '')
            strike = position.get('strike', 0)
            option_type = position.get('type', position.get('option_type', ''))
            expiry = position.get('expiry', '')
            
            # Handle expiry format
            if isinstance(expiry, dict):
                expiry = expiry.get('value', '') if expiry else ''
            elif not isinstance(expiry, str):
                expiry = str(expiry) if expiry else ''
            
            # Convert expiry to YYMMDD format for TrueData
            try:
                if '-' in expiry:
                    year, month, day = expiry.split('-')
                    yy = year[-2:]
                    expiry_td = f"{yy}{month}{day}"
                else:
                    expiry_td = expiry
            except Exception as e:
                print(f"[CIRCUIT BREAKER] Expiry parse error: {e}")
                expiry_td = expiry
            
            # Build TrueData symbol and convert to Zerodha
            td_symbol = f"{symbol}{expiry_td}{int(strike)}{option_type}"
            
            # 🔥 FIX: Use get_zerodha_symbol FIRST (more reliable)
            tradingsymbol, token, error = get_zerodha_symbol(td_symbol)
            if not tradingsymbol:
                # Fallback to td_to_zerodha_symbol
                tradingsymbol = td_to_zerodha_symbol(td_symbol)
            
            if tradingsymbol:
                # Check if position exists in Zerodha
                zerodha_qty = zerodha_positions.get(tradingsymbol, 0)
                
                if zerodha_qty == 0:
                    print(f"[CIRCUIT BREAKER]  POSITION SYNC BLOCK: {tradingsymbol} not found in Zerodha!")
                    print(f"[CIRCUIT BREAKER] User may have manually closed this position in Zerodha app")
                    print(f"[CIRCUIT BREAKER] Removing position from auto_positions to prevent infinite loop")
                    
                    # Mark position as manually sold and remove from auto_positions
                    position['manual_sold'] = True
                    position['circuit_breaker_triggered'] = 'POSITION_NOT_IN_ZERODHA'
                    if position in app_state['auto_positions']:
                        app_state['auto_positions'].remove(position)
                    
                    # Record in trade history
                    app_state['trade_history'].append({
                        'action': 'Circuit Breaker: Position Sync Block',
                        'type': option_type,
                        'strike': strike,
                        'qty': 0,
                        'price': position.get('current_price', 0),
                        'pnl': 0,
                        'position_id': position.get('id', 'unknown'),
                        'order_status': 'BLOCKED: Position not found in Zerodha',
                        'time': dt.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
                    
                    return False
                else:
                    print(f"[CIRCUIT BREAKER] ✅ Position verified in Zerodha: {tradingsymbol} = {zerodha_qty} qty")
        
        # 🛡️ STEP 2: CYCLE LIMITER - Check max auto cycles per position
        max_cycles = app_state['auto_trading_config'].get('max_auto_cycles_per_position', 3)
        auto_sell_count = position.get('auto_sell_count', 0)
        auto_buy_count = position.get('auto_buy_count', 0)
        total_cycles = auto_sell_count + auto_buy_count
        
        if total_cycles >= max_cycles:
            print(f"[CIRCUIT BREAKER] 🚫 MAX CYCLES EXCEEDED: {total_cycles} >= {max_cycles}")
            print(f"[CIRCUIT BREAKER] Strike: {position.get('strike')}, Type: {position.get('type')}")
            print(f"[CIRCUIT BREAKER] Auto Sells: {auto_sell_count}, Auto Buys: {auto_buy_count}")
            print(f"[CIRCUIT BREAKER] Blocking auto-buy to prevent infinite loop")
            
            # Mark position with circuit breaker and remove from auto_positions
            position['circuit_breaker_triggered'] = 'MAX_CYCLES_EXCEEDED'
            position['waiting_for_autobuy'] = False
            if position in app_state['auto_positions']:
                app_state['auto_positions'].remove(position)
            
            # Record in trade history
            app_state['trade_history'].append({
                'action': 'Circuit Breaker: Max Cycles Exceeded',
                'type': position.get('type', 'unknown'),
                'strike': position.get('strike', 0),
                'qty': 0,
                'price': position.get('current_price', 0),
                'pnl': 0,
                'position_id': position.get('id', 'unknown'),
                'order_status': f'BLOCKED: {total_cycles} cycles >= {max_cycles} limit',
                'time': dt.now().strftime('%Y-%m-%d %H:%M:%S')
            })
            
            return False
        max_loss = app_state['auto_trading_config'].get('max_loss_per_position', 5000)
        total_pnl = position.get('total_pnl', 0)
        realized_pnl = position.get('realized_pnl', 0)
        cumulative_loss = abs(min(total_pnl, realized_pnl, 0))  # Get absolute loss value
        
        if cumulative_loss >= max_loss:
            print(f"[CIRCUIT BREAKER] MAX LOSS EXCEEDED: ₹{cumulative_loss} >= ₹{max_loss}")
            print(f"[CIRCUIT BREAKER] Strike: {position.get('strike')}, Type: {position.get('type')}")
            print(f"[CIRCUIT BREAKER] Total PnL: ₹{total_pnl}, Realized PnL: ₹{realized_pnl}")
            print(f"[CIRCUIT BREAKER] Blocking auto-buy to prevent further losses")
            
            # Mark position with circuit breaker and remove from auto_positions
            position['circuit_breaker_triggered'] = 'MAX_LOSS_EXCEEDED'
            position['waiting_for_autobuy'] = False
            if position in app_state['auto_positions']:
                app_state['auto_positions'].remove(position)
            
            # Record in trade history
            app_state['trade_history'].append({
                'action': 'Circuit Breaker: Max Loss Exceeded',
                'type': position.get('type', 'unknown'),
                'strike': position.get('strike', 0),
                'qty': 0,
                'price': position.get('current_price', 0),
                'pnl': -cumulative_loss,
                'position_id': position.get('id', 'unknown'),
                'order_status': f'BLOCKED: ₹{cumulative_loss} loss >= ₹{max_loss} limit',
                'time': dt.now().strftime('%Y-%m-%d %H:%M:%S')
            })
            
            return False
        
        print(f"[CIRCUIT BREAKER] ✅ All checks passed - Auto-buy allowed")
        print(f"[CIRCUIT BREAKER] Cycles: {total_cycles}/{max_cycles}, Loss: ₹{cumulative_loss}/₹{max_loss}")
    
    # 🚨 CRITICAL: STRONGEST DOUBLE BUY PREVENTION
    position_id = position.get('id', 'unknown')
    strike = position.get('strike', 'unknown')
    option_type = position.get('option_type', position.get('type', 'unknown'))
    
    # Check if manually sold - absolute block
    if position.get('manual_sold', False) or position.get('sold', False):
        print(f"⚠️ AUTO BUY BLOCKED (MANUALLY SOLD): {strike} {option_type} (ID: {position_id})")
        # Remove the position completely if it was manually sold
        if position in app_state['auto_positions']:
            app_state['auto_positions'].remove(position)
        return False
    
    # Check if NOT waiting for auto buy
    if not position.get('waiting_for_autobuy', False):
        print(f"⚠️ AUTO BUY BLOCKED (NOT WAITING): {strike} {option_type} (ID: {position_id})")
        return False
    
    # Check if position already has quantity (already bought)
    current_qty = position.get('qty', position.get('quantity', 0))
    if current_qty > 0:
        print(f"⚠️ AUTO BUY BLOCKED (ALREADY HAS QTY {current_qty}): {strike} {option_type} (ID: {position_id})")
        return False
    
    # 🚨 FIX: Auto buy price depends on phase
    # Phase 1: Buy at manual buy price (not current price!)
    # Phase 2&3: Buy at current price (sell price)
    if position.get('algorithm_phase', 1) == 1:
        # 🚨 CRITICAL: Ensure manual_buy_price exists, use original_buy_price as backup
        manual_price = position.get('manual_buy_price') or position.get('original_buy_price') or position.get('buy_price')
        if manual_price:
            buy_price = manual_price
            print(f"🎯 PHASE 1 AUTO BUY: Using manual buy price ₹{buy_price} instead of current price ₹{position['current_price']}")
        else:
            print(f"❌ ERROR: No manual_buy_price found! Position data: {position}")
            return False
    else:
        buy_price = position['current_price']
        print(f"🎯 PHASE {position.get('algorithm_phase', 1)} AUTO BUY: Using current price ₹{buy_price}")
    
    # Check if we're in paper trading mode
    if app_state['paper_trading_enabled']:
        # Paper Trading Mode - Execute virtual buy
        quantity = position.get('original_quantity', position.get('quantity', position.get('qty', 0)))
        total_cost = quantity * buy_price
        
        # Check if enough balance
        if app_state['paper_wallet_balance'] < total_cost:
            print(f"📄 AUTO BUY FAILED: Insufficient balance. Required: ₹{total_cost:.2f}, Available: ₹{app_state['paper_wallet_balance']:.2f}")
            return False
        
        # Deduct from wallet
        app_state['paper_wallet_balance'] -= total_cost
        
        # Update the original position to continue monitoring instead of creating new position
        position['waiting_for_autobuy'] = False
        position['mode'] = 'Auto-Monitoring (After Auto Buy)'
        position['buy_price'] = buy_price
        
        # 🚨 FIX: For Phase 1, we bought at manual price but current price is market price
        if position.get('algorithm_phase', 1) == 1:
            # Keep current_price as market price for monitoring, but buy_price is manual price
            print(f"🎯 PHASE 1: Auto bought at ₹{buy_price} (manual price), current market price ₹{position['current_price']}")
        else:
            # For Phase 2&3, set current_price to buy_price since we bought at market price
            position['current_price'] = buy_price
            
        position['highest_price'] = buy_price  # Reset highest price for new auto buy
        
        # 🚨 CRITICAL FIX: For Phase 1, maintain original manual buy stop loss
        # Auto buy at manual price, but stop loss stays at manual_buy_price - 10
        if position.get('algorithm_phase', 1) == 1:
            manual_buy_price = position.get('manual_buy_price', buy_price)
            position['stop_loss_price'] = manual_buy_price - 10  # Original manual SL level
            print(f"🎯 PHASE 1: Auto bought at ₹{buy_price}, Stop Loss remains at original ₹{position['stop_loss_price']} (manual ₹{manual_buy_price} - 10)")
        else:
            # Phase 2&3: Normal auto buy stop loss
            volatility_buffer = 15 if position.get('auto_buy_count', 0) > 0 else 10
            position['stop_loss_price'] = buy_price - volatility_buffer
            
        position['original_buy_price'] = buy_price  # Update original buy price for new cycle
        position['minimum_stop_loss'] = position['stop_loss_price']  # Update minimum stop loss
        position['auto_buy_count'] = position.get('auto_buy_count', 0) + 1
        position['quantity'] = quantity  # Restore quantity after auto buy
        position['total_cost'] = total_cost
        position['id'] = f"paper_auto_{len(app_state['paper_positions'])}_{int(time.time())}"
        position['timestamp'] = get_ist_timestamp()
        position['auto_bought'] = True  # Mark as auto bought for trailing logic
        
        # 🚨 COOLDOWN PROTECTION: If auto buy count >= 5 AND cooldown is enabled, move to pending with higher trigger
        if position['auto_buy_count'] >= 5 and app_state.get('cooldown_enabled', True):
            print(f"🚨 COOLDOWN ACTIVATED: Auto buy count {position['auto_buy_count']} >= 5 for {position['strike']} {option_type}")
            
            # Set to pending status
            position['waiting_for_autobuy'] = True
            position['mode'] = 'Cooldown (Auto Buy Count >= 5)'
            
            # Adjust trigger prices 5 points higher
            original_trigger = position.get('last_stop_loss_price', position['stop_loss_price'])
            new_trigger = original_trigger + 5
            position['last_stop_loss_price'] = new_trigger
            position['stop_loss_price'] = new_trigger
            
            # 🎯 RESET AUTO BUY COUNT FOR NEW CYCLE after cooldown
            position['auto_buy_count'] = 0
            
            # Reset quantity to 0 (sold state)
            position['quantity'] = 0
            position['qty'] = 0
            
            print(f"🎯 COOLDOWN: Next auto buy at ₹{new_trigger} (5 points higher) | Stop Loss also at ₹{new_trigger} | Auto buy count reset to 0")
            
            # Record cooldown in trade history
            trade_record_cooldown = {
                'id': position['id'],
                'action': 'Cooldown Activated',
                'type': option_type,
                'option_type': option_type,
                'strike': position['strike'],
                'qty': 0,
                'quantity': 0,
                'price': buy_price,
                'buy_price': buy_price,
                'pnl': 0,
                'total_value': 0,
                'timestamp': get_ist_timestamp(),
                'time': get_ist_time_formatted(),
                'status': 'COOLDOWN',
                'mode': 'Paper Trading',
                'trading_mode': 'paper',
                'reason': f'Cooldown: Next trigger at ₹{new_trigger}'
            }
            
            app_state['paper_trade_history'].append(trade_record_cooldown)
            
            # Emit cooldown update
            socketio.emit('trade_history_update', {
                'trade': trade_record_cooldown,
                'total_trades': len(app_state['paper_trade_history'])
            })
            
            return True  # Return early, don't continue with normal auto buy
        
        # 🚨 CRITICAL: Clear all sold flags after successful auto buy and reset P&L
        position['sold'] = False
        position['manual_sold'] = False
        position['sell_in_progress'] = False
        position['sell_triggered'] = False
        position['pnl'] = 0.0  # Reset P&L to zero for fresh start
        position['pnl_percentage'] = 0.0  # Reset P&L percentage
        
        # 🔥 ENSURE POSITION STAYS IN MONITORING: Add back to paper_positions if not already there
        if position not in app_state['paper_positions']:
            app_state['paper_positions'].append(position)
            print(f"📋 POSITION ADDED TO MONITORING: {position['strike']} {option_type} will continue being monitored")
        
        # Add to paper order history
        order = {
            'id': position['id'],
            'type': 'BUY',
            'action': 'Buy',  # Add action field for frontend
            'strike': position['strike'],
            'option_type': option_type,
            'price': buy_price,
            'buy_price': buy_price,  # Add for consistency
            'quantity': quantity,
            'qty': quantity,  # Add qty field for frontend
            'lots': position.get('lots', 1),
            'total_value': total_cost,
            'stop_loss_price': position['stop_loss_price'],  # Always include stop loss for UI
            'timestamp': position['timestamp'],
            'time': get_ist_time_formatted(),  # IST formatted time
            'status': 'COMPLETE',
            'reason': 'Auto Buy'
        }
        app_state['paper_orders'].append(order)
        
        # Add to trade history for complete tracking
        trade_record = {
            'id': position['id'],
            'action': 'Auto Buy',  # Clearly mark as auto buy
            'type': option_type,
            'option_type': option_type,
            'strike': position['strike'],
            'qty': quantity,
            'quantity': quantity,
            'price': buy_price,
            'buy_price': buy_price,
            'pnl': 0,  # No PnL at buy time
            'total_value': total_cost,
            'timestamp': position['timestamp'],
            'time': dt.now().strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'COMPLETE',
            'mode': 'Paper Trading',
            'trading_mode': 'paper',
            'reason': 'Auto Buy'
        }
        
        app_state['paper_trade_history'].append(trade_record)
        
        # Emit real-time trade history update for auto buy
        socketio.emit('trade_history_update', {
            'trade': trade_record,
            'total_trades': len(app_state['paper_trade_history'])
        })
        
        # 🚨 CRITICAL FIX: Add auto buy position to paper_positions for monitoring
        if position not in app_state['paper_positions']:
            app_state['paper_positions'].append(position)
            print(f"📍 AUTO BUY POSITION ADDED TO MONITORING: {position['strike']} {option_type}")
        
        print(f"📄 AUTO BUY: {position.get('lots', 1)} lot(s) of {option_type} {position['strike']} @ ₹{buy_price:.2f} = ₹{total_cost:.2f}")
        print(f"📍 PAPER AUTO BUY: {position['strike']} {option_type} @ ₹{buy_price} | Stop Loss: ₹{position['stop_loss_price']} (Same as auto sell price)")
        return True
        
    else:
        # Live Trading Mode - Execute Zerodha order
        print(f"🏦 LIVE TRADING AUTO BUY: {strike} {option_type} @ ₹{buy_price}")
        print(f"🔍 DEBUG AUTO BUY - Position details: {position}")
        print(f"🔍 DEBUG AUTO BUY - Kite connection status: {app_state.get('kite') is not None}")
        print(f"🔍 DEBUG AUTO BUY - Paper trading enabled: {app_state.get('paper_trading_enabled', False)}")
        
        # 🚨 CRITICAL FIX: Restore quantity from original_quantity before placing order
        # After auto-sell, qty is set to 0, but we need to restore it for auto-buy
        qty = position.get('original_quantity', position.get('qty', position.get('quantity', 0)))
        
        # If qty is still 0, this is a problem - log and abort
        if qty == 0:
            print(f"❌ LIVE AUTO BUY FAILED: Zero quantity detected!")
            print(f"   Position ID: {position_id}")
            print(f"   Original quantity: {position.get('original_quantity', 'NOT SET')}")
            print(f"   Current qty: {position.get('qty', 0)}")
            return False
        
        cost = qty * buy_price
        
        print(f"🔍 DEBUG AUTO BUY - Quantity: {qty}, Buy Price: {buy_price}, Total Cost: ₹{cost}")

        # Place Zerodha buy order with automatic retry on session failure
        def place_auto_buy_order():
            """Inner function to place auto buy order"""
            print(f"🔍 DEBUG AUTO BUY - Entering place_auto_buy_order()")
            print(f"🔍 DEBUG AUTO BUY - Position data: strike={position['strike']}, type={position['type']}, qty={position.get('qty', 0)}")
            print(f"🔍 DEBUG AUTO BUY - Buy price: ₹{buy_price}")
            print(f"🔍 DEBUG AUTO BUY - Kite connection: {app_state.get('kite') is not None}")
            
            symbol = position['symbol']
            strike = position['strike']
            option_type = position['type']
            expiry = position.get('expiry', '')
            
            print(f"🔍 DEBUG AUTO BUY - Symbol components: symbol={symbol}, strike={strike}, type={option_type}, expiry={expiry}")
            
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
                raise Exception(f"Expiry parse error: {e}")
            
            # Build TrueData symbol and convert to Zerodha format
            td_symbol = f"{symbol}{expiry_td}{int(strike)}{option_type}"
            print(f"[DEBUG] AUTO BUY - Built TrueData symbol: {td_symbol}")
            print(f"[DEBUG] AUTO BUY - Expiry details: original={expiry}, parsed_td={expiry_td}")
            
            # 🔥 FIX: Use get_zerodha_symbol FIRST (more reliable) instead of td_to_zerodha_symbol
            print(f"[DEBUG] AUTO BUY - Converting using get_zerodha_symbol (primary method)...")
            tradingsymbol, token, error = get_zerodha_symbol(td_symbol)
            
            if not tradingsymbol:
                # Fallback to td_to_zerodha_symbol if get_zerodha_symbol fails
                print(f"[DEBUG] AUTO BUY - get_zerodha_symbol failed, trying td_to_zerodha_symbol as fallback...")
                tradingsymbol = td_to_zerodha_symbol(td_symbol)
                
                if not tradingsymbol:
                    print(f"[ERROR] AUTO BUY - Both conversion methods failed for: {td_symbol}")
                    print(f"[ERROR] AUTO BUY - Error: {error}")
                    raise Exception(f"Zerodha symbol conversion failed: {error}")
            
            print(f"[DEBUG] AUTO BUY - Placing order for: {tradingsymbol}")
            print(f"🔍 DEBUG AUTO BUY - Using MARKET order for immediate execution (same as auto sell)")
            print(f"🔍 DEBUG AUTO BUY - About to place BUY order...")
            
            # Place the order with all required parameters
            order_params = {
                'variety': app_state['kite'].VARIETY_REGULAR,
                'exchange': app_state['kite'].EXCHANGE_NFO,
                'tradingsymbol': tradingsymbol,
                'transaction_type': app_state['kite'].TRANSACTION_TYPE_BUY,
                'quantity': qty,  # 🚨 FIX: Use qty variable, not position['qty'] which is 0
                'order_type': app_state['kite'].ORDER_TYPE_MARKET,
                'product': app_state['kite'].PRODUCT_MIS,
                'validity': app_state['kite'].VALIDITY_DAY  # Required parameter
            }
            
            print(f"🔍 DEBUG AUTO BUY - Order params: {order_params}")
            print(f"🔍 DEBUG AUTO BUY - Calling kite.place_order()...")
            
            order_id = app_state['kite'].place_order(**order_params)
            
            print(f"[SUCCESS] ✅ AUTO BUY order placed: {order_id}")
            print(f"🔍 DEBUG AUTO BUY - Order placement successful, returning order_id: {order_id}")
            return order_id
        
        # Execute with automatic session retry
        print(f"🔍 DEBUG AUTO BUY - About to execute place_auto_buy_order with session retry...")
        success, order_id, error_msg = execute_with_session_retry(
            place_auto_buy_order, 
            f"Auto Buy {position['strike']} {position['type']}"
        )
        
        print(f"🔍 DEBUG AUTO BUY - Session retry result: success={success}, order_id={order_id}, error={error_msg}")
        
        if success:
            order_status = f"✅ Order ID: {order_id}"
            print(f"[SUCCESS] ✅✅✅ AUTO BUY ORDER PLACED SUCCESSFULLY: {order_id}")
            print(f"[SUCCESS] Strike: {position['strike']}, Type: {position['type']}, Price: ₹{buy_price}")
        else:
            order_status = f"❌ {error_msg}"
            print(f"[ERROR] ❌❌❌ AUTO BUY FAILED after retries: {error_msg}")
            print(f"[ERROR] Strike: {position['strike']}, Type: {position['type']}, Price: ₹{buy_price}")
            # Return False on failure
            return False

        # 🚨 CRITICAL FIX: Restore quantity after successful buy
        position['qty'] = qty
        position['quantity'] = qty
        
        # Update position
        position['buy_price'] = buy_price
        position['highest_price'] = buy_price
        
        # 🚨 FIX: Auto buy stop loss = auto buy price - 10 (NOT same as sell price)
        position['stop_loss_price'] = buy_price - 10  # Correct: auto buy price - 10
        position['original_buy_price'] = buy_price  # Update original buy price for new cycle
        position['minimum_stop_loss'] = buy_price - 10  # Update minimum stop loss
        position['auto_bought'] = True
        position['mode'] = 'Running'
        position['waiting_for_autobuy'] = False
        
        # Increment auto buy count
        position['auto_buy_count'] = position.get('auto_buy_count', 0) + 1
        
        # 🚨 COOLDOWN PROTECTION: Check individual cooldown setting first, then global cooldown
        individual_cooldown = position.get('individual_cooldown_enabled', True)  # Default: enabled
        global_cooldown = app_state.get('cooldown_enabled', True)
        
        # Apply cooldown only if BOTH individual AND global cooldown are enabled
        if (position['auto_buy_count'] >= 5 and individual_cooldown and global_cooldown):
            # Individual cooldown activated - less verbose logging
            
            # Set to pending status
            position['waiting_for_autobuy'] = True
            position['mode'] = 'Cooldown (Auto Buy Count >= 5)'
            
            # Adjust trigger prices 5 points higher
            original_trigger = position.get('last_stop_loss_price', position['stop_loss_price'])
            new_trigger = original_trigger + 5
            position['last_stop_loss_price'] = new_trigger
            position['stop_loss_price'] = new_trigger
            
            # RESET AUTO BUY COUNT FOR NEW CYCLE after cooldown
            position['auto_buy_count'] = 0
            
            # Reset quantity to 0 (sold state)
            position['qty'] = 0
            position['quantity'] = 0
            
            # Individual cooldown - minimal logging
            
            # Record cooldown in trade history
            app_state['trade_history'].append({
                'action': 'Individual Cooldown Activated',
                'type': position['type'],
                'strike': position['strike'],
                'qty': 0,
                'price': buy_price,
                'pnl': 0,
                'position_id': position['id'],
                'order_status': f'Individual Cooldown: Next trigger at ₹{new_trigger}',
                'time': dt.now().strftime('%Y-%m-%d %H:%M:%S')
            })
            
            return True  # Return early, don't continue with normal auto buy
        elif position['auto_buy_count'] >= 5:
            # Cooldown is disabled (either individually or globally), continue normal trading
            print(f"🎯 COOLDOWN BYPASSED: Auto buy count {position['auto_buy_count']} >= 5 for {position['strike']} {position['type']} but cooldown disabled (Individual: {individual_cooldown}, Global: {global_cooldown})")
            # Continue with normal auto buy (don't reset count or apply cooldown)
        
        # CRITICAL: Clear all sold flags after successful auto buy
        position['sold'] = False
        position['manual_sold'] = False
        position['sell_in_progress'] = False
        position['sell_triggered'] = False

        # 🚨 CRITICAL FIX: Add auto buy position to auto_positions for monitoring (Live Trading)
        if position not in app_state['auto_positions']:
            app_state['auto_positions'].append(position)
            print(f"📍 AUTO BUY POSITION ADDED TO MONITORING: {position['strike']} {position['type']}")

        # Debug print to confirm stop loss is set correctly for auto buy
        print(f"📍 AUTO BUY EXECUTED: {position['strike']} {position['type']} @ ₹{buy_price} | Stop Loss: ₹{position['stop_loss_price']} (Same as auto sell price) | Auto Buy Count: {position['auto_buy_count']}")

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

        print(f"🟢 AUTO BUY: {position['strike']} {position['type']} @ ₹{buy_price} | Stop Loss: ₹{position['stop_loss_price']} (Same as auto sell price) | Auto Buy Count: {position['auto_buy_count']} | {order_status}")
        
        # 🛡️ ZERODHA PROTECTION: Place protective SL order after auto-buy in live trading
        if not app_state['paper_trading_enabled'] and app_state.get('kite') and success:
            try:
                def place_protective_sl_after_buy():
                    """Place protective SL order after successful auto-buy"""
                    symbol = position['symbol']
                    strike = position['strike']
                    option_type = position['type']
                    expiry = position.get('expiry', '')
                    
                    # Handle expiry format
                    if isinstance(expiry, dict):
                        expiry = expiry.get('value', '') if expiry else ''
                    elif not isinstance(expiry, str):
                        expiry = str(expiry) if expiry else ''
                    
                    # Convert expiry
                    try:
                        if '-' in expiry:
                            year, month, day = expiry.split('-')
                            yy = year[-2:]
                            expiry_td = f"{yy}{month}{day}"
                        else:
                            expiry_td = expiry
                    except Exception as e:
                        print(f"[ERROR] Failed to parse expiry: {e}")
                        raise Exception(f"Expiry parse error: {e}")
                    
                    # Build symbol
                    td_symbol = f"{symbol}{expiry_td}{int(strike)}{option_type}"
                    tradingsymbol = td_to_zerodha_symbol(td_symbol)
                    
                    if not tradingsymbol:
                        print(f"[ERROR] Symbol conversion failed: {td_symbol}")
                        raise Exception(f"Symbol conversion failed")
                    
                    print(f"[DEBUG] AUTO-BUY PROTECTIVE SL - Placing SL-M at ₹{position['stop_loss_price']} for {tradingsymbol}")
                    
                    # Place SL-M order with all required parameters
                    sl_order_id = app_state['kite'].place_order(
                        variety=app_state['kite'].VARIETY_REGULAR,
                        exchange=app_state['kite'].EXCHANGE_NFO,
                        tradingsymbol=tradingsymbol,
                        transaction_type=app_state['kite'].TRANSACTION_TYPE_SELL,
                        quantity=qty,  # 🚨 FIX: Use qty variable from outer scope
                        order_type=app_state['kite'].ORDER_TYPE_SLM,
                        trigger_price=position['stop_loss_price'],
                        product=app_state['kite'].PRODUCT_MIS,
                        validity=app_state['kite'].VALIDITY_DAY  # Required parameter
                    )
                    
                    print(f"[SUCCESS] AUTO-BUY PROTECTIVE SL placed: {sl_order_id}")
                    return sl_order_id
                
                # Execute with retry
                sl_success, sl_order_id, sl_error = execute_with_session_retry(
                    place_protective_sl_after_buy,
                    f"Auto-Buy Protective SL {position['strike']} {position['type']}"
                )
                
                if sl_success:
                    position['protective_sl_order_id'] = sl_order_id
                    print(f"🛡️ AUTO-BUY PROTECTIVE SL PLACED: Order ID {sl_order_id} at trigger ₹{position['stop_loss_price']}")
                else:
                    print(f"⚠️ AUTO-BUY PROTECTIVE SL FAILED: {sl_error}")
            
            except Exception as e:
                print(f"⚠️ Exception placing auto-buy protective SL: {e}")
        
        return True

def get_active_positions_count():
    """Helper function to get count of active positions across all trading modes"""
    # Check for active auto positions
    active_auto_positions = [
        pos for pos in app_state.get('auto_positions', [])
        if not pos.get('sold', False) and not pos.get('manual_sold', False)
    ]
    
    # Check for active paper positions (if in paper trading mode)
    active_paper_positions = []
    if app_state.get('paper_trading_enabled', False):
        active_paper_positions = [
            pos for pos in app_state.get('paper_positions', [])
            if pos.get('quantity', 0) > 0
        ]
    
    # Check for active live positions (if in live trading mode)
    active_live_positions = []
    if not app_state.get('paper_trading_enabled', False):
        active_live_positions = [
            pos for pos in app_state.get('zerodha_positions', [])
            if pos.get('quantity', 0) != 0
        ]
    
    return {
        'auto_positions': len(active_auto_positions),
        'paper_positions': len(active_paper_positions),
        'live_positions': len(active_live_positions),
        'total': len(active_auto_positions) + len(active_paper_positions) + len(active_live_positions),
        'details': {
            'auto': active_auto_positions,
            'paper': active_paper_positions,
            'live': active_live_positions
        }
    }

def update_trailing_stop_loss(position, algorithm='simple'):
    """USER REQUIREMENT CORRECTED: SL = buy_price + (steps × 10) [NO MINUS 10]
    🚨 CRITICAL PROTECTION: STOP LOSS NEVER GOES BELOW MINIMUM_STOP_LOSS (original_buy_price - 10)
    🚨 NOTE: This function is ONLY for SIMPLE algorithm. Advanced algorithm has its own logic.
    
    CORRECT FORMULAS:
    - Manual Buy Initial: SL = buy_price - 10
    - Manual Buy Trailing: SL = buy_price + (steps × 10)
    - Auto Buy Initial: SL = auto_buy_price - 10  
    - Auto Buy Trailing: SL = auto_buy_price + (steps × 10)
    """
    # Safety check: This function should only be called for simple algorithm
    if algorithm != 'simple':
        print(f"[WARNING] update_trailing_stop_loss called for {algorithm} algorithm - skipping")
        return
    
    # 🚨 STRENGTHENED MANUAL STOP LOSS PROTECTION
    manual_sl_set = position.get('manual_stop_loss_set', False)
    manual_sl_time = position.get('manual_stop_loss_time')
    current_sl = position.get('stop_loss_price', 0)
    
    # � IMMEDIATE PROTECTION: If manual flag is set, ALWAYS respect it (regardless of time)
    if manual_sl_set:
        print(f"🔧 MANUAL STOP LOSS ACTIVE: ₹{current_sl} - BLOCKING ALL ALGORITHM UPDATES")
        print(f"   manual_stop_loss_set: {manual_sl_set}")
        print(f"   manual_stop_loss_time: {manual_sl_time}")
        print(f"   🚫 SKIPPING update_trailing_stop_loss() to preserve manual setting")
        
        # Only clear manual flag if it's been more than 30 minutes AND user hasn't retriggered
        if manual_sl_time:
            try:
                current_time = get_ist_now()
                time_diff = (current_time - manual_sl_time).total_seconds()
                time_diff_minutes = time_diff / 60
                
                # Extended protection: Only clear after 30 minutes
                if time_diff >= 1800:  # 30 minutes
                    print(f"⏰ MANUAL PROTECTION EXPIRED after {time_diff_minutes:.1f} minutes - Clearing flag")
                    position['manual_stop_loss_set'] = False
                    # Don't return - let algorithm take over now
                else:
                    print(f"�️ MANUAL PROTECTION ACTIVE: {time_diff_minutes:.1f}/30 minutes remaining")
                    return  # Skip algorithm update
            except Exception as e:
                print(f"⚠️ Error in time calculation: {e} - Keeping manual protection active")
                return  # If time calc fails, err on side of protecting manual setting
        else:
            # No time set, but manual flag is True - respect it anyway
            print(f"🛡️ MANUAL FLAG SET (no timestamp) - Protecting manual stop loss")
            return
    
    trailing_step = app_state['auto_trading_config']['trailing_step']  # 10
    stop_loss_point = app_state['auto_trading_config']['stop_loss_points']  # 10
    
    # Get the original buy price 
    original_buy_price = position.get('original_buy_price', position['buy_price'])
    current_stop_loss = position.get('stop_loss_price', 0)
    # 🚨 CRITICAL: Get absolute minimum stop loss - NEVER go below this!
    minimum_stop_loss = position.get('minimum_stop_loss', original_buy_price - stop_loss_point)
    
    # 🚨 FIXED: Check if this is auto bought or manual buy
    if position.get('auto_bought', False):
        # AUTO BUY: Stop loss = auto buy price (where it was bought back)
        auto_buy_price = position['buy_price']
        current_price = position['current_price']
        highest_after_auto_buy = position['highest_price']

        # Calculate profit from auto buy price
        profit_from_auto_buy = highest_after_auto_buy - auto_buy_price

        if profit_from_auto_buy >= trailing_step:  # If profit >= 10
            # Calculate how many 10-rupee steps we've achieved
            profit_steps = int(profit_from_auto_buy // trailing_step)  # Number of complete 10-rupee steps

            # 🚨 USER REQUIREMENT FIXED: SL = auto_buy_price + (steps × 10) [NO MINUS 10]
            new_trailing_stop_loss = auto_buy_price + (profit_steps * trailing_step)

            # 🚨 CRITICAL FIX: Ensure stop loss is always below current price to prevent immediate sell trigger
            if new_trailing_stop_loss >= current_price:
                new_trailing_stop_loss = current_price - 0.01

            # 🚨 CRITICAL: NEVER let stop loss go below current_stop_loss
            position['stop_loss_price'] = max(new_trailing_stop_loss, current_stop_loss)

            print(f"🎯 AUTO BUY TRAILING: Auto Buy ₹{auto_buy_price} | Current ₹{current_price} | High ₹{highest_after_auto_buy} | Profit ₹{profit_from_auto_buy:.2f} | Steps: {profit_steps}")
            print(f"   CORRECT FORMULA: SL = Auto Buy Price + (Steps × 10) = ₹{auto_buy_price} + ({profit_steps} × {trailing_step}) = ₹{new_trailing_stop_loss:.2f}")
            print(f"   New Stop Loss: ₹{position['stop_loss_price']:.2f}")
        else:
            # No profit yet, stop loss = auto buy price - 10 (maintain original stop loss level)
            position['stop_loss_price'] = auto_buy_price - 10

            print(f"🔒 AUTO BUY INITIAL STOP LOSS: Auto Buy ₹{auto_buy_price} | Current ₹{current_price} | High ₹{highest_after_auto_buy}")
            print(f"   Stop Loss: ₹{position['stop_loss_price']:.2f} (Auto buy price - ₹10)")
    else:
        # MANUAL BUY: USER REQUIREMENT - SL = buy_price + (steps × 10) - 10
        highest_price = position['highest_price']
        current_price = position['current_price']
        profit = highest_price - original_buy_price

        if profit >= trailing_step:  # If profit >= 10
            # Calculate how many 10-rupee steps we've achieved from buy price
            profit_steps = int(profit // trailing_step)  # Number of complete 10-rupee steps

            # 🚨 USER REQUIREMENT FIXED: SL = buy_price + (steps × 10) [NO MINUS 10]
            # Example: Buy 535.85, Price 562.70 → Steps = 2, SL = 535.85 + 20 = 555.85
            new_trailing_stop_loss = original_buy_price + (profit_steps * trailing_step)

            # 🚨 CRITICAL FIX: Ensure stop loss is always below current price to prevent immediate sell trigger
            if new_trailing_stop_loss >= current_price:
                new_trailing_stop_loss = current_price - 0.01

            # 🚨 CRITICAL: NEVER let stop loss go below minimum_stop_loss
            old_stop_loss = position['stop_loss_price']
            position['stop_loss_price'] = max(new_trailing_stop_loss, current_stop_loss, minimum_stop_loss)

            # Debug print for manual trailing
            print(f"🎯 MANUAL TRAILING: Buy ₹{original_buy_price} | Current ₹{current_price} | High ₹{highest_price} | Profit ₹{profit:.2f} | Steps: {profit_steps}")
            print(f"   CORRECT FORMULA: SL = Buy Price + (Steps × 10) = ₹{original_buy_price} + ({profit_steps} × {trailing_step}) = ₹{new_trailing_stop_loss:.2f}")
            print(f"   Old Stop Loss: ₹{old_stop_loss:.2f} → New Stop Loss: ₹{position['stop_loss_price']:.2f}")
            print(f"   🚨 LIVE TRADING CHECK: If price drops below ₹{position['stop_loss_price']:.2f}, will trigger AUTO SELL")

        else:
            # 🚨 FIXED: MANUAL BUY INITIAL STOP LOSS: EXACTLY 10 points below buy price
            initial_stop_loss = original_buy_price - stop_loss_point  # Buy price - 10
            # 🚨 CRITICAL: NEVER let stop loss go above current price or below minimum
            position['stop_loss_price'] = max(initial_stop_loss, minimum_stop_loss)

            print(f"🔒 MANUAL BUY INITIAL STOP LOSS: Buy ₹{original_buy_price} | Current ₹{current_price} | High ₹{highest_price} | Profit ₹{profit:.2f} < ₹{trailing_step}")
            print(f"   Stop Loss: ₹{position['stop_loss_price']:.2f} (Buy price - ₹{stop_loss_point})")

def process_auto_trading():
    """Main auto trading processing function for both Live and Paper trading"""
    if not app_state['auto_trading_enabled']:
        print("⚠️ Auto trading disabled")
        return
    
    try:
        # Get positions based on trading mode
        if app_state['paper_trading_enabled']:
            # Paper trading mode - monitor paper positions
            positions_to_monitor = app_state['paper_positions']
            trading_mode = "PAPER"
        else:
            # Live trading mode - monitor auto positions
            positions_to_monitor = app_state['auto_positions']
            trading_mode = "LIVE"
        
        # Debug: Check if we have any positions to monitor
        if not positions_to_monitor:
            # Only print this occasionally to avoid spam
            if not hasattr(process_auto_trading, 'last_no_positions_print'):
                process_auto_trading.last_no_positions_print = 0
            
            current_time = time.time()
            if current_time - process_auto_trading.last_no_positions_print > 10:  # Print every 10 seconds
                print(f"ℹ️ No {trading_mode} positions to monitor")
                process_auto_trading.last_no_positions_print = current_time
            return
        
        # 🔥 DEBUG: Count positions waiting for auto buy
        waiting_for_autobuy_count = sum(1 for pos in positions_to_monitor if pos.get('waiting_for_autobuy', False))
        if waiting_for_autobuy_count > 0:
            print(f"⏳ {waiting_for_autobuy_count} positions waiting for auto buy in {trading_mode} mode")
        
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
        for position in positions_to_monitor[:]:  # Create copy to allow removal during iteration
            positions_checked += 1
            
            # 🔥 DEBUG: Print each position being processed
            position_type = position.get('option_type', position.get('type', 'UNKNOWN'))
            waiting_status = "WAITING FOR AUTO BUY" if position.get('waiting_for_autobuy', False) else "MONITORING"
            print(f"🔄 PROCESSING [{positions_checked}]: {position['strike']} {position_type} - {waiting_status}")
            
            # CRITICAL SAFETY: Skip positions that have been manually sold
            if position.get('manual_sold', False):
                print(f"🗑️ REMOVING MANUALLY SOLD POSITION: {position['strike']} {position.get('option_type', position.get('type'))}")
                positions_to_monitor.remove(position)
                continue
            
            # CRITICAL SAFETY: Skip positions currently being sold to prevent race conditions
            # BUT DO NOT skip positions waiting for auto buy - they need to be monitored!
            if position.get('sell_in_progress', False) and not position.get('waiting_for_autobuy', False):
                print(f"⏳ SKIPPING POSITION IN SELL PROCESS: {position['strike']} {position.get('option_type', position.get('type'))}")
                continue
            
            # Find matching option data
            matching_option = None
            for option in all_options:
                try:
                    option_strike = float(option.get('strike', 0))
                    position_strike = float(position['strike'])
                    
                    # 🔥 FIXED: Check both 'type' and 'option_type' fields for option data
                    option_type = str(option.get('type', option.get('option_type', '')))
                    position_type = str(position.get('option_type', position.get('type', '')))
                    
                    # 🔥 DEBUG: Print option matching details for ALL positions
                    print(f"🔍 MATCHING CHECK: Position {position_strike} {position_type} vs Option {option_strike} {option_type} | Option LTP: ₹{option.get('ltp', 0)}")
                    
                    if (option_strike == position_strike and 
                        option_type == position_type):
                        matching_option = option
                        print(f"✅ MATCH FOUND: {position_strike} {position_type} - LTP: ₹{option.get('ltp', 0)}")
                        break
                except (ValueError, TypeError) as e:
                    print(f"[ERROR] Error comparing option data: {e}")
                    continue

            if matching_option:
                try:
                    current_price = float(matching_option.get('ltp', 0))
                    
                    if position.get('waiting_for_autobuy', False):
                        # CRITICAL SAFETY: Double-check manual sell before auto buy
                        if position.get('manual_sold', False):
                            print(f"🛑 AUTO BUY CANCELLED: {position['strike']} {position['type']} was manually sold")
                            positions_to_monitor.remove(position)  # Remove from correct list
                            continue
                        
                        # Update current price for auto buy logic
                        position['current_price'] = current_price
                        
                        # 🚨 NEW: Skip old auto buy logic for advanced algorithm Phase 1 ONLY
                        # Phase 1 positions should only auto buy when price reaches manual buy price
                        # Phase 2 and 3 should use stop loss price trigger
                        current_algorithm = app_state.get('trading_algorithm', 'simple')
                        is_phase1_advanced = (current_algorithm == 'advanced' and 
                                            position.get('algorithm_phase', 1) == 1)
                        
                        if is_phase1_advanced:
                            # Phase 1 Advanced: Use manual buy price trigger
                            manual_buy_price = position.get('manual_buy_price', position.get('original_buy_price', 0))
                            if current_price >= manual_buy_price:
                                print(f"🟢 PHASE 1 AUTO BUY TRIGGERED: Price ₹{current_price} reached manual buy price ₹{manual_buy_price}")
                                success = execute_auto_buy(position)
                                if success:
                                    print(f"✅ AUTO BUY EXECUTED: {position['strike']} {position['type']} successfully bought back")
                                else:
                                    print(f"❌ AUTO BUY FAILED: {position['strike']} {position['type']} could not be bought back")
                            else:
                                print(f"⏳ PHASE 1 WAITING: Current ₹{current_price} < Manual Buy ₹{manual_buy_price}")
                        else:
                            # Original logic for simple algorithm and Phase 2/3 advanced
                            # 🚨 FIXED AUTO BUY LOGIC: Buy when price comes back to or above the stop loss sell price
                            # When stop loss hits at ₹150, auto buy should trigger when price comes back to ₹150
                            last_stop_loss = position.get('last_stop_loss_price', position.get('stop_loss_price', 0))
                            auto_buy_trigger_price = last_stop_loss  # Buy at EXACT stop loss price (same price as sell)
                            
                            # 🚨 SAFETY: Check minimum stop loss but don't remove position unnecessarily
                            minimum_stop_loss = position.get('minimum_stop_loss', 0)
                            if minimum_stop_loss > 0 and auto_buy_trigger_price < minimum_stop_loss:
                                print(f"⚠️ AUTO BUY ADJUSTED: Trigger adjusted from ₹{auto_buy_trigger_price} to minimum ₹{minimum_stop_loss}")
                                auto_buy_trigger_price = minimum_stop_loss  # Adjust trigger, don't remove position
                            
                            # 🔥 FIXED TRIGGER LOGIC: Buy when price comes back to the sell price
                            # This covers both scenarios: price going up to sell level, or coming down to sell level
                            auto_buy_buffer = app_state['auto_trading_config'].get('auto_buy_buffer', 0)
                            # Allow a buffer of ±1 rupee for auto buy trigger
                            if abs(current_price - auto_buy_trigger_price) <= max(1, auto_buy_buffer):
                                current_phase = position.get('algorithm_phase', 1)
                                print(f"🟢 PHASE {current_phase} AUTO BUY TRIGGERED: Price ₹{current_price} reached trigger ₹{auto_buy_trigger_price} (Stop loss sell price ± buffer)")
                                success = execute_auto_buy(position)
                                if success:
                                    print(f"✅ AUTO BUY EXECUTED: {position['strike']} {position['type']} successfully bought back")
                                else:
                                    print(f"❌ AUTO BUY FAILED: {position['strike']} {position['type']} could not be bought back")
                            else:
                                print(f"⏳ WAITING FOR AUTO BUY: Current ₹{current_price} not within buffer of Trigger ₹{auto_buy_trigger_price} (Need price to reach sell level ± buffer)")
                    else:
                        # Update position and check for auto sell
                        # In paper trading mode, we need special handling
                        if app_state['paper_trading_enabled']:
                            # Paper trading - handle auto sell differently
                            position['current_price'] = current_price
                            
                            # 🚨 CRITICAL FIX: Update highest price and trailing stop loss in paper trading
                            # Initialize highest_price if it doesn't exist
                            if 'highest_price' not in position:
                                position['highest_price'] = position.get('buy_price', current_price)
                            
                            # Update highest price for trailing stop loss
                            if current_price > float(position['highest_price']):
                                position['highest_price'] = current_price
                                print(f"📈 NEW HIGH: {position['strike']} {position.get('option_type', position.get('type'))} - New High: ₹{current_price}")
                            
                            # Update trailing stop loss with new price data (based on current algorithm)
                            current_algorithm = app_state.get('trading_algorithm', 'simple')
                            if current_algorithm == 'simple':
                                update_trailing_stop_loss(position, algorithm='simple')
                            elif current_algorithm == 'advanced':
                                # 🚨 CRITICAL FIX: Call advanced algorithm for paper trading too!
                                update_advanced_algorithm(position, current_price)
                            
                            # Debug print for stop loss monitoring
                            print(f"🔍 PAPER MONITORING: {position['strike']} {position.get('option_type', position.get('type'))} | Current: ₹{current_price} | Highest: ₹{position['highest_price']} | Stop Loss: ₹{position.get('stop_loss_price', 0)}")
                            
                            # Check for stop loss in paper trading - ONLY trigger if price DROPS below stop loss
                            stop_loss_price = position.get('stop_loss_price', 0)
                            original_buy_price = position.get('original_buy_price', position.get('buy_price', 0))
                            
                            # 🚨 ENHANCED STOP LOSS TRIGGER: Support both profit targets and stop losses
                            manual_sl_active = position.get('manual_stop_loss_set', False)
                            
                            # Debug stop loss trigger conditions
                            print(f"🔍 SL TRIGGER CHECK: Current=₹{current_price}, SL=₹{stop_loss_price}, Manual={manual_sl_active}")
                            print(f"   Conditions: SL>0={stop_loss_price > 0}, Not waiting={not position.get('waiting_for_autobuy', False)}, Not triggered={not position.get('sell_triggered', False)}")
                            
                            # FIXED: Enhanced trigger logic based on stop loss position relative to buy price
                            trigger_condition = False
                            if manual_sl_active:
                                # Get buy price to determine if SL is above or below entry
                                buy_price = position.get('original_buy_price', position.get('buy_price', 0))
                                
                                if stop_loss_price > buy_price:
                                    # Manual stop loss ABOVE buy price = PROFIT TARGET
                                    # Only trigger when price reaches or exceeds the target
                                    trigger_condition = current_price >= stop_loss_price
                                    print(f"   Manual PROFIT TARGET: {current_price} >= {stop_loss_price} = {trigger_condition} (SL above buy ₹{buy_price})")
                                else:
                                    # Manual stop loss BELOW buy price = STOP LOSS
                                    # Trigger when price touches or drops below
                                    trigger_condition = current_price <= stop_loss_price
                                    print(f"   Manual STOP LOSS: {current_price} <= {stop_loss_price} = {trigger_condition} (SL below buy ₹{buy_price})")
                            else:
                                # Algorithm stop loss: trigger when price goes below (strict)
                                trigger_condition = current_price < stop_loss_price
                                print(f"   Algorithm SL Trigger: {current_price} < {stop_loss_price} = {trigger_condition}")
                            
                            if (trigger_condition and
                                stop_loss_price > 0 and 
                                not position.get('waiting_for_autobuy', False) and
                                not position.get('sell_triggered', False)):
                                
                                # Determine appropriate reason based on profit/loss and manual setting
                                buy_price = position.get('original_buy_price', position.get('buy_price', 0))
                                is_profit = current_price > buy_price
                                
                                if manual_sl_active:
                                    if stop_loss_price > buy_price:
                                        reason = 'Manual Profit Target'
                                    else:
                                        reason = 'Manual Stop Loss'
                                elif is_profit:
                                    reason = 'Trailing Stop Loss (Profit Booking)'
                                else:
                                    reason = 'Stop Loss'
                                
                                print(f"🚨 PAPER TRADING STOP LOSS: {position['strike']} {position.get('option_type', position.get('type'))} @ ₹{current_price}")
                                auto_sold = execute_auto_sell(position, reason=reason)
                                if auto_sold:
                                    print(f"🔴 PAPER AUTO SELL TRIGGERED: {position['strike']} {position.get('option_type', position.get('type'))} @ ₹{current_price}")
                                    continue
                        else:
                            # Live trading - use existing logic

                            print(f"🏦 LIVE TRADING: Calling update_auto_position_price for {position['strike']} {position['type']} @ ₹{current_price}")
                            auto_sold = update_auto_position_price(position, current_price)
                            if auto_sold:
                                print(f"🔴 LIVE AUTO SELL TRIGGERED: {position['strike']} {position['type']} @ ₹{current_price}")
                                continue
                            else:
                                print(f"✅ LIVE POSITION MONITORED: {position['strike']} {position['type']} @ ₹{current_price} | SL: ₹{position.get('stop_loss_price', 0)}")
                except (ValueError, TypeError) as e:
                    print(f"[ERROR] Invalid price data in option: {matching_option}, error: {e}")
                    current_price = float(position.get('current_price', 0))
            else:
                # If no matching option data, use last known price but still check stop loss
                current_price = float(position.get('current_price', 0))
                position_type = position.get('option_type', position.get('type', 'UNKNOWN'))
                
                # 🔥 DEBUG: Print when no matching option is found
                if position.get('waiting_for_autobuy', False):
                    print(f"❌ NO MATCH FOUND: {position['strike']} {position_type} waiting for auto buy but no option data found!")
                    print(f"📊 Available options: {len(all_options)} total")
                    if len(all_options) > 0:
                        print(f"🔍 Sample option data: Strike={all_options[0].get('strike')}, Type={all_options[0].get('option_type')}")
                else:
                    print(f"⚠️ NO OPTION DATA: {position['strike']} {position_type} (Last known price: ₹{current_price})")
                
                # Continue with last known price for stop loss checks
                print(f"⚠️ No matching option data for {position['strike']} {position['type']}, using last price: ₹{current_price}")
                
                # Still check stop loss with last known price
                if not position.get('waiting_for_autobuy', False):
                    # In paper trading mode, handle stop loss differently
                    if app_state['paper_trading_enabled']:
                        # Paper trading - check for stop loss (Last Price)
                        stop_loss_price = position.get('stop_loss_price', 0)
                        original_buy_price = position.get('original_buy_price', position.get('buy_price', 0))
                        
                        # 🚨 ENHANCED STOP LOSS TRIGGER (Last Price): Support both profit targets and stop losses
                        manual_sl_active = position.get('manual_stop_loss_set', False)
                        
                        # Debug stop loss trigger conditions (last price scenario)
                        print(f"🔍 SL TRIGGER CHECK (Last Price): Current=₹{current_price}, SL=₹{stop_loss_price}, Manual={manual_sl_active}")
                        
                        # FIXED: Enhanced trigger logic based on stop loss position relative to buy price
                        trigger_condition = False
                        if manual_sl_active:
                            # Get buy price to determine if SL is above or below entry
                            buy_price = position.get('original_buy_price', position.get('buy_price', 0))
                            
                            if stop_loss_price > buy_price:
                                # Manual stop loss ABOVE buy price = PROFIT TARGET
                                # Only trigger when price reaches or exceeds the target
                                trigger_condition = current_price >= stop_loss_price
                                print(f"   Manual PROFIT TARGET (Last): {current_price} >= {stop_loss_price} = {trigger_condition} (SL above buy ₹{buy_price})")
                            else:
                                # Manual stop loss BELOW buy price = STOP LOSS
                                # Trigger when price touches or drops below
                                trigger_condition = current_price <= stop_loss_price
                                print(f"   Manual STOP LOSS (Last): {current_price} <= {stop_loss_price} = {trigger_condition} (SL below buy ₹{buy_price})")
                        else:
                            # Algorithm stop loss: trigger when price goes below (strict)
                            trigger_condition = current_price < stop_loss_price
                            print(f"   Algorithm SL Trigger (Last): {current_price} < {stop_loss_price} = {trigger_condition}")
                        
                        if (trigger_condition and
                            stop_loss_price > 0 and 
                            not position.get('sell_triggered', False)):
                            
                            # Determine appropriate reason based on profit/loss and manual setting
                            buy_price = position.get('original_buy_price', position.get('buy_price', 0))
                            is_profit = current_price > buy_price
                            
                            if manual_sl_active:
                                if stop_loss_price > buy_price:
                                    reason = 'Manual Profit Target'
                                else:
                                    reason = 'Manual Stop Loss'
                            elif is_profit:
                                reason = 'Trailing Stop Loss (Profit Booking)'
                            else:
                                reason = 'Stop Loss'
                            
                            print(f"🚨 PAPER TRADING STOP LOSS (Last Price): {position['strike']} {position['type']} @ ₹{current_price}")
                            auto_sold = execute_auto_sell(position, reason=reason)
                            if auto_sold:
                                print(f"🔴 PAPER AUTO SELL TRIGGERED (Last Price): {position['strike']} {position['type']} @ ₹{current_price}")
                                continue
                    else:
                        # Live trading - use existing logic
                        auto_sold = update_auto_position_price(position, current_price)
                        if auto_sold:
                            print(f"🔴 AUTO SELL TRIGGERED (Last Price): {position['strike']} {position['type']} @ ₹{current_price}")
                            continue
        
        # Debug: Print processing summary occasionally
        if positions_to_monitor:
            if not hasattr(process_auto_trading, 'last_summary_print'):
                process_auto_trading.last_summary_print = 0
            
            current_time = time.time()
            if current_time - process_auto_trading.last_summary_print > 5:  # Print every 5 seconds
                print(f"🤖 {trading_mode} Auto Trading: {positions_checked}/{len(positions_to_monitor)} positions checked | Options data: {len(all_options)} options")
                process_auto_trading.last_summary_print = current_time
        
    except Exception as e:
        print(f"❌ Auto Trading Error: {e}")
        traceback.print_exc()

def check_market_close_and_exit_positions():
    """
    Check if market close time is approaching (3:20 PM) and auto-exit all live positions
    Market closes at 3:30 PM, so we exit at 3:20 PM for safety
    """
    try:
        current_time = get_ist_now()
        current_hour = current_time.hour
        current_minute = current_time.minute
        
        # Market close exit time: 3:20 PM (15:20)
        EXIT_HOUR = 15
        EXIT_MINUTE = 20
        
        # Check if it's exactly 3:20 PM or between 3:20 and 3:30
        if current_hour == EXIT_HOUR and current_minute >= EXIT_MINUTE:
            # Check if we're in live trading mode
            if not app_state['paper_trading_enabled']:
                positions_to_exit = app_state.get('auto_positions', [])
                
                # Filter only positions with quantity > 0 (active positions)
                active_positions = [pos for pos in positions_to_exit if pos.get('qty', pos.get('quantity', 0)) > 0]
                
                if active_positions:
                    print(f"⏰ MARKET CLOSE EXIT: It's {current_hour}:{current_minute:02d} - Auto-exiting {len(active_positions)} live positions")
                    
                    for position in active_positions:
                        # Check if already sold or in progress
                        if position.get('sold') or position.get('sell_in_progress') or position.get('sell_triggered'):
                            continue
                        
                        strike = position.get('strike')
                        option_type = position.get('type', position.get('option_type'))
                        current_price = position.get('current_price', position.get('buy_price', 0))
                        
                        print(f"🔴 MARKET CLOSE EXIT: Selling {strike} {option_type} @ ₹{current_price}")
                        
                        # Execute auto sell with market close reason
                        try:
                            execute_auto_sell(position, reason='Market Close Exit')
                        except Exception as e:
                            print(f"❌ MARKET CLOSE EXIT FAILED: {strike} {option_type} - {e}")
                    
                    # After exiting all positions, disable auto trading to prevent new trades
                    app_state['auto_trading_enabled'] = False
                    print(f"🛑 MARKET CLOSE: Auto trading disabled until next trading day")
                    
                    return True
        
        return False
        
    except Exception as e:
        print(f"❌ Market Close Check Error: {e}")
        return False

def sync_and_remove_manually_closed_positions():
    """
    🔄 POSITION SYNC: Check if positions were manually closed in Zerodha app
    If a position is closed in Zerodha app, remove it from webapp and stop auto trading
    This prevents infinite sell rejection loops
    """
    if app_state.get('paper_trading_enabled', True):
        # Skip sync for paper trading mode
        return
    
    if not app_state.get('zerodha_connected') or not app_state.get('kite'):
        return
    
    try:
        # Fetch current Zerodha positions
        positions_data = app_state['kite'].positions()
        zerodha_positions = positions_data.get('net', [])
        
        # Build a set of all active tradingsymbols in Zerodha
        active_zerodha_symbols = set()
        for z_pos in zerodha_positions:
            qty = z_pos.get('quantity', 0)
            if qty != 0:  # Only active positions
                symbol = z_pos.get('tradingsymbol', '')
                active_zerodha_symbols.add(symbol)
        
        print(f"[POSITION SYNC] Active Zerodha positions: {len(active_zerodha_symbols)}")
        
        # Check all webapp positions
        positions_to_check = []
        
        # Check manual positions
        for pos in app_state.get('positions', []):
            positions_to_check.append(('manual', pos))
        
        # Check auto positions
        for pos in app_state.get('auto_positions', []):
            positions_to_check.append(('auto', pos))
        
        removed_count = 0
        for pos_type, position in positions_to_check:
            try:
                # Build tradingsymbol for this position
                symbol = position.get('symbol', 'NIFTY')
                strike = position.get('strike', 0)
                option_type = position.get('option_type', position.get('type', ''))
                expiry = position.get('expiry', '')
                
                if not strike or not option_type or not expiry:
                    continue
                
                # Convert expiry to YYMMDD format for TrueData
                if '-' in expiry:
                    expiry_parts = expiry.split('-')
                    if len(expiry_parts) == 3:
                        yymmdd = expiry_parts[0][2:] + expiry_parts[1] + expiry_parts[2]
                    else:
                        continue
                else:
                    yymmdd = expiry
                
                # Build TrueData symbol and convert to Zerodha tradingsymbol
                td_symbol = f"{symbol}{yymmdd}{int(strike)}{option_type}"
                tradingsymbol, instrument_token, error = get_zerodha_symbol(td_symbol)
                
                if not tradingsymbol:
                    continue
                
                # Check if position exists in Zerodha
                if tradingsymbol not in active_zerodha_symbols:
                    print(f"[POSITION SYNC] ⚠️ Position NOT found in Zerodha: {tradingsymbol}")
                    print(f"[POSITION SYNC] 🗑️ User manually closed this in Zerodha app - Removing from webapp")
                    
                    # Remove from appropriate list
                    if pos_type == 'manual':
                        if position in app_state['positions']:
                            app_state['positions'].remove(position)
                            print(f"[POSITION SYNC] ✅ Removed from manual positions: {strike} {option_type}")
                            removed_count += 1
                    elif pos_type == 'auto':
                        if position in app_state['auto_positions']:
                            app_state['auto_positions'].remove(position)
                            print(f"[POSITION SYNC] ✅ Removed from auto positions: {strike} {option_type}")
                            removed_count += 1
                            
                            # Also add to trade history
                            app_state['trade_history'].append({
                                'timestamp': get_ist_timestamp(),
                                'action': 'Position Removed (Manually Closed in Zerodha App)',
                                'strike': strike,
                                'type': option_type,
                                'quantity': position.get('quantity', 0),
                                'lots': position.get('lots', 1),
                                'sell_price': 0,
                                'buy_price': position.get('buy_price', 0),
                                'pnl': 0,
                                'reason': 'Position manually closed in Zerodha app - preventing auto trading loop'
                            })
                    
            except Exception as e:
                print(f"[POSITION SYNC] Error checking position: {e}")
                continue
        
        if removed_count > 0:
            print(f"[POSITION SYNC] 🧹 Cleaned up {removed_count} manually closed positions")
            # Emit update to frontend
            try:
                socketio.emit('position_update', {
                    'positions': app_state.get('positions', []),
                    'auto_positions': app_state.get('auto_positions', [])
                })
            except:
                pass
                
    except Exception as e:
        print(f"[POSITION SYNC] ❌ Error syncing positions: {e}")

def auto_trading_background_task():
    """Background task for auto trading and market close monitoring"""
    print("🤖 Auto trading background task started")
    last_market_close_check = 0
    last_position_sync = 0
    market_closed_today = False
    
    while True:
        try:
            current_time = time.time()
            
            # � Position sync every 30 seconds (check if positions were closed in Zerodha app)
            if current_time - last_position_sync >= 10:  # Check every 10 seconds - fast but safe
                last_position_sync = current_time
                sync_and_remove_manually_closed_positions()
            
            # 🕐 Check for market close every 60 seconds (only after 3:00 PM)
            if current_time - last_market_close_check >= 60:  # Check every minute
                last_market_close_check = current_time
                
                ist_time = get_ist_now()
                # Only check after 3:00 PM (15:00) and before 3:31 PM
                if ist_time.hour == 15 and ist_time.minute >= 0 and ist_time.minute <= 30:
                    if not market_closed_today:
                        print(f"⏰ Market close check: Current time {ist_time.hour}:{ist_time.minute:02d}")
                        if check_market_close_and_exit_positions():
                            market_closed_today = True
                            print(f"✅ All positions exited for market close")
                # Reset flag at midnight or market open (9:00 AM)
                elif ist_time.hour == 0 or ist_time.hour == 9:
                    if market_closed_today:
                        market_closed_today = False
                        print(f"🔄 Market close flag reset for new trading day")
            
            # Continue normal auto trading
            if app_state['auto_trading_running']:
                process_auto_trading()
            else:
                # Sleep longer when auto trading is disabled
                time.sleep(2)
        except Exception as e:
            print(f"❌ Auto trading background error: {e}")
            import traceback
            traceback.print_exc()
        
        time.sleep(0.1)  # Check every 0.1 seconds for faster response

def zerodha_session_monitor():
    """Background task to monitor Zerodha session and auto-reconnect"""
    print("🔐 Zerodha session monitor started")
    last_check = 0
    consecutive_failures = 0
    while True:
        try:
            current_time = time.time()
            # Check every SESSION_MONITOR_INTERVAL seconds
            if current_time - last_check >= SESSION_MONITOR_INTERVAL:
                last_check = current_time
                if app_state.get('zerodha_connected') and app_state.get('kite'):
                    try:
                        # Test connection by calling a simple API
                        profile = app_state['kite'].profile()
                        # Only print occasionally to avoid spam
                        if consecutive_failures == 0:
                            print(f"✅ Zerodha session healthy - {profile.get('user_name', 'User')}")
                        consecutive_failures = 0  # Reset failure counter after print
                    except Exception as e:
                        consecutive_failures += 1
                        error_msg = str(e).lower()
                        print(f"⚠️ Zerodha session check failed (attempt {consecutive_failures}): {e}")
                        # Check if it's a session/token related error
                        if any(keyword in error_msg for keyword in ['session', 'token', 'expired', 'invalid', 'unauthorized', 'forbidden']):
                            print(f"🔄 Session expired detected - marking as disconnected")
                            app_state['zerodha_connected'] = False
                            # Try to clear and reinitialize if we have stored credentials
                            if KITE_CONFIG.get('access_token'):
                                print(f"🔄 Attempting to reinitialize connection...")
                                try:
                                    # Reinitialize with existing token
                                    app_state['kite'] = KiteConnect(api_key=KITE_CONFIG['api_key'])
                                    app_state['kite'].set_access_token(KITE_CONFIG['access_token'])
                                    # Test the new connection
                                    test_profile = app_state['kite'].profile()
                                    app_state['zerodha_connected'] = True
                                    print(f"✅ Zerodha session restored successfully!")
                                    consecutive_failures = 0  # Reset after successful restore
                                except Exception as reinit_error:
                                    print(f"❌ Session restore failed: {reinit_error}")
                                    # Clear invalid tokens
                                    if 'session' in str(reinit_error).lower() or 'invalid' in str(reinit_error).lower():
                                        KITE_CONFIG['access_token'] = ''
                                        app_state['kite'] = None
                        # If too many consecutive failures, mark as disconnected
                        if consecutive_failures >= 3:
                            print(f"❌ Too many session failures - marking Zerodha as disconnected")
                            app_state['zerodha_connected'] = False
                else:
                    # Not connected, just log occasionally
                    if consecutive_failures == 0:
                        print(f"ℹ️ Zerodha not connected - session monitor waiting...")
            time.sleep(SESSION_MONITOR_RETRY_INTERVAL)  # Use constant for retry interval
        except Exception as e:
            print(f"❌ Session monitor error: {e}")
            time.sleep(SESSION_MONITOR_RETRY_INTERVAL)  # Wait on unexpected errors

def execute_with_session_retry(operation_func, operation_name="Zerodha operation", max_retries=2):
    """
    Execute Zerodha operation with automatic session retry on failure
    
    Args:
        operation_func: Function to execute that uses app_state['kite']
        operation_name: Name of operation for logging
        max_retries: Maximum retry attempts
    
    Returns:
        (success: bool, result: any, error_message: str)
    """
    for attempt in range(max_retries + 1):
        try:
            if not app_state.get('zerodha_connected') or not app_state.get('kite'):
                return False, None, "Zerodha not connected"
            
            # Execute the operation
            result = operation_func()
            return True, result, ""
            
        except Exception as e:
            error_msg = str(e).lower()
            print(f"⚠️ {operation_name} failed (attempt {attempt + 1}): {e}")
            
            # Check if it's a session/auth error
            if any(keyword in error_msg for keyword in ['session', 'token', 'expired', 'invalid', 'unauthorized', 'forbidden']):
                print(f"🔄 Session error detected in {operation_name} - attempting reconnection...")
                
                # Try to restore session
                if KITE_CONFIG.get('access_token') and attempt < max_retries:
                    try:
                        # Reinitialize connection
                        app_state['kite'] = KiteConnect(api_key=KITE_CONFIG['api_key'])
                        app_state['kite'].set_access_token(KITE_CONFIG['access_token'])
                        
                        # Test the connection
                        app_state['kite'].profile()
                        app_state['zerodha_connected'] = True
                        print(f"✅ Session restored for {operation_name}")
                        
                        # Retry the operation
                        continue
                        
                    except Exception as restore_error:
                        print(f"❌ Session restore failed: {restore_error}")
                        app_state['zerodha_connected'] = False
                        if 'session' in str(restore_error).lower() or 'invalid' in str(restore_error).lower():
                            KITE_CONFIG['access_token'] = ''
                            app_state['kite'] = None
                        break
                else:
                    # No token to retry with or max retries reached
                    app_state['zerodha_connected'] = False
                    break
            else:
                # Non-session error, don't retry
                break
    
    return False, None, str(e) if 'e' in locals() else "Operation failed"

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
    """Logout and disconnect Zerodha for safety"""
    # Clear user session
    clear_active_session()
    session.clear()
    
    # 🔥 DISCONNECT ZERODHA for safety - prevent accidental trades
    if app_state.get('zerodha_connected'):
        print(f"🔌 LOGOUT: Disconnecting Zerodha connection for safety")
        
        # 🚨 CRITICAL: Invalidate Zerodha session at API level
        zerodha_session_invalidated = False
        if app_state.get('kite'):
            try:
                print(f"🔐 LOGOUT: Invalidating Zerodha session at API level...")
                # Call Zerodha logout API to invalidate session
                app_state['kite'].invalidate_access_token(KITE_CONFIG.get('access_token', ''))
                zerodha_session_invalidated = True
                print(f"✅ LOGOUT: Zerodha session invalidated at API level")
            except Exception as e:
                print(f"⚠️ LOGOUT: Could not invalidate Zerodha session: {e}")
                # Continue with local cleanup even if API call fails
                zerodha_session_invalidated = False
        
        # Clear Zerodha connection locally
        app_state['zerodha_connected'] = False
        app_state['kite'] = None
        
        # Clear access token from config
        KITE_CONFIG['access_token'] = ''
        
        # Stop auto trading to prevent any accidental orders
        app_state['auto_trading_enabled'] = False
        app_state['auto_trading_running'] = False
        
        # Clear auto positions for safety
        app_state['auto_positions'] = []
        
        # Clear paper trading positions
        app_state['paper_positions'] = []
        
        print(f"✅ LOGOUT: Zerodha disconnected successfully")
        print(f"✅ LOGOUT: Auto trading stopped")
        print(f"✅ LOGOUT: Auto positions cleared")
        print(f"✅ LOGOUT: Paper positions cleared")
        
        return jsonify({
            'success': True,
            'message': 'Logged out successfully. Zerodha session invalidated.',
            'zerodha_disconnected': True,
            'zerodha_session_invalidated': zerodha_session_invalidated
        })
    else:
        return jsonify({
            'success': True,
            'message': 'Logged out successfully.',
            'zerodha_disconnected': False
        })


@app.route('/api/market-status')
def api_market_status():
    return jsonify(get_market_status())

# Paper Trading API Routes
@app.route('/api/paper-trading/toggle', methods=['POST'])
def api_toggle_paper_trading():
    """Toggle paper trading mode with race condition protection"""
    global PAPER_TRADING_ENABLED
    
    # Add a simple lock to prevent concurrent toggles
    if not hasattr(api_toggle_paper_trading, 'processing'):
        api_toggle_paper_trading.processing = False
    
    if api_toggle_paper_trading.processing:
        return jsonify({
            'success': False, 
            'error': 'Toggle operation already in progress'
        }), 429
    
    try:
        api_toggle_paper_trading.processing = True
        
        data = request.get_json()
        enabled = data.get('enabled', False)
        
        print(f"🐛 TOGGLE DEBUG: Received enabled={enabled}")
        print(f"🐛 TOGGLE DEBUG: Before - PAPER_TRADING_ENABLED={PAPER_TRADING_ENABLED}, app_state={app_state['paper_trading_enabled']}")
        
        # Small delay to simulate processing and prevent rapid toggles
        import time
        time.sleep(0.1)
        
        PAPER_TRADING_ENABLED = enabled
        app_state['paper_trading_enabled'] = enabled
        
        print(f"🐛 TOGGLE DEBUG: After - PAPER_TRADING_ENABLED={PAPER_TRADING_ENABLED}, app_state={app_state['paper_trading_enabled']}")
        
        mode_text = "Paper Trading" if enabled else "Live Trading"
        print(f"🔄 Switched to {mode_text} mode")
        
        return jsonify({
            'success': True,
            'paper_trading_enabled': enabled,
            'message': f'Switched to {mode_text} mode'
        })
    except Exception as e:
        print(f"❌ Error toggling paper trading: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        # Always reset the processing flag
        api_toggle_paper_trading.processing = False

@app.route('/api/toggle_cooldown', methods=['POST'])
def api_toggle_cooldown():
    """Toggle cooldown protection on/off"""
    try:
        # Toggle the cooldown state
        app_state['cooldown_enabled'] = not app_state.get('cooldown_enabled', True)
        
        status = "ENABLED" if app_state['cooldown_enabled'] else "DISABLED"
        message = f"Cooldown protection {status}"
        
        print(f"🔄 COOLDOWN TOGGLE: {message}")
        
        # Emit real-time update to frontend
        socketio.emit('cooldown_status_update', {
            'enabled': app_state['cooldown_enabled'],
            'message': message
        })
        
        return jsonify({
            'success': True,
            'cooldown_enabled': app_state['cooldown_enabled'],
            'message': message
        })
        
    except Exception as e:
        print(f"❌ Error toggling cooldown: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/cooldown/status')
def api_cooldown_status():
    """Get current cooldown status"""
    return jsonify({
        'cooldown_enabled': app_state.get('cooldown_enabled', True)
    })

@app.route('/api/trading-algorithm', methods=['GET', 'POST'])
def api_trading_algorithm():
    """Get or set trading algorithm"""
    if request.method == 'GET':
        return jsonify({
            'algorithm': app_state.get('trading_algorithm', 'simple')
        })
    
    try:
        data = request.get_json()
        algorithm = data.get('algorithm', 'simple')
        force_change = data.get('force', False)  # Emergency force change option
        
        if algorithm not in ['simple', 'advanced']:
            return jsonify({
                'success': False,
                'error': 'Invalid algorithm. Must be "simple" or "advanced"'
            }), 400
        
        # 🚨 CHECK FOR ACTIVE POSITIONS BEFORE ALGORITHM CHANGE
        current_algorithm = app_state.get('trading_algorithm', 'simple')
        
        # If trying to change algorithm, check for active positions (unless forced)
        if algorithm != current_algorithm and not force_change:
            # Check for active auto positions
            active_auto_positions = [
                pos for pos in app_state.get('auto_positions', [])
                if not pos.get('sold', False) and not pos.get('manual_sold', False)
            ]
            
            # Check for active paper positions (if in paper trading mode)
            active_paper_positions = []
            if app_state.get('paper_trading_enabled', False):
                active_paper_positions = [
                    pos for pos in app_state.get('paper_positions', [])
                    if pos.get('quantity', 0) > 0
                ]
            
            # Check for active live positions (if in live trading mode)
            active_live_positions = []
            if not app_state.get('paper_trading_enabled', False):
                active_live_positions = [
                    pos for pos in app_state.get('zerodha_positions', [])
                    if pos.get('quantity', 0) != 0
                ]
            
            total_active_positions = len(active_auto_positions) + len(active_paper_positions) + len(active_live_positions)
            
            if total_active_positions > 0:
                # Create detailed position summary
                position_details = []
                
                # Add auto positions
                for pos in active_auto_positions:
                    position_details.append({
                        'type': 'Auto Trading',
                        'strike': pos.get('strike'),
                        'option_type': pos.get('type', pos.get('option_type')),
                        'quantity': pos.get('qty', pos.get('quantity', 0)),
                        'status': pos.get('mode', 'Active'),
                        'current_price': pos.get('current_price', 0)
                    })
                
                # Add paper positions
                for pos in active_paper_positions:
                    position_details.append({
                        'type': 'Paper Trading',
                        'strike': pos.get('strike'),
                        'option_type': pos.get('option_type'),
                        'quantity': pos.get('quantity', 0),
                        'status': 'Active',
                        'current_price': pos.get('current_price', 0)
                    })
                
                # Add live positions
                for pos in active_live_positions:
                    position_details.append({
                        'type': 'Live Trading',
                        'strike': pos.get('instrument_token'),
                        'option_type': pos.get('product'),
                        'quantity': pos.get('quantity', 0),
                        'status': 'Active',
                        'current_price': pos.get('last_price', 0)
                    })
                
                print(f"🚨 ALGORITHM CHANGE BLOCKED: {total_active_positions} active positions found")
                print(f"   Current Algorithm: {current_algorithm}")
                print(f"   Requested Algorithm: {algorithm}")
                print(f"   Active Auto Positions: {len(active_auto_positions)}")
                print(f"   Active Paper Positions: {len(active_paper_positions)}")
                print(f"   Active Live Positions: {len(active_live_positions)}")
                print(f"   💡 Use 'force: true' parameter to override (not recommended)")
                
                return jsonify({
                    'success': False,
                    'error': 'Cannot change algorithm with active positions',
                    'message': f'Please sell all {total_active_positions} active positions before changing from {current_algorithm} to {algorithm} algorithm',
                    'active_positions_count': total_active_positions,
                    'current_algorithm': current_algorithm,
                    'requested_algorithm': algorithm,
                    'position_details': position_details,
                    'warning': 'Algorithm change blocked due to active positions',
                    'force_change_available': True,
                    'instructions': 'Add "force": true to request body to override this check (not recommended)'
                }), 400
        
        # If no active positions or same algorithm or forced change, proceed with change
        app_state['trading_algorithm'] = algorithm
        
        if force_change and algorithm != current_algorithm:
            positions_count = get_active_positions_count()['total']
            print(f"🚨 FORCED Trading algorithm changed to: {algorithm} (with {positions_count} active positions)")
            message = f'Trading algorithm FORCE changed to {algorithm} (Warning: {positions_count} active positions)'
            warning = f'FORCED CHANGE: Algorithm changed with {positions_count} active positions. Monitor positions carefully!'
        else:
            print(f"🧠 Trading algorithm changed to: {algorithm}")
            message = f'Trading algorithm set to {algorithm}'
            warning = None
        
        return jsonify({
            'success': True,
            'algorithm': algorithm,
            'message': message,
            'previous_algorithm': current_algorithm,
            'forced': force_change,
            'warning': warning
        })
        
    except Exception as e:
        print(f"❌ Error setting trading algorithm: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/algorithm-debug-status')
def api_algorithm_debug_status():
    """Get detailed algorithm status for debugging"""
    try:
        current_algorithm = app_state.get('trading_algorithm', 'simple')
        positions_info = get_active_positions_count()
        
        # Get sample position for debugging
        sample_position = None
        if app_state.get('auto_positions'):
            sample_position = {
                'strike': app_state['auto_positions'][0].get('strike'),
                'type': app_state['auto_positions'][0].get('type'),
                'current_price': app_state['auto_positions'][0].get('current_price'),
                'stop_loss_price': app_state['auto_positions'][0].get('stop_loss_price'),
                'advanced_stop_loss': app_state['auto_positions'][0].get('advanced_stop_loss'),
                'progressive_minimum': app_state['auto_positions'][0].get('progressive_minimum'),
                'highest_stop_loss': app_state['auto_positions'][0].get('highest_stop_loss'),
                'auto_bought': app_state['auto_positions'][0].get('auto_bought', False)
            }
        
        return jsonify({
            'success': True,
            'current_algorithm': current_algorithm,
            'active_positions': positions_info,
            'sample_position': sample_position,
            'algorithm_behaviors': {
                'simple': {
                    'auto_buy_trigger': 'original_buy_price',
                    'stop_loss_formula': 'buy_price + (steps × 10)',
                    'trailing_function': 'update_trailing_stop_loss()'
                },
                'advanced': {
                    'auto_buy_trigger': 'same_sell_price',
                    'stop_loss_formula': 'buy_price + (steps × 10) with progressive_minimum protection',
                    'trailing_function': 'built-in advanced logic'
                }
            },
            'debug_info': {
                'last_algorithm_change': 'Check console logs for [DEBUG] ALGORITHM CALLED messages',
                'monitoring_prints': 'Look for SIMPLE MONITORING vs ADVANCED MONITORING in console'
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/active-positions-status')
def api_active_positions_status():
    """Get count and details of active positions across all trading modes"""
    try:
        positions_info = get_active_positions_count()
        current_algorithm = app_state.get('trading_algorithm', 'simple')
        
        return jsonify({
            'success': True,
            'current_algorithm': current_algorithm,
            'active_positions': positions_info,
            'can_change_algorithm': positions_info['total'] == 0,
            'warning_message': f"Cannot change algorithm with {positions_info['total']} active positions" if positions_info['total'] > 0 else None
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/paper-trading/status')
def api_paper_trading_status():
    """Get current paper trading status"""
    return jsonify({
        'paper_trading_enabled': app_state['paper_trading_enabled'],
        'wallet_balance': app_state['paper_wallet_balance'],
        'positions_count': len(app_state['paper_positions']),
        'orders_count': len(app_state['paper_orders'])
    })

@app.route('/api/paper-trading/reset-wallet', methods=['POST'])
def api_reset_paper_wallet():
    """Reset paper trading wallet to initial balance"""
    app_state['paper_wallet_balance'] = INITIAL_PAPER_WALLET_BALANCE
    app_state['paper_positions'] = []
    app_state['paper_orders'] = []
    app_state['paper_trade_history'] = []
    
    print(f"🔄 Paper trading wallet reset to ₹{INITIAL_PAPER_WALLET_BALANCE:,.2f}")
    
    return jsonify({
        'success': True,
        'wallet_balance': app_state['paper_wallet_balance'],
        'message': f'Wallet reset to ₹{INITIAL_PAPER_WALLET_BALANCE:,.2f}'
    })

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
@app.route('/api/zerodha/session-status')
def api_zerodha_session_status():
    """Get current Zerodha session status"""
    try:
        if not app_state.get('kite') or not KITE_CONFIG.get('access_token'):
            return jsonify({
                'connected': False,
                'status': 'not_initialized',
                'message': 'Zerodha not connected',
                'last_check': None
            })
        
        # Test connection
        try:
            profile = app_state['kite'].profile()
            return jsonify({
                'connected': True,
                'status': 'active',
                'message': f'Connected as {profile.get("user_name", "User")}',
                'user_name': profile.get('user_name', 'User'),
                'broker': profile.get('broker', 'Unknown'),
                'last_check': dt.now().strftime('%H:%M:%S')
            })
        except Exception as e:
            error_msg = str(e).lower()
            if any(keyword in error_msg for keyword in ['session', 'token', 'expired', 'invalid', 'unauthorized']):
                app_state['zerodha_connected'] = False
                return jsonify({
                    'connected': False,
                    'status': 'session_expired',
                    'message': 'Session expired - please login again',
                    'last_check': dt.now().strftime('%H:%M:%S')
                })
            else:
                return jsonify({
                    'connected': False,
                    'status': 'connection_error',
                    'message': f'Connection error: {str(e)}',
                    'last_check': dt.now().strftime('%H:%M:%S')
                })
    except Exception as e:
        return jsonify({
            'connected': False,
            'status': 'error',
            'message': f'Status check failed: {str(e)}',
            'last_check': dt.now().strftime('%H:%M:%S')
        })

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
    """Get wallet info from Paper Trading or Zerodha account (based on mode)"""
    print(f"[DEBUG] /api/wallet-info called")
    
    # Check if paper trading is enabled
    if app_state['paper_trading_enabled']:
        # Paper Trading Mode
        total_investment = sum(pos['total_cost'] for pos in app_state['paper_positions'])
        total_positions = len(app_state['paper_positions'])
        total_trades = len(app_state['paper_trade_history'])
        
        # Calculate total P&L from current positions
        total_current_value = 0
        for pos in app_state['paper_positions']:
            current_price = pos.get('current_price', pos['buy_price'])
            total_current_value += current_price * pos['quantity']
        
        unrealized_pnl = total_current_value - total_investment
        
        # Calculate realized P&L from trade history
        realized_pnl = sum(trade['pnl'] for trade in app_state['paper_trade_history'])
        
        return jsonify({
            'success': True,
            'wallet_balance': app_state['paper_wallet_balance'],
            'total_investment': total_investment,
            'current_value': total_current_value,
            'unrealized_pnl': unrealized_pnl,
            'realized_pnl': realized_pnl,
            'total_pnl': unrealized_pnl + realized_pnl,
            'total_positions': total_positions,
            'total_trades': total_trades,
            'mode': 'paper',
            'paper_trading_enabled': True,
            'zerodha_connected': False
        })
    
    # Live Trading Mode
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
            'waiting_positions': 0,
            'mode': 'live',
            'paper_trading_enabled': False
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
    """Fetch expiry dates for a given symbol using TrueData API
    NOTE: This function ONLY uses real TrueData API data.
    No dummy/fallback data is generated - returns error if API fails.
    """
    expiry_url = f"https://history.truedata.in/getSymbolExpiryList?symbol={symbol}&response=csv"
    headers = {
        "accept": "application/json",
        "authorization": "Bearer ump5ksCOXfao5QuWAJqFnFSCGBxVq4YjZrEGiWC2dXfjadn2U2lF4hCfys40LnT-rMI0E-IRD1pZO-hRTvHMFV6OBitR0kBdBKG3h5VEO8-wpLweQu5kWLYyxTidEkYXVxyxr3VjMftQ6LuH5aBP1iXT1ydMKm6rH4BqGzuMcgn3VsB2yKv-wKJIgFlvGa2FhI7lwbOKKvJnwyxtxXJPkpv5bWvfl1dF1fljV0UUwyyK2BsN4BJ-WA7WmAraOYhKZaHknTKwe-z1RrUkpYyZCQ"  # 🔴 REPLACE THIS WITH YOUR REAL TOKEN
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
            print(f"❌ TrueData API Error: HTTP {response.status_code}")
            print(f"Response: {response.text[:200]}")
            return jsonify({
                'error': f'Failed to fetch expiry dates from TrueData API (HTTP {response.status_code})',
                'details': 'Please check your Bearer token and API credentials'
            }), 500
    except Exception as e:
        print(f"❌ Exception fetching expiry list: {str(e)}")
        return jsonify({
            'error': f'Exception occurred while fetching expiry dates: {str(e)}',
            'details': 'Please check your TrueData API configuration'
        }), 500

@app.route('/api/start-option-chain', methods=['POST'])
def api_start_option_chain():
    data = request.get_json()
    symbol = data.get('symbol')
    expiry = data.get('expiry')
    
    if not symbol or not expiry:
        return jsonify({'success': False, 'message': 'Symbol and expiry required'})
    
    try:
        # Ensure expiry is a string, not dict
        if isinstance(expiry, dict):
            expiry = expiry.get('value', str(expiry))
        expiry = str(expiry)
        
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
        
        # Fix LTP bug: If most LTP values are the underlying price, calculate from bid-ask
        unique_ltp_values = df_chain['ltp'].unique()
        underlying_price = 24868.6  # Current NIFTY price
        
        # Count how many options have LTP = underlying price (this is the bug)
        options_with_underlying_ltp = (df_chain['ltp'] == underlying_price).sum()
        total_options = len(df_chain)
        
        if options_with_underlying_ltp >= (total_options * 0.5):  # If 50%+ options have underlying price as LTP
            print(f"🐛 LTP BUG DETECTED: {options_with_underlying_ltp}/{total_options} options showing underlying price ({underlying_price})")
            print(f"🔧 FIXING: Using bid-ask midpoint for LTP calculation")
            
            # Calculate LTP as midpoint of bid-ask where LTP = underlying price
            for idx in df_chain.index:
                current_ltp = df_chain.loc[idx, 'ltp']
                
                # Only fix if LTP is the underlying price (this is the bug)
                if current_ltp == underlying_price:
                    bid = df_chain.loc[idx, 'bid']
                    ask = df_chain.loc[idx, 'ask'] 
                    
                    if pd.notna(bid) and pd.notna(ask) and bid > 0 and ask > 0:
                        # Use bid-ask midpoint
                        df_chain.loc[idx, 'ltp'] = (bid + ask) / 2
                    elif pd.notna(bid) and bid > 0:
                        # Use bid if ask is not available
                        df_chain.loc[idx, 'ltp'] = bid
                    elif pd.notna(ask) and ask > 0:
                        # Use ask if bid is not available  
                        df_chain.loc[idx, 'ltp'] = ask
                    # If both bid and ask are 0 or NaN, keep original LTP
            
            print(f"✅ LTP FIXED: New LTP range {df_chain['ltp'].min():.2f} - {df_chain['ltp'].max():.2f}")
            print(f"✅ Fixed options now have proper LTP values")
        else:
            print(f"✅ LTP OK: Only {options_with_underlying_ltp}/{total_options} options have underlying price")
        
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
        
        # Store FULL option chain data for position lookup (not just top 5)
        # This ensures positions API can find ALL strikes, not just first 5
        app_state['current_option_data'] = {
            'success': True,
            'underlying': float(underlying) if underlying else None,
            'atm_strike': float(atm_strike) if atm_strike else None,
            'calls': convert_df_to_records(calls),  # ALL calls, not just head(5)
            'puts': convert_df_to_records(puts),   # ALL puts, not just head(5)
            'atm': convert_df_to_records(atm),
            'total_options': len(df_chain),
            'ce_count': len(df_chain[df_chain['option_type'] == 'CE']),
            'pe_count': len(df_chain[df_chain['option_type'] == 'PE'])
        }
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# Paper Trading Helper Functions
def paper_buy_option(strike, option_type, price, quantity, lot_size):
    """Execute paper buy order and add to auto-trading monitoring"""
    total_qty = quantity * lot_size
    total_cost = total_qty * price
    
    # Check if enough balance
    if app_state['paper_wallet_balance'] < total_cost:
        return False, f"Insufficient balance. Required: ₹{total_cost:.2f}, Available: ₹{app_state['paper_wallet_balance']:.2f}"
    
    # Deduct from wallet
    app_state['paper_wallet_balance'] -= total_cost
    
    # FIXED: MANUAL BUY STOP LOSS = buy_price - 10 (NOT buy_price)
    manual_buy_stop_loss = price - 10  # Manual buy: 10 points below buy price
    
    # Create position
    position = {
        'id': f"paper_{len(app_state['paper_positions'])}_{int(time.time())}",
        'strike': strike,
        'option_type': option_type,
        'buy_price': price,
        'quantity': total_qty,
        'lots': quantity,
        'total_cost': total_cost,
        'timestamp': get_ist_timestamp(),
        'symbol': app_state.get('current_symbol', 'NIFTY'),
        'expiry': app_state.get('current_expiry', ''),
        'current_price': price,
        'pnl': 0.0,
        'pnl_percentage': 0.0,
        # CRITICAL FIX: Manual buy stop loss fields
        'stop_loss_price': manual_buy_stop_loss,  # 10 points below buy price
        'original_buy_price': price,
        'highest_price': price,  # Initialize highest price to buy price
        'minimum_stop_loss': manual_buy_stop_loss,  # Absolute minimum stop loss
        'auto_buy_count': 0,
        'auto_sell_count': 0,
        'total_pnl': 0.0,
        'mode': 'Auto-Monitoring',
        'waiting_for_autobuy': False,
        'sell_triggered': False,
        'manual_sold': False,
        'qty': total_qty,  # For compatibility with auto-trading functions
        'type': option_type,  # For compatibility with auto-trading functions
        'last_update': dt.now(),  # Add last update timestamp
        'entry_time': dt.now(),  # Add entry time
        'auto_bought': False,  # CRITICAL: Mark as NOT auto bought (manual buy)
        'l_cooldown_enabledindividua': True,  # NEW: Individual cooldown control
        'manual_buy_price': price,  # RULE-BASED: Entry price anchor for new algorithm
        're_entry_enabled': True  # RULE-BASED: Always enabled for confirmation re-entry
    }
    
    app_state['paper_positions'].append(position)
    
    # Also add to auto_positions for stop-loss monitoring
    auto_position = position.copy()
    app_state['auto_positions'].append(auto_position)
    
    # Add to order history
    order = {
        'id': position['id'],
        'type': 'BUY',
        'action': 'Buy',  # Add action field for frontend
        'strike': strike,
        'option_type': option_type,
        'price': price,
        'buy_price': price,  # Add for consistency
        'quantity': total_qty,
        'qty': total_qty,  # Add qty field for frontend
        'lots': quantity,
        'total_value': total_cost,
        'timestamp': position['timestamp'],
        'time': get_ist_time_formatted(),  # IST formatted time
        'status': 'COMPLETE'
    }
    
    app_state['paper_orders'].append(order)
    
    # Add to trade history for complete tracking
    trade_record = {
        'id': position['id'],
        'action': 'Manual Buy',  # Clearly mark as manual buy
        'type': option_type,
        'option_type': option_type,
        'strike': strike,
        'qty': total_qty,
        'quantity': total_qty,
        'price': price,
        'buy_price': price,
        'pnl': 0,  # No PnL at buy time
        'total_value': total_cost,
        'timestamp': position['timestamp'],
        'time': dt.now().strftime('%Y-%m-%d %H:%M:%S'),
        'status': 'COMPLETE',
        'mode': 'Paper Trading',
        'trading_mode': 'paper'
    }
    
    app_state['paper_trade_history'].append(trade_record)
    
    # Emit real-time trade history update
    socketio.emit('trade_history_update', {
        'trade': trade_record,
        'total_trades': len(app_state['paper_trade_history'])
    })
    
    print(f"📄 MANUAL BUY: {quantity} lot(s) of {option_type} {strike} @ ₹{price:.2f} = ₹{total_cost:.2f}")
    print(f"🛡️ MANUAL BUY STOP LOSS: ₹{manual_buy_stop_loss:.2f} (Buy Price - 10)")
    
    return True, position

def paper_sell_option(strike, option_type, price, quantity, lot_size):
    """Execute paper sell order - Enhanced to sell ALL lots of same strike if needed"""
    total_qty = quantity * lot_size
    
    # 🚨 FIX: Find ALL matching positions for this strike and sell them together
    matching_positions = []
    total_available_qty = 0
    
    for pos in app_state['paper_positions']:
        if (pos['strike'] == strike and pos['option_type'] == option_type):
            matching_positions.append(pos)
            total_available_qty += pos['quantity']
    
    if not matching_positions:
        return False, f"No matching position found for {option_type} {strike}"
    
    # If user wants to sell more than available, sell everything available
    if total_qty > total_available_qty:
        print(f"⚠️ Requested {total_qty} but only {total_available_qty} available. Selling ALL available.")
        total_qty = total_available_qty
    
    # Calculate total cost and P&L for all matching positions
    total_cost = 0
    remaining_to_sell = total_qty
    positions_to_remove = []
    positions_to_update = []
    
    for pos in matching_positions:
        if remaining_to_sell <= 0:
            break
            
        pos_qty = pos['quantity']
        pos_cost = pos.get('total_cost', pos_qty * pos['buy_price'])
        cost_per_qty = pos_cost / pos_qty
        
        if remaining_to_sell >= pos_qty:
            # Sell entire position
            qty_to_sell_from_this_pos = pos_qty
            cost_from_this_pos = pos_cost
            positions_to_remove.append(pos)
        else:
            # Sell partial position
            qty_to_sell_from_this_pos = remaining_to_sell
            cost_from_this_pos = qty_to_sell_from_this_pos * cost_per_qty
            pos['quantity'] -= qty_to_sell_from_this_pos
            pos['total_cost'] = pos.get('total_cost', pos_qty * pos['buy_price']) - cost_from_this_pos
            positions_to_update.append(pos)
        
        total_cost += cost_from_this_pos
        remaining_to_sell -= qty_to_sell_from_this_pos
    
    # Calculate P&L
    sell_value = total_qty * price
    pnl = sell_value - total_cost
    
    # Add to wallet
    app_state['paper_wallet_balance'] += sell_value
    
    # Mark as manually sold in auto-positions to prevent auto-buy
    for auto_pos in app_state['auto_positions']:
        if (auto_pos.get('strike') == strike and 
            auto_pos.get('option_type', auto_pos.get('type')) == option_type):
            auto_pos['manual_sold'] = True
            auto_pos['sold'] = True
            print(f"🔴 Marked auto-position as manually sold: {strike} {option_type}")
    
    # Apply position changes
    for pos in positions_to_remove:
        app_state['paper_positions'].remove(pos)
    
    # Calculate actual lots sold
    actual_lots_sold = total_qty // lot_size
    
    # Add to order history
    order = {
        'id': f"paper_sell_{len(app_state['paper_orders'])}_{int(time.time())}",
        'type': 'SELL',
        'strike': strike,
        'option_type': option_type,
        'price': price,
        'quantity': total_qty,
        'lots': actual_lots_sold,
        'total_value': sell_value,
        'pnl': pnl,
        'timestamp': get_ist_timestamp(),
        'status': 'COMPLETE',
        'reason': 'Manual Sell (ALL LOTS)'
    }
    
    app_state['paper_orders'].append(order)
    
    # Add to trade history
    avg_cost_per_qty = total_cost / total_qty if total_qty > 0 else 0
    trade = {
        'buy_price': avg_cost_per_qty,
        'sell_price': price,
        'price': price,  # Add this for frontend compatibility
        'quantity': total_qty,
        'qty': total_qty,  # Add this for frontend compatibility
        'lots': actual_lots_sold,
        'pnl': pnl,
        'pnl_percentage': (pnl / total_cost) * 100 if total_cost > 0 else 0,
        'strike': strike,
        'option_type': option_type,
        'type': option_type,  # Add this for frontend compatibility
        'action': 'Sell',  # Add action field
        'timestamp': order['timestamp'],
        'time': get_ist_time_formatted(),  # IST formatted time
        'reason': 'Manual Sell (ALL LOTS)'
    }
    
    app_state['paper_trade_history'].append(trade)
    
    print(f"📄 Paper MANUAL SELL: {actual_lots_sold} lot(s) ({total_qty} units) of {option_type} {strike} @ ₹{price:.2f} = ₹{sell_value:.2f} (P&L: ₹{pnl:.2f})")
    
    # Clean up auto-positions that are manually sold
    app_state['auto_positions'] = [pos for pos in app_state['auto_positions'] 
                                  if not (pos.get('manual_sold', False) and 
                                         pos.get('strike') == strike and 
                                         pos.get('option_type', pos.get('type')) == option_type)]
    
    return True, {'order': order, 'trade': trade}

@app.route('/api/buy-option', methods=['POST'])
def api_buy_option():
    """Buy option through Paper Trading or Zerodha (based on mode)"""
    data = request.get_json()
    strike = float(data.get('strike'))
    option_type = data.get('option_type')
    price = float(data.get('price'))
    lots = int(data.get('lots', 1))
    symbol = data.get('symbol', 'NIFTY')
    expiry = data.get('expiry', '')
    
    # Debug: Print current paper trading status
    print(f"🐛 DEBUG BUY: paper_trading_enabled = {app_state['paper_trading_enabled']}")
    print(f"🐛 DEBUG BUY: PAPER_TRADING_ENABLED = {PAPER_TRADING_ENABLED}")
    print(f"🐛 DEBUG BUY: Strike={strike}, Type={option_type}, Price={price}, Lots={lots}")
    
    # Check if paper trading is enabled
    if app_state['paper_trading_enabled']:
        print(f"📄 PAPER TRADING MODE: Processing buy order")
        # Paper Trading Mode
        lot_size = LOT_SIZES.get(symbol, 75)
        success, result = paper_buy_option(strike, option_type, price, lots, lot_size)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'📄 Paper order placed: {lots} lot(s) of {option_type} {strike}',
                'order_id': result['id'],
                'wallet_balance': app_state['paper_wallet_balance'],
                'mode': 'paper'
            })
        else:
            return jsonify({
                'success': False,
                'message': result,
                'mode': 'paper'
            })
    
    print(f"🏦 LIVE TRADING MODE: Checking Zerodha connection")
    # Live Trading Mode - Check Zerodha connection
    is_connected = app_state['zerodha_connected']
    if not is_connected:
        return jsonify({
            'success': False, 
            'message': f'Cannot trade: Zerodha not connected. Please complete Zerodha login first.',
            'mode': 'live'
        })
    
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
    
    # ⚡ PERFORMANCE FIX: Fast symbol conversion with minimal overhead
    print(f"[FAST BUY] Converting {td_symbol} to Zerodha symbol...")
    start_time = time.time()
    
    # Try conversion using the new unified method
    tradingsymbol = td_to_zerodha_symbol(td_symbol)
    if not tradingsymbol:
        # If td_to_zerodha_symbol fails, try get_zerodha_symbol directly
        tradingsymbol, token, error = get_zerodha_symbol(td_symbol)
        
        if not tradingsymbol:
            print(f"[ERROR] Symbol conversion failed for: {td_symbol} - Error: {error}")
            return jsonify({
                "success": False,
                "message": f"❌ Symbol not found: {td_symbol}",
                "error": error
            }), 400
    
    conversion_time = (time.time() - start_time) * 1000  # milliseconds
    print(f"[FAST BUY] Symbol conversion took {conversion_time:.0f}ms → {tradingsymbol}")
    
    lot_size = LOT_SIZES.get(symbol, 75)
    total_qty = lot_size * lots
    
    # ⚡ CRITICAL FIX: Use MARKET order for INSTANT execution (not LIMIT)
    print(f"[FAST BUY] Placing MARKET order for {total_qty} qty of {tradingsymbol}...")
    order_start_time = time.time()
    
    try:
        order_id = app_state['kite'].place_order(
            variety=app_state['kite'].VARIETY_REGULAR,
            exchange=app_state['kite'].EXCHANGE_NFO,
            tradingsymbol=tradingsymbol,
            transaction_type=app_state['kite'].TRANSACTION_TYPE_BUY,
            quantity=total_qty,
            order_type=app_state['kite'].ORDER_TYPE_MARKET,  # ⚡ MARKET order = instant fill
            product=app_state['kite'].PRODUCT_MIS,
            validity=app_state['kite'].VALIDITY_DAY
        )
        
        order_time = (time.time() - order_start_time) * 1000  # milliseconds
        total_time = (time.time() - start_time) * 1000  # milliseconds
        
        print(f"[FAST BUY] ✅ Order placed in {order_time:.0f}ms (Total: {total_time:.0f}ms)")
        print(f"[FAST BUY] Order ID: {order_id}")
        
        # Record trade in local tracking (async - don't wait)
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

        # ⚡ FAST: Create auto-position for stop-loss monitoring (non-blocking)
        position = create_auto_position(strike, option_type, price, total_qty, symbol, expiry)
        
        print(f"[FAST BUY] ✅ Complete! Auto-trading enabled with SL @ ₹{position['stop_loss_price']}")
        
        return jsonify({
            'success': True,
            'message': f'⚡ INSTANT BUY: {total_qty} {option_type} @ Market ({total_time:.0f}ms)',
            'order_id': order_id,
            'tradingsymbol': tradingsymbol,
            'execution_time_ms': int(total_time),
            'order_time_ms': int(order_time)
        })
    except Exception as e:
        error_msg = str(e)
        error_time = (time.time() - start_time) * 1000
        print(f"[FAST BUY] ❌ Order failed after {error_time:.0f}ms: {error_msg}")
        
        # Quick error responses
        if "expired or does not exist" in error_msg or "invalid trading symbol" in error_msg.lower():
            return jsonify({
                'success': False,
                'message': f'❌ Symbol Error: {tradingsymbol} not found'
            }), 400
        else:
            return jsonify({
                'success': False,
                'message': f'❌ Order failed: {error_msg}'
            }), 400

@app.route('/api/sell-option', methods=['POST'])
def api_sell_option():
    """Sell option through Paper Trading or Zerodha (based on mode)"""
    data = request.get_json()
    strike = float(data.get('strike'))
    option_type = data.get('option_type')
    price = float(data.get('price'))
    symbol = data.get('symbol', 'NIFTY')
    expiry = data.get('expiry', '')
    lots = int(data.get('lots', 0))  # 0 means sell ALL lots of this strike
    
    # Debug: Print current paper trading status
    print(f"🐛 DEBUG SELL: paper_trading_enabled = {app_state['paper_trading_enabled']}")
    print(f"🐛 DEBUG SELL: PAPER_TRADING_ENABLED = {PAPER_TRADING_ENABLED}")
    print(f"🐛 DEBUG SELL: Strike={strike}, Type={option_type}, Price={price}, Lots={lots}")
    
    # Check if paper trading is enabled
    if app_state['paper_trading_enabled']:
        print(f"📄 PAPER TRADING MODE: Processing sell order")
        
        # 🚨 FIX: If lots=0 or not specified, find total lots for this strike and sell ALL
        if lots == 0:
            total_lots_for_strike = 0
            lot_size = LOT_SIZES.get(symbol, 75)
            
            for pos in app_state['paper_positions']:
                if (pos['strike'] == strike and pos['option_type'] == option_type):
                    total_lots_for_strike += pos['quantity'] // lot_size
            
            if total_lots_for_strike > 0:
                lots = total_lots_for_strike
                print(f"🎯 AUTO-DETECTED: Found {total_lots_for_strike} lot(s) of {option_type} {strike} - Selling ALL")
            else:
                return jsonify({
                    'success': False,
                    'message': f'No position found for {option_type} {strike}',
                    'mode': 'paper'
                })
        
        # Paper Trading Mode
        lot_size = LOT_SIZES.get(symbol, 75)
        success, result = paper_sell_option(strike, option_type, price, lots, lot_size)
        
        if success:
            pnl = result['trade']['pnl']
            pnl_text = f"Profit: ₹{pnl:.2f}" if pnl >= 0 else f"Loss: ₹{abs(pnl):.2f}"
            
            return jsonify({
                'success': True,
                'message': f'📄 Paper sell order placed: {lots} lot(s) of {option_type} {strike} ({pnl_text})',
                'order_id': result['order']['id'],
                'wallet_balance': app_state['paper_wallet_balance'],
                'pnl': pnl,
                'mode': 'paper'
            })
        else:
            return jsonify({
                'success': False,
                'message': result,
                'mode': 'paper'
            })
    
    print(f"🏦 LIVE TRADING MODE: Checking Zerodha connection")
    # Live Trading Mode - Check Zerodha connection
    is_connected = app_state['zerodha_connected']
    if not is_connected:
        return jsonify({
            'success': False, 
            'message': f'Cannot trade: Zerodha not connected. Please complete Zerodha login first.',
            'mode': 'live'
        })
    
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
    print(f"[DEBUG] Expiry details: original={expiry}, parsed_td={expiry_td}")
    
    # Try both conversion methods
    tradingsymbol = td_to_zerodha_symbol(td_symbol)
    if not tradingsymbol:
        # Try CSV-based conversion as fallback - need to convert format first
        print(f"[DEBUG] Trying CSV-based conversion for: {td_symbol}")
        # Convert YYMMDD format to YYMM format for CSV lookup
        if len(expiry_td) == 6:  # YYMMDD format
            yymm_format = expiry_td[:4]  # Take first 4 chars (YYMM)
            csv_td_symbol = f"{symbol}{yymm_format}{int(strike)}{option_type}"
            print(f"[DEBUG] CSV format symbol: {csv_td_symbol}")
            tradingsymbol, token, error = get_zerodha_symbol(csv_td_symbol)
        else:
            tradingsymbol, token, error = get_zerodha_symbol(td_symbol)
        
        if not tradingsymbol:
            print(f"[ERROR] Both conversion methods failed for: {td_symbol}")
            print(f"[ERROR] CSV conversion error: {error}")
            return jsonify({"error": f"❌ Trading Symbol not found in Zerodha for {td_symbol}. Error: {error}"}), 400
    
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
        
        # Place sell order through Zerodha with all required parameters
        order_id = app_state['kite'].place_order(
            variety=app_state['kite'].VARIETY_REGULAR,
            exchange=app_state['kite'].EXCHANGE_NFO,
            tradingsymbol=tradingsymbol,
            transaction_type=app_state['kite'].TRANSACTION_TYPE_SELL,
            quantity=quantity,
            order_type=app_state['kite'].ORDER_TYPE_MARKET,
            product=app_state['kite'].PRODUCT_MIS,
            validity=app_state['kite'].VALIDITY_DAY  # Required parameter
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
        
        # Emit trade update for frontend
        socketio.emit('trade_history_update', {
            'trade': {
                'action': 'Sell (LIVE)',
                'type': option_type,
                'strike': strike,
                'qty': quantity,
                'price': price,
                'pnl': pnl,
                'order_id': order_id,
                'tradingsymbol': tradingsymbol,
                'time': dt.now().strftime('%Y-%m-%d %H:%M:%S'),
                'mode': 'live',
                'stop_loss_price': position_found.get('stop_loss', '-')
            }
        })
        # Emit updated positions to frontend (with stop_loss_price)
        positions = app_state['kite'].positions()['net']
        all_positions = []
        for pos in positions:
            position_data = {
                'tradingsymbol': pos['tradingsymbol'],
                'quantity': int(pos['quantity']),
                'average_price': float(pos['average_price']),
                'last_price': float(pos['last_price']),
                'pnl': float(pos['unrealised']),
                'realized_pnl': float(pos['realised']),
                'instrument_token': pos['instrument_token'],
                'exchange': pos['exchange'],
                'product': pos['product'],
                'stop_loss_price': pos.get('stop_loss', '-')
            }
            all_positions.append(position_data)
        socketio.emit('positions_update', {'positions': all_positions})
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

@app.route('/api/cancel-pending-position', methods=['POST'])
def api_cancel_pending_position():
    """Cancel pending position to prevent further auto buy/sell"""
    data = request.get_json()
    position_key = data.get('position_key')
    
    if not position_key:
        return jsonify({
            'success': False,
            'message': 'Position key is required'
        })
    
    print(f"🚨 Cancelling pending position: {position_key}")
    
    # Find and update the position in auto positions
    position_found = False
    for pos in app_state.get('auto_positions', []):
        # Match by position key - try multiple formats
        pos_key = pos.get('id')  # First try ID
        
        if not pos_key:
            # Try strike-type format
            pos_key = f"{pos.get('strike', '')}-{pos.get('type', '')}"
        
        # Also try symbol format for comparison
        pos_symbol_key = None
        if pos.get('strike') and pos.get('type'):
            pos_symbol_key = f"{pos.get('type', '')}{pos.get('strike', '')}"
        
        print(f"🔎 Checking auto position: ID={pos.get('id')}, strike-type={pos_key}, symbol={pos_symbol_key}")
        
        # Check if any of the keys match
        if pos_key == position_key or (pos_symbol_key and pos_symbol_key == position_key):
            # Set status to CANCELLED and disable waiting_for_autobuy
            pos['status'] = 'CANCELLED'
            pos['waiting_for_autobuy'] = False
            position_found = True
            print(f"✅ Cancelled pending position: {position_key} -> matched {pos_key or pos_symbol_key}")
            # Remove the auto position from active auto positions so it no longer appears as PENDING
            try:
                app_state['auto_positions'].remove(pos)
                print(f"🗑️ Removed auto position from app_state['auto_positions']: {position_key}")
            except Exception as e:
                print(f"⚠️ Failed to remove auto position from list: {e}")
            break

    if not position_found:
        # If not found in auto_positions, collect available auto position keys for debugging
        available_keys = []
        for pos in app_state.get('auto_positions', []):
            k = pos.get('id') or f"{pos.get('strike', '')}-{pos.get('type', '')}"
            available_keys.append(k)

        print(f"⚠️ Pending position not found in auto_positions: {position_key}. Available keys: {available_keys}")
        # Continue execution to attempt removal from paper_positions and emit updates.
        # Treat missing auto position as idempotent (already cancelled/removed).

    # Also remove matching entries from paper_positions (if any) so pending row disappears
    removed_paper = 0
    try:
        new_paper_positions = []
        for p in app_state.get('paper_positions', []):
            # Match by id or tradingsymbol or strike-type
            p_key = p.get('id') or p.get('tradingsymbol') or f"paper_{p.get('mode','paper')}_{p.get('timestamp', '')}"
            if p_key == position_key or p.get('tradingsymbol') == position_key:
                print(f"🗑️ Removing matching paper position: {p_key}")
                removed_paper += 1
                continue
            # Try matching by strike-type if present in position_key
            try:
                if '-' in position_key:
                    parts = position_key.split('-')
                    if len(parts) >= 2:
                        strike_part = parts[0]
                        type_part = parts[1]
                        if str(p.get('strike')) == strike_part and (p.get('option_type') == type_part or p.get('type') == type_part):
                            print(f"🗑️ Removing paper position by strike-type match: {p_key}")
                            removed_paper += 1
                            continue
            except Exception:
                pass
            new_paper_positions.append(p)
        if removed_paper > 0:
            app_state['paper_positions'] = new_paper_positions
            print(f"🗑️ Removed {removed_paper} paper_positions matching {position_key}")
    except Exception as e:
        print(f"⚠️ Error while removing paper positions: {e}")

    # Save updated positions to file (use auto_positions)
    try:
        with open('auto_positions.json', 'w') as f:
            json.dump(app_state.get('auto_positions', []), f, indent=2, default=str)
        print(f"💾 Saved cancelled position status to auto_positions.json")
    except Exception as e:
        print(f"⚠️ Failed to save auto_positions to file: {e}")

    # Emit updated positions to frontend so pending row disappears without reload
    try:
        with app.test_request_context():
            positions_resp = api_positions().get_json()
            socketio.emit('positions_update', positions_resp)
            # Also emit auto positions update
            auto_resp = api_auto_trading_positions().get_json()
            socketio.emit('auto_positions_update', auto_resp)
            print("🔔 Emitted updated positions to frontend after cancel")
    except Exception as e:
        print(f"⚠️ Failed to emit updated positions: {e}")
    
    return jsonify({
        'success': True,
        'message': f'✅ Pending position cancelled: {position_key}. No further auto buy/sell will occur.'
    })


@app.route('/api/debug-auto-keys')
def api_debug_auto_keys():
    """Return current auto and paper position keys for debugging mismatches"""
    keys = {
        'auto_positions_keys': [],
        'paper_positions_keys': [],
        'auto_trading_positions_keys': []
    }

    for pos in app_state.get('auto_positions', []):
        k = pos.get('id') or f"{pos.get('strike', '')}-{pos.get('type', '')}"
        keys['auto_positions_keys'].append(k)

    for pos in app_state.get('paper_positions', []):
        k = pos.get('id') or pos.get('tradingsymbol') or f"paper_{pos.get('mode', 'paper')}_{int(time.time())}"
        keys['paper_positions_keys'].append(k)

    for pos in app_state.get('auto_trading_positions', []):
        k = pos.get('id') or f"{pos.get('strike', '')}-{pos.get('option_type', '')}"
        keys['auto_trading_positions_keys'].append(k)

    return jsonify({'success': True, 'keys': keys})

@app.route('/api/debug-auto-trading')
def api_debug_auto_trading():
    """Debug endpoint to check auto trading status"""
    auto_positions = app_state.get('auto_positions', [])
    
    debug_info = {
        'auto_trading_enabled': app_state.get('auto_trading_enabled'),
        'auto_trading_running': app_state.get('auto_trading_running'),
        'paper_trading_enabled': app_state.get('paper_trading_enabled'),
        'total_auto_positions': len(auto_positions),
        'positions': []
    }
    
    for pos in auto_positions:
        debug_info['positions'].append({
            'strike': pos.get('strike'),
            'type': pos.get('type'),
            'qty': pos.get('qty'),
            'buy_price': pos.get('buy_price'),
            'current_price': pos.get('current_price'),
            'stop_loss_price': pos.get('stop_loss_price'),
            'waiting_for_autobuy': pos.get('waiting_for_autobuy', False),
            'sold': pos.get('sold', False),
            'sell_triggered': pos.get('sell_triggered', False),
            'sell_in_progress': pos.get('sell_in_progress', False)
        })
    
    return jsonify(debug_info)

@app.route('/api/positions')
def api_positions():
    """Get positions from Paper Trading or Zerodha account (based on mode)"""
    
    # Check if paper trading is enabled
    if app_state['paper_trading_enabled']:
        # Paper Trading Mode - Return paper positions
        paper_positions = []
        
        print(f"📊 API POSITIONS: Paper trading enabled, {len(app_state['paper_positions'])} positions found")
        print(f"📊 Trading algorithm: {app_state.get('trading_algorithm', 'unknown')}")
        
        # Update current prices for paper positions if we have option chain data
        current_option_data = app_state.get('current_option_data', {})
        
        for pos in app_state['paper_positions']:
            # Try to find current price from option chain data
            current_price = pos['buy_price']  # Default to buy price
            
            print(f"🔍 Looking for position: Strike={pos['strike']}, Type={pos['option_type']}")
            print(f"🔍 Position Buy Price: ₹{pos['buy_price']}")
            
            # Look for current price in option chain data
            if current_option_data:
                price_found = False
                print(f"📊 Available option data sections: {list(current_option_data.keys())}")
                
                for option_type_data in ['calls', 'puts', 'atm']:
                    if option_type_data in current_option_data:
                        options_list = current_option_data[option_type_data]
                        print(f"📊 Checking {option_type_data}: {len(options_list)} options")
                        
                        for i, option in enumerate(options_list):
                            # Debug: Print option details
                            option_strike = option.get('strike')
                            option_type = option.get('option_type')
                            option_ltp = option.get('ltp')
                            
                            # Print first few options in each section for debugging
                            if i < 3:
                                print(f"    Option {i}: Strike={option_strike}, Type={option_type}, LTP=₹{option_ltp}")
                            
                            # Try multiple field names for option type matching
                            option_type_variations = [
                                option.get('option_type'),
                                option.get('type'),
                                'CE' if 'CE' in str(option_type_data).upper() or 'call' in str(option_type_data).lower() else None,
                                'PE' if 'PE' in str(option_type_data).upper() or 'put' in str(option_type_data).lower() else None
                            ]
                            
                            # Check if this option matches our position
                            strike_match = (float(option_strike) == float(pos['strike']))
                            type_match = pos['option_type'] in option_type_variations
                            
                            if strike_match and type_match:
                                current_price = option_ltp
                                price_found = True
                                print(f"✅ MATCH FOUND for {pos['strike']} {pos['option_type']}")
                                print(f"✅ Using LTP: ₹{current_price} (was buy price: ₹{pos['buy_price']})")
                                break
                        if price_found:
                            break
                
                if not price_found:
                    print(f"❌ NO MATCH found for {pos['strike']} {pos['option_type']}")
                    print(f"❌ Using fallback buy price: ₹{current_price}")
            else:
                print(f"❌ No option chain data available")
            
            # Update position with current price and P&L
            pos['current_price'] = current_price
            
            # 🎯 RULE-BASED ALGORITHM: Update stop loss with new current price
            print(f"🔍 DEBUGGING: Position {pos['strike']} {pos['option_type']} - Current: ₹{current_price}, Buy: ₹{pos['buy_price']}")
            print(f"🔍 Algorithm setting: {app_state.get('trading_algorithm', 'unknown')}")
            
            if app_state.get('trading_algorithm') == 'advanced':
                try:
                    update_advanced_algorithm(pos, current_price)
                    calculated_sl = pos.get('advanced_stop_loss', 'NOT_SET')
                    print(f"🎯 RULE-BASED: Updated stop loss for {pos['strike']} {pos['option_type']}: ₹{calculated_sl}")
                    # Copy to stop_loss_price for frontend compatibility
                    if calculated_sl != 'NOT_SET':
                        pos['stop_loss_price'] = calculated_sl
                    else:
                        # Fallback if algorithm didn't set stop loss
                        pos['stop_loss_price'] = pos['buy_price'] - 10
                        print(f"⚠️ RULE-BASED FAILED: Using fallback SL ₹{pos['stop_loss_price']}")
                except Exception as e:
                    print(f"❌ ERROR in rule-based algorithm: {e}")
                    pos['stop_loss_price'] = pos['buy_price'] - 10
                    print(f"🔧 ERROR FALLBACK: stop loss ₹{pos['stop_loss_price']}")
            else:
                # Simple algorithm fallback
                pos['stop_loss_price'] = pos['buy_price'] - 10
                print(f"🔧 SIMPLE: Fallback stop loss for {pos['strike']} {pos['option_type']}: ₹{pos['stop_loss_price']}")
            
            # 🚨 IMPROVED P&L LOGIC: Handle auto buy positions correctly
            if pos.get('waiting_for_autobuy', False):
                # Position is sold and waiting for auto-buy - show zero P&L and quantity
                pos['pnl'] = 0.0
                pos['pnl_percentage'] = 0.0
                display_quantity = 0  # Don't show quantity for waiting positions
            else:
                # Active position - calculate normal P&L
                display_quantity = pos.get('quantity', pos.get('qty', 0))
                if display_quantity > 0:
                    pos['pnl'] = (current_price - pos['buy_price']) * display_quantity
                    pos['pnl_percentage'] = ((current_price - pos['buy_price']) / pos['buy_price']) * 100 if pos['buy_price'] > 0 else 0
                else:
                    pos['pnl'] = 0.0
                    pos['pnl_percentage'] = 0.0
            
            # Format for frontend display
            stop_loss_value = pos.get('stop_loss_price', pos.get('advanced_stop_loss', pos['buy_price'] - 10))
            position_data = {
                'tradingsymbol': f"{pos['option_type']}{pos['strike']}",
                'quantity': display_quantity,
                'average_price': pos['buy_price'],
                'last_price': current_price,
                'pnl': pos['pnl'],
                'realized_pnl': 0.0,
                'lots': pos['lots'],
                'strike': pos['strike'],
                'option_type': pos['option_type'],
                'total_cost': pos['total_cost'],
                'id': pos['id'],
                'mode': 'paper',
                'stop_loss_price': stop_loss_value,  # Use calculated stop loss
                'highest_price': pos.get('highest_price', pos['buy_price']),  # Include highest price for display
                'auto_buy_count': pos.get('auto_buy_count', 0),  # Include auto buy count
                'auto_sell_count': pos.get('auto_sell_count', 0),  # Include auto sell count
                'waiting_for_autobuy': pos.get('waiting_for_autobuy', False),  # Include auto buy status
                'status': 'Cooldown Pending' if (pos.get('auto_buy_count', 0) >= 5 and pos.get('waiting_for_autobuy', False) and app_state.get('cooldown_enabled', True)) else ('Pending Auto-Buy' if pos.get('waiting_for_autobuy', False) else 'Active')
            }
            print(f"📤 SENDING TO FRONTEND: {pos['strike']} {pos['option_type']} - Stop Loss: ₹{stop_loss_value}")
            paper_positions.append(position_data)
        
        return jsonify({
            'success': True,
            'positions': paper_positions,
            'total_positions': len(paper_positions),
            'wallet_balance': app_state['paper_wallet_balance'],
            'mode': 'paper'
        })
    
    # Live Trading Mode - Check Zerodha connection
    is_connected, message = check_zerodha_connection()
    if not is_connected:
        return jsonify({
            'success': False,
            'message': f'Zerodha not connected: {message}',
            'positions': [],
            'mode': 'live'
        })
    
    try:
        # Get positions from Zerodha
        positions = app_state['kite'].positions()
        net_positions = positions['net']
        print(f"[DEBUG] Raw net_positions: {net_positions}")
        
        # 🔥 CRITICAL FIX: Get current option chain data for real-time price updates
        current_option_data = app_state.get('current_option_data', {})
        print(f"[DEBUG] Live Trading - Option chain data available: {bool(current_option_data)}")
        
        # 🔥 FILTER OUT CLOSED POSITIONS (qty=0) to prevent negative SL display
        all_positions = []
        for pos in net_positions:
            # Skip positions with quantity = 0 (already sold/closed)
            if int(pos['quantity']) == 0:
                print(f"[DEBUG] Skipping closed position: {pos['tradingsymbol']} qty=0")
                continue
                
            print(f"[DEBUG] Checking position: {pos['tradingsymbol']} qty={pos['quantity']}")
            
            # Try to extract strike and option_type from tradingsymbol if not present
            strike = pos.get('strike', None)
            option_type = pos.get('option_type', None)
            if not strike or not option_type:
                m = re.search(r'(\d+)(CE|PE)$', pos['tradingsymbol'])
                if m:
                    strike = int(m.group(1))
                    option_type = m.group(2)
            
            # 🔥 FIX: Get live price from option chain data (same as paper trading)
            live_price = float(pos['last_price'])  # Default to Zerodha's last price
            
            if current_option_data and strike and option_type:
                price_found = False
                print(f"🔍 LIVE: Looking for {strike} {option_type} in option chain")
                
                for option_type_data in ['calls', 'puts', 'atm']:
                    if option_type_data in current_option_data:
                        options_list = current_option_data[option_type_data]
                        
                        for option in options_list:
                            option_strike = option.get('strike')
                            opt_type = option.get('option_type', option.get('type'))
                            option_ltp = option.get('ltp')
                            
                            if float(option_strike) == float(strike) and opt_type == option_type:
                                live_price = float(option_ltp)
                                price_found = True
                                print(f"✅ LIVE PRICE UPDATE: {strike} {option_type} = ₹{live_price} (was ₹{pos['last_price']})")
                                break
                        if price_found:
                            break
                
                if not price_found:
                    print(f"⚠️ LIVE: No live price found for {strike} {option_type}, using Zerodha price ₹{live_price}")
            
            # Now match auto position and update with current price
            stop_loss_val = None  # Use None instead of 'No SL'
            status = 'Active'
            auto_buy_count = 0
            auto_pos_found = None
            
            for auto_pos in app_state.get('auto_positions', []):
                if str(auto_pos.get('strike')) == str(strike) and auto_pos.get('type', auto_pos.get('option_type')) == option_type:
                    auto_pos_found = auto_pos
                    
                    # 🔥 CRITICAL: Update auto position with live price for algorithm
                    if live_price != auto_pos.get('current_price', 0):
                        print(f"🔄 LIVE: Updating auto position {strike} {option_type} price: ₹{auto_pos.get('current_price', 0)} → ₹{live_price}")
                        update_auto_position_price(auto_pos, live_price)
                    
                    # Get stop loss from auto position (numeric value)
                    sl_price = auto_pos.get('stop_loss_price', auto_pos.get('advanced_stop_loss', 0))
                    if sl_price and sl_price > 0:
                        stop_loss_val = float(sl_price)
                        print(f"✅ LIVE: Auto position SL from auto_pos: ₹{stop_loss_val:.2f}")
                    
                    auto_buy_count = auto_pos.get('auto_buy_count', 0)
                    
                    if auto_pos.get('waiting_for_autobuy', False):
                        if auto_pos.get('auto_buy_count', 0) >= 5 and app_state.get('cooldown_enabled', True):
                            status = 'Cooldown Pending'
                        else:
                            status = 'Pending Auto-Buy'
                    
                    sl_display = f"₹{stop_loss_val:.2f}" if stop_loss_val else "calculating..."
                    print(f"✅ LIVE: Auto position matched - SL: {sl_display}, Status: {status}")
                    break
            
            # 🔥 FIX: If no auto position or no stop loss set, calculate default SL (buy_price - 10)
            if stop_loss_val is None or stop_loss_val == 0:
                avg_price = float(pos['average_price'])
                stop_loss_val = avg_price - 10  # Default: buy price - 10
                print(f"🔧 LIVE: Calculated default SL for {strike} {option_type}: ₹{avg_price} - 10 = ₹{stop_loss_val:.2f}")
                
                # 🔥 BONUS: Create auto position for this Zerodha position if it doesn't exist
                if not auto_pos_found and int(pos['quantity']) > 0:
                    print(f"🆕 LIVE: Creating auto position for existing Zerodha position {strike} {option_type}")
                    try:
                        # 🔥 FIX: Get actual expiry from instruments_df instead of parsing from tradingsymbol
                        # Zerodha format: BANKNIFTY25NOV58800CE has NO day in symbol!
                        # We need to fetch the actual expiry date from instruments
                        
                        expiry_date = None
                        
                        # Try to get expiry from instruments_df
                        if instruments_df is not None:
                            matching_instrument = instruments_df[
                                (instruments_df['tradingsymbol'] == pos['tradingsymbol']) &
                                (instruments_df['exchange'] == 'NFO')
                            ]
                            
                            if not matching_instrument.empty:
                                # Get expiry date from instruments
                                instrument_expiry = matching_instrument.iloc[0]['expiry']
                                if pd.notna(instrument_expiry):
                                    # Convert to string format YYYY-MM-DD
                                    if hasattr(instrument_expiry, 'strftime'):
                                        expiry_date = instrument_expiry.strftime('%Y-%m-%d')
                                    else:
                                        expiry_date = str(instrument_expiry)[:10]  # Take YYYY-MM-DD part
                                    
                                    print(f"✅ EXPIRY FETCHED: {pos['tradingsymbol']} -> {expiry_date}")
                        
                        # Fallback: Extract symbol from tradingsymbol for manual parsing
                        if not expiry_date:
                            symbol_match = re.match(r'^([A-Z]+)', pos['tradingsymbol'])
                            base_symbol = symbol_match.group(1) if symbol_match else 'UNKNOWN'
                            expiry_date = ''  # Empty expiry if we can't determine it
                            print(f"⚠️ EXPIRY FETCH FAILED: Using empty expiry for {pos['tradingsymbol']}")
                        else:
                            # Extract base symbol
                            symbol_match = re.match(r'^([A-Z]+)', pos['tradingsymbol'])
                            base_symbol = symbol_match.group(1) if symbol_match else 'UNKNOWN'
                        
                        # Create auto position with correct expiry
                        auto_pos = create_auto_position(
                            strike=strike,
                            option_type=option_type,
                            buy_price=avg_price,
                            qty=int(pos['quantity']),
                            symbol=base_symbol,
                            expiry=expiry_date
                        )
                        print(f"✅ LIVE: Auto position created for {strike} {option_type} with SL ₹{stop_loss_val:.2f}")
                        print(f"   Symbol: {base_symbol}, Expiry: {expiry_date}, Strike: {strike}")
                    except Exception as e:
                        print(f"⚠️ LIVE: Could not create auto position: {e}")
            
            if not auto_pos_found:
                print(f"⚠️ LIVE: No auto position found for {strike} {option_type}, using default SL")
            
            # Calculate P&L with live price
            pnl = (live_price - float(pos['average_price'])) * int(pos['quantity'])
            
            position_data = {
                'tradingsymbol': pos['tradingsymbol'],
                'quantity': int(pos['quantity']),
                'average_price': float(pos['average_price']),
                'last_price': live_price,  # 🔥 Use live price instead of static Zerodha price
                'pnl': pnl,  # 🔥 Recalculated P&L with live price
                'realized_pnl': float(pos['realised']),
                'instrument_token': pos['instrument_token'],
                'exchange': pos['exchange'],
                'product': pos['product'],
                'strike': strike,
                'option_type': option_type,
                'stop_loss_price': stop_loss_val,  # 🔥 Show stop loss from auto position
                'status': status,
                'auto_buy_count': auto_buy_count
            }
            all_positions.append(position_data)
        
        print(f"[DEBUG] Returning {len(all_positions)} LIVE positions from Zerodha")
        print(f"[DEBUG] Total auto_positions: {len(app_state.get('auto_positions', []))}")
        
        # 🔥 FIX: Add ONLY auto positions that have qty > 0 AND are NOT in Zerodha positions yet
        # This prevents duplicates while showing positions immediately after buying
        for auto_pos in app_state.get('auto_positions', []):
            strike = auto_pos.get('strike')
            option_type = auto_pos.get('type', auto_pos.get('option_type'))
            qty = auto_pos.get('qty', auto_pos.get('quantity', 0))
            
            print(f"[DEBUG] Checking auto_pos: strike={strike}, type={option_type}, qty={qty}")
            
            # Skip if waiting for auto-buy (qty = 0)
            if qty <= 0 and not auto_pos.get('waiting_for_autobuy', False):
                print(f"[DEBUG] Skipping auto_pos {strike} {option_type} - qty={qty}, not waiting for autobuy")
                continue
            
            # Check if this position is already in all_positions (from Zerodha)
            already_in = False
            for pos in all_positions:
                if (str(pos.get('strike')) == str(auto_pos.get('strike')) and 
                    pos.get('option_type') == auto_pos.get('type', auto_pos.get('option_type')) and
                    int(pos.get('quantity', 0)) > 0):  # Only match if Zerodha has qty > 0
                    already_in = True
                    print(f"[DEBUG] Auto_pos {strike} {option_type} already in Zerodha positions - SKIPPING to avoid duplicate")
                    break
            
            if not already_in:
                print(f"[DEBUG] Auto_pos {strike} {option_type} NOT in Zerodha - adding to display")
                # Get live price from option chain data
                strike = auto_pos.get('strike')
                option_type = auto_pos.get('type', auto_pos.get('option_type'))
                live_price = auto_pos.get('current_price', auto_pos.get('buy_price', 0))
                
                if current_option_data and strike and option_type:
                    for option_type_data in ['calls', 'puts', 'atm']:
                        if option_type_data in current_option_data:
                            options_list = current_option_data[option_type_data]
                            for option in options_list:
                                option_strike = option.get('strike')
                                opt_type = option.get('option_type', option.get('type'))
                                option_ltp = option.get('ltp')
                                if float(option_strike) == float(strike) and opt_type == option_type:
                                    live_price = float(option_ltp)
                                    print(f"✅ LIVE PRICE UPDATE (AUTO POS): {strike} {option_type} = ₹{live_price}")
                                    break
                
                # Check if this is a position with quantity or pending auto-buy
                qty = auto_pos.get('qty', auto_pos.get('quantity', 0))
                if qty > 0 or auto_pos.get('waiting_for_autobuy', False):
                    # Calculate P&L
                    buy_price = auto_pos.get('buy_price', 0)
                    pnl = (live_price - buy_price) * qty if qty > 0 else 0.0
                    
                    # Determine status
                    if auto_pos.get('waiting_for_autobuy', False):
                        status = 'Cooldown Pending' if (auto_pos.get('auto_buy_count', 0) >= 5 and app_state.get('cooldown_enabled', True)) else 'Pending Auto-Buy'
                        qty_display = 0  # Sold, waiting for auto-buy
                    else:
                        status = 'Active'
                        qty_display = qty
                    
                    # Get stop loss
                    sl_price = auto_pos.get('stop_loss_price', auto_pos.get('advanced_stop_loss', 0))
                    if not sl_price or sl_price == 0:
                        sl_price = buy_price - 10  # Default SL
                    
                    position_from_auto = {
                        'tradingsymbol': f"{option_type}{strike}",
                        'quantity': qty_display,
                        'average_price': buy_price,
                        'last_price': live_price,
                        'pnl': pnl,
                        'realized_pnl': auto_pos.get('realized_pnl', 0),
                        'instrument_token': '',
                        'exchange': 'NFO',
                        'product': 'MIS' if qty > 0 else 'PENDING',
                        'strike': strike,
                        'option_type': option_type,
                        'stop_loss_price': sl_price if qty > 0 else auto_pos.get('last_stop_loss_price', '-'),
                        'status': status,
                        'auto_buy_count': auto_pos.get('auto_buy_count', 0),
                        'waiting_for_autobuy': auto_pos.get('waiting_for_autobuy', False),
                        'id': auto_pos.get('id')
                    }
                    all_positions.append(position_from_auto)
                    print(f"✅ LIVE: Added auto position {strike} {option_type} to display (qty={qty_display}, SL=₹{sl_price:.2f})")
        
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
    """Get comprehensive trade history from Paper Trading or Live Trading (based on mode)"""
    if app_state['paper_trading_enabled']:
        # Return paper trading history - Show ALL trades, not just 20
        paper_trades = app_state['paper_trade_history']
        
        # Add mode information to each trade for frontend display
        formatted_trades = []
        for trade in paper_trades:
            formatted_trade = trade.copy()
            formatted_trade['mode'] = 'Paper Trading'
            formatted_trade['trading_mode'] = 'paper'
            # Ensure consistent field names
            if 'option_type' in formatted_trade:
                formatted_trade['type'] = formatted_trade['option_type']
            if 'timestamp' in formatted_trade:
                formatted_trade['time'] = formatted_trade['timestamp']
            # Add action field if missing
            if 'action' not in formatted_trade:
                formatted_trade['action'] = 'Sell'  # Most paper trades are sells from auto-trading
            formatted_trades.append(formatted_trade)
        
        return jsonify({
            'trades': formatted_trades,  # Show ALL paper trades
            'mode': 'paper',
            'total_trades': len(formatted_trades),
            'trading_mode': 'Paper Trading'
        })
    else:
        # Return live trading history - Show ALL trades
        live_trades = app_state['trade_history']
        
        # Add mode information to each trade for frontend display  
        formatted_trades = []
        for trade in live_trades:
            formatted_trade = trade.copy()
            formatted_trade['mode'] = 'Live Trading'
            formatted_trade['trading_mode'] = 'live'
            formatted_trades.append(formatted_trade)
        
        return jsonify({
            'trades': formatted_trades,  # Show ALL live trades
            'mode': 'live', 
            'total_trades': len(formatted_trades),
            'trading_mode': 'Live Trading'
        })

@app.route('/api/trade-history/all')  
def api_trade_history_all():
    """Get ALL trade history from both Paper and Live Trading combined"""
    all_trades = []
    
    # Add paper trading history
    for trade in app_state['paper_trade_history']:
        formatted_trade = trade.copy()
        formatted_trade['mode'] = 'Paper Trading'
        formatted_trade['trading_mode'] = 'paper'
        # Ensure consistent field names
        if 'option_type' in formatted_trade:
            formatted_trade['type'] = formatted_trade['option_type']
        if 'timestamp' in formatted_trade:
            formatted_trade['time'] = formatted_trade['timestamp']
        if 'action' not in formatted_trade:
            formatted_trade['action'] = 'Sell'
        all_trades.append(formatted_trade)
    
    # Add live trading history  
    for trade in app_state['trade_history']:
        formatted_trade = trade.copy()
        formatted_trade['mode'] = 'Live Trading'
        formatted_trade['trading_mode'] = 'live'
        all_trades.append(formatted_trade)
    
    # Sort by timestamp (most recent first)
    try:
        all_trades.sort(key=lambda x: x.get('timestamp', x.get('time', '')), reverse=True)
    except:
        pass  # Keep original order if sorting fails
    
    return jsonify({
        'trades': all_trades,
        'mode': 'combined',
        'total_trades': len(all_trades),
        'paper_trades': len(app_state['paper_trade_history']),
        'live_trades': len(app_state['trade_history']),
        'trading_mode': 'All History'
    })

@app.route('/api/clear-history', methods=['POST'])
def api_clear_history():
    """Clear trade history based on current trading mode"""
    data = request.get_json() or {}
    clear_mode = data.get('mode', 'current')  # 'current', 'paper', 'live', 'all'
    
    if clear_mode == 'all':
        # Clear both paper and live history
        app_state['trade_history'] = []
        app_state['paper_trade_history'] = []
        print("🗑️ Cleared ALL trade history (Paper + Live)")
        return jsonify({
            'success': True, 
            'message': 'All trade history cleared',
            'cleared': 'both'
        })
    elif clear_mode == 'paper':
        # Clear only paper trading history
        app_state['paper_trade_history'] = []
        print("🗑️ Cleared Paper Trading history")
        return jsonify({
            'success': True, 
            'message': 'Paper trading history cleared',
            'cleared': 'paper'
        })
    elif clear_mode == 'live':
        # Clear only live trading history
        app_state['trade_history'] = []
        print("🗑️ Cleared Live Trading history")
        return jsonify({
            'success': True, 
            'message': 'Live trading history cleared', 
            'cleared': 'live'
        })
    else:
        # Clear current mode history
        if app_state['paper_trading_enabled']:
            app_state['paper_trade_history'] = []
            cleared_mode = 'paper'
            message = 'Paper trading history cleared'
        else:
            app_state['trade_history'] = []
            cleared_mode = 'live'
            message = 'Live trading history cleared'
        
        print(f"🗑️ Cleared {cleared_mode} trade history")
        return jsonify({
            'success': True, 
            'message': message,
            'cleared': cleared_mode
        })

@app.route('/api/sell-all-positions', methods=['POST'])
def api_sell_all_positions():
    """Sell all positions through Paper Trading or Zerodha (based on mode)"""
    
    # Check if paper trading is enabled
    if app_state['paper_trading_enabled']:
        # Paper Trading Mode - Sell all paper positions
        if not app_state['paper_positions']:
            return jsonify({
                'success': False,
                'message': 'No paper trading positions to sell'
            })
        
        total_proceeds = 0
        total_pnl = 0
        positions_sold = 0
        
        # Sell all paper positions
        for position in app_state['paper_positions'][:]:  # Create a copy to iterate safely
            # Get current market price for the position
            sell_price = position.get('current_price', 0)
            if sell_price == 0:
                sell_price = position.get('buy_price', 0)  # Use buy_price instead of average_price
            
            buy_price = position.get('buy_price', 0)  # Use buy_price instead of average_price
            quantity = position.get('quantity', 0)
            
            print(f"📄 SELL ALL DEBUG: Position {position.get('strike')} {position.get('option_type')} - sell_price: {sell_price}, buy_price: {buy_price}, quantity: {quantity}")
            
            if quantity > 0:
                if sell_price == 0:
                    sell_price = buy_price  # Use buy price as fallback
                
                pnl = (sell_price - buy_price) * quantity
                sell_value = sell_price * quantity
                
                # Add to paper wallet
                app_state['paper_wallet_balance'] += sell_value
                total_proceeds += sell_value
                total_pnl += pnl
                positions_sold += 1
                
                print(f"📄 SELLING: {position.get('lots', 1)} lot(s) of {position.get('option_type')} {position.get('strike')} @ ₹{sell_price} = ₹{sell_value} (P&L: ₹{pnl})")
                
                # Add to paper trade history
                trade = {
                    'buy_price': buy_price,
                    'sell_price': sell_price,
                    'price': sell_price,  # Add this for frontend compatibility
                    'quantity': quantity,
                    'qty': quantity,  # Add this for frontend compatibility
                    'lots': position.get('lots', 1),
                    'pnl': pnl,
                    'pnl_percentage': (pnl / (buy_price * quantity)) * 100 if buy_price > 0 else 0,
                    'strike': position['strike'],
                    'option_type': position.get('option_type', 'CE'),
                    'type': position.get('option_type', 'CE'),  # Add this for frontend compatibility
                    'action': 'Sell',  # Add action field
                    'timestamp': get_ist_timestamp(),
                    'time': get_ist_time_formatted(),  # IST formatted time
                    'reason': 'Sell All'
                }
                app_state['paper_trade_history'].append(trade)
                
                # Add to paper orders
                order = {
                    'id': f"paper_sell_all_{len(app_state['paper_orders'])}_{int(time.time())}",
                    'type': 'SELL',
                    'action': 'Sell',  # Add action field for frontend
                    'strike': position['strike'],
                    'option_type': position.get('option_type', 'CE'),
                    'price': sell_price,
                    'sell_price': sell_price,  # Add for consistency
                    'quantity': quantity,
                    'qty': quantity,  # Add qty field for frontend
                    'lots': position.get('lots', 1),
                    'total_value': sell_value,
                    'pnl': pnl,
                    'timestamp': get_ist_timestamp(),
                    'time': get_ist_time_formatted(),  # IST formatted time
                    'status': 'COMPLETE',
                    'reason': 'Sell All'
                }
                app_state['paper_orders'].append(order)
        
        # Clear all paper positions
        app_state['paper_positions'].clear()
        
        return jsonify({
            'success': True,
            'message': f'📄 All {positions_sold} paper positions sold successfully!',
            'proceeds': total_proceeds,
            'total_pnl': total_pnl,
            'positions_sold': positions_sold,
            'wallet_balance': app_state['paper_wallet_balance'],
            'mode': 'paper'
        })
    
    # Live Trading Mode - Check Zerodha connection
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
            # 🛡️ ZERODHA: Cancel all protective SL orders first
            cancelled_sl_count = 0
            for auto_pos in app_state['auto_positions']:
                protective_sl_order_id = auto_pos.get('protective_sl_order_id')
                if protective_sl_order_id:
                    try:
                        def cancel_protective_sl():
                            app_state['kite'].cancel_order(
                                variety=app_state['kite'].VARIETY_REGULAR,
                                order_id=protective_sl_order_id
                            )
                            return True
                        
                        cancel_success, _, cancel_error = execute_with_session_retry(
                            cancel_protective_sl,
                            f"Cancel Protective SL {protective_sl_order_id}"
                        )
                        
                        if cancel_success:
                            cancelled_sl_count += 1
                            print(f"🗑️ CANCELLED PROTECTIVE SL: {protective_sl_order_id} (sell all)")
                        else:
                            print(f"⚠️ Could not cancel protective SL: {cancel_error}")
                    except Exception as e:
                        print(f"⚠️ Error canceling protective SL: {e}")
            
            app_state['auto_positions'] = []
            print(f"🗑️ CLEARED ALL AUTO POSITIONS: {auto_positions_count} positions removed, {cancelled_sl_count} protective SL orders cancelled (Sell All)")
        
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
    """Sell individual position through Paper Trading or Zerodha (based on mode) - SELLS ALL LOTS OF SAME STRIKE"""
    
    data = request.get_json()
    tradingsymbol = data.get('tradingsymbol')
    
    if not tradingsymbol:
        return jsonify({
            'success': False,
            'message': 'Trading symbol is required'
        })
    
    print(f"🐛 INDIVIDUAL SELL DEBUG: paper_trading_enabled = {app_state['paper_trading_enabled']}")
    print(f"🐛 INDIVIDUAL SELL DEBUG: tradingsymbol = {tradingsymbol}")
    
    # Check if paper trading is enabled
    if app_state['paper_trading_enabled']:
        print(f"📄 PAPER MODE: Selling ALL lots of individual position {tradingsymbol}")
        
        # 🚨 FIX: Find ALL positions with same strike and sell them together
        positions_found = []
        total_quantity = 0
        total_cost = 0
        
        for pos in app_state['paper_positions']:
            if pos['tradingsymbol'] == tradingsymbol:
                positions_found.append(pos)
                total_quantity += pos['quantity']
                total_cost += pos.get('total_cost', pos['quantity'] * pos['buy_price'])
        
        if not positions_found:
            return jsonify({
                'success': False,
                'message': f'No paper position found for {tradingsymbol}'
            })
        
        # Use the first position for reference data
        first_position = positions_found[0]
        current_price = float(data.get('current_price', first_position.get('ltp', first_position['buy_price'])))
        
        # Calculate P&L for ALL positions combined
        total_sell_value = total_quantity * current_price
        pnl = total_sell_value - total_cost
        
        # Update paper wallet balance
        app_state['paper_wallet_balance'] += total_sell_value
        
        # Remove ALL positions with same trading symbol
        app_state['paper_positions'] = [pos for pos in app_state['paper_positions'] 
                                       if pos['tradingsymbol'] != tradingsymbol]
        
        # Calculate average buy price for trade history
        avg_buy_price = total_cost / total_quantity if total_quantity > 0 else 0
        
        # Add to trade history
        app_state['trade_history'].append({
            'action': 'Paper Sell Individual (ALL LOTS)',
            'tradingsymbol': tradingsymbol,
            'qty': total_quantity,
            'buy_price': avg_buy_price,
            'sell_price': current_price,
            'pnl': pnl,
            'wallet_balance': app_state['paper_wallet_balance'],
            'time': dt.now().strftime('%Y-%m-%d %H:%M:%S'),
            'lots_count': len(positions_found)
        })
        
        pnl_text = f"Profit: ₹{pnl:.2f}" if pnl >= 0 else f"Loss: ₹{abs(pnl):.2f}"
        
        return jsonify({
            'success': True,
            'message': f'📄 ALL positions sold: {total_quantity} units ({len(positions_found)} lots) of {tradingsymbol} ({pnl_text})',
            'pnl': pnl,
            'wallet_balance': app_state['paper_wallet_balance'],
            'mode': 'paper',
            'lots_sold': len(positions_found),
            'total_quantity': total_quantity
        })
    
    print(f"🏦 LIVE MODE: Selling individual position via Zerodha")
    # Live Trading Mode - Check Zerodha connection
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

@app.route("/api/update-manual-stop-loss", methods=["POST"])
def update_manual_stop_loss():
    """Update stop loss manually for a position, ensuring both paper and auto lists are synced."""
    try:
        data = request.get_json()
        position_key = data.get("position_key")
        new_stop_loss = float(data.get("new_stop_loss", 0))

        if not position_key or new_stop_loss <= 0:
            return jsonify(
                {"success": False, "message": "Invalid position key or stop loss value"}
            ), 400

        position_updated = False
        target_position_details = {}

        def apply_update(pos):
            old_stop_loss = pos.get("stop_loss_price", 0)
            current_price = pos.get("current_price", 0)
            
            pos["stop_loss_price"] = new_stop_loss
            pos["manual_stop_loss_set"] = True
            pos["manual_stop_loss_time"] = get_ist_now()
            
            # 🚨 CRITICAL FIX: Only reset armed flag if current price is ABOVE new stop loss
            # If current price is already below SL, keep it UNARMED to prevent immediate trigger
            if current_price > new_stop_loss:
                # Price is above SL - ARM immediately (ready to trigger on drop)
                pos["manual_sl_armed"] = True
                print(f"✅ Manual SL ₹{new_stop_loss} ARMED (current price ₹{current_price} > SL)")
            else:
                # Price is at or below SL - keep UNARMED to prevent immediate sell
                pos["manual_sl_armed"] = False
                print(f"⏸️ Manual SL ₹{new_stop_loss} UNARMED (current price ₹{current_price} <= SL, waiting for recovery)")
            
            if "advanced_stop_loss" in pos:
                pos["advanced_stop_loss"] = new_stop_loss
            
            return {
                "strike": pos.get("strike"),
                "type": pos.get("type", pos.get("option_type")),
                "old_stop_loss": old_stop_loss,
            }

        for pos_list in [app_state["auto_positions"], app_state["paper_positions"]]:
            for pos in pos_list:
                match_found = False
                # 1. Primary Match: Check by unique ID (for paper trades)
                if pos.get("id") == position_key:
                    match_found = True
                # 2. Secondary Match: Check by full tradingsymbol (for live Zerodha trades)
                elif pos.get("tradingsymbol") == position_key:
                    match_found = True
                else:
                    # 3. Fallback Match: Parse the key (e.g., "CE56100") and match components
                    key_match = re.match(r"^(CE|PE)(\d+(\.\d+)?)$", position_key)
                    if key_match:
                        key_type = key_match.group(1)
                        key_strike = float(key_match.group(2))

                        pos_strike_val = pos.get("strike")
                        pos_type_val = pos.get("type") or pos.get("option_type")

                        if pos_strike_val is not None and pos_type_val:
                            try:
                                if (
                                    pos_type_val == key_type
                                    and float(pos_strike_val) == key_strike
                                ):
                                    match_found = True
                            except (ValueError, TypeError):
                                pass  # Ignore casting errors

                if match_found:
                    details = apply_update(pos)
                    if not target_position_details:
                        target_position_details = details
                    position_updated = True
                    # Do not break; ensure updates across both lists if needed

        if position_updated:
            strike = target_position_details.get("strike", "N/A")
            pos_type = target_position_details.get("type", "N/A")
            print(
                f"🔧 MANUAL STOP LOSS UPDATED: {strike} {pos_type} -> ₹{new_stop_loss:.2f}"
            )
            
            # 🛡️ ZERODHA PROTECTION: Place protective SL order for live trading
            zerodha_order_status = None
            if not app_state['paper_trading_enabled'] and app_state.get('kite'):
                # Find the position that was updated (need full position data for Zerodha order)
                updated_position = None
                for pos in app_state["auto_positions"]:
                    if (pos.get("strike") == strike and 
                        (pos.get("type") == pos_type or pos.get("option_type") == pos_type)):
                        updated_position = pos
                        break
                
                if updated_position:
                    try:
                        # 🚨 CRITICAL: Cancel existing protective SL order first
                        old_sl_order_id = updated_position.get('protective_sl_order_id')
                        if old_sl_order_id:
                            try:
                                def cancel_old_sl_order():
                                    app_state['kite'].cancel_order(
                                        variety=app_state['kite'].VARIETY_REGULAR,
                                        order_id=old_sl_order_id
                                    )
                                    return True
                                
                                cancel_success, _, cancel_error = execute_with_session_retry(
                                    cancel_old_sl_order,
                                    f"Cancel Old SL {old_sl_order_id}"
                                )
                                
                                if cancel_success:
                                    print(f"🗑️ CANCELLED OLD SL ORDER: {old_sl_order_id}")
                                else:
                                    print(f"⚠️ Could not cancel old SL order {old_sl_order_id}: {cancel_error}")
                            except Exception as e:
                                print(f"⚠️ Error canceling old SL order: {e}")
                        
                        # Place protective SL-M order on Zerodha
                        def place_protective_sl_order():
                            """Place protective stop-loss order on Zerodha"""
                            symbol = updated_position['symbol']
                            expiry = updated_position.get('expiry', '')
                            
                            # Handle expiry format
                            if isinstance(expiry, dict):
                                expiry = expiry.get('value', '') if expiry else ''
                            elif not isinstance(expiry, str):
                                expiry = str(expiry) if expiry else ''
                            
                            # Convert expiry from YYYY-MM-DD to YYMMDD for TrueData format
                            try:
                                if '-' in expiry:
                                    year, month, day = expiry.split('-')
                                    yy = year[-2:]
                                    expiry_td = f"{yy}{month}{day}"
                                else:
                                    expiry_td = expiry
                            except Exception as e:
                                print(f"[ERROR] Failed to parse expiry date {expiry}: {e}")
                                raise Exception(f"Expiry parse error: {e}")
                            
                            # Build TrueData symbol and convert to Zerodha format
                            td_symbol = f"{symbol}{expiry_td}{int(strike)}{pos_type}"
                            tradingsymbol = td_to_zerodha_symbol(td_symbol)
                            
                            if not tradingsymbol:
                                print(f"[ERROR] Failed to convert symbol: {td_symbol}")
                                raise Exception(f"Symbol conversion failed for {td_symbol}")
                            
                            print(f"[DEBUG] PROTECTIVE SL - Placing SL-M order for: {tradingsymbol} at trigger ₹{new_stop_loss}")
                            
                            # Place SL-M (Stop Loss Market) order for protection
                            order_id = app_state['kite'].place_order(
                                variety=app_state['kite'].VARIETY_REGULAR,
                                exchange=app_state['kite'].EXCHANGE_NFO,
                                tradingsymbol=tradingsymbol,
                                transaction_type=app_state['kite'].TRANSACTION_TYPE_SELL,
                                quantity=updated_position.get('qty', updated_position.get('quantity', 0)),
                                order_type=app_state['kite'].ORDER_TYPE_SLM,  # SL-M for market execution
                                trigger_price=new_stop_loss,
                                product=app_state['kite'].PRODUCT_MIS
                            )
                            
                            print(f"[SUCCESS] PROTECTIVE SL order placed: {order_id}")
                            return order_id
                        
                        # Execute with retry
                        success, order_id, error_msg = execute_with_session_retry(
                            place_protective_sl_order, 
                            f"Protective SL {strike} {pos_type}"
                        )
                        
                        if success:
                            zerodha_order_status = f"✅ Zerodha SL Order: {order_id}"
                            updated_position['protective_sl_order_id'] = order_id
                            print(f"🛡️ PROTECTIVE SL ORDER PLACED: Order ID {order_id} at trigger ₹{new_stop_loss}")
                        else:
                            zerodha_order_status = f"⚠️ Zerodha order failed: {error_msg}"
                            print(f"[ERROR] PROTECTIVE SL order failed: {error_msg}")
                    
                    except Exception as e:
                        zerodha_order_status = f"⚠️ Error: {str(e)}"
                        print(f"[ERROR] Exception placing protective SL: {e}")
            
            return jsonify(
                {
                    "success": True,
                    "message": f"✅ Stop loss for {strike} {pos_type} updated to ₹{new_stop_loss:.2f}",
                    "new_stop_loss": new_stop_loss,
                    "position_details": target_position_details,
                    "zerodha_order": zerodha_order_status
                }
            )
        else:
            print(
                f"❌ POSITION NOT FOUND for manual SL update with key: {position_key}"
            )
            return jsonify(
                {
                    "success": False,
                    "message": f"Position not found for key: {position_key}",
                }
            ), 404

    except Exception as e:
        print(f"❌ Error updating manual stop loss: {str(e)}")
        traceback.print_exc()
        return jsonify(
            {"success": False, "message": f"Error updating stop loss: {str(e)}"}
        ), 500

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
    
@app.route('/api/manual-trigger-auto-sell', methods=['POST'])
def api_manual_trigger_auto_sell():
    """Manually trigger auto sell for a specific position"""
    try:
        data = request.get_json()
        position_id = data.get('position_id')
        
        if not position_id:
            return jsonify({
                'success': False,
                'message': 'Position ID is required'
            })
        
        # Find the position
        position = None
        for pos in app_state['auto_positions']:
            if pos['id'] == position_id:
                position = pos
                break
        
        if not position:
            return jsonify({
                'success': False,
                'message': f'Position with ID {position_id} not found'
            })
        
        # Check if position is already waiting for auto buy or sold
        if position.get('waiting_for_autobuy', False):
            return jsonify({
                'success': False,
                'message': 'Position is already waiting for auto buy'
            })
        
        if position.get('sold', False) or position.get('manual_sold', False):
            return jsonify({
                'success': False,
                'message': 'Position is already sold'
            })
        
        # Execute manual auto sell
        success = execute_auto_sell(position, reason='Manual Trigger')
        
        if success:
            return jsonify({
                'success': True,
                'message': f'✅ Manual auto sell executed for {position["strike"]} {position["type"]} @ ₹{position["current_price"]}'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to execute manual auto sell'
            })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error executing manual auto sell: {str(e)}'
        })

@app.route('/api/manual-sell-auto-position', methods=['POST'])
def api_manual_sell_auto_position():
    """Manually sell auto position and completely remove it (no auto buy will trigger)"""
    try:
        data = request.get_json()
        position_id = data.get('position_id')
        strike = data.get('strike')
        option_type = data.get('option_type')
        symbol = data.get('symbol', 'NIFTY')
        
        if position_id:
            # Find position by ID
            position = None
            for pos in app_state['auto_positions']:
                if pos['id'] == position_id:
                    position = pos
                    strike = pos['strike']
                    option_type = pos['type']
                    symbol = pos['symbol']
                    break
            
            if not position:
                return jsonify({
                    'success': False,
                    'message': f'Position with ID {position_id} not found'
                })
        elif strike and option_type:
            # Find position by strike and type
            strike = float(strike)
        else:
            return jsonify({
                'success': False,
                'message': 'Either position_id or (strike + option_type) is required'
            })
        
        # Execute manual sell and complete removal
        removed_count = execute_manual_sell_auto_position(strike, option_type, symbol)
        
        if removed_count > 0:
            return jsonify({
                'success': True,
                'message': f'✅ Manually sold and completely removed {removed_count} auto position(s) for {strike} {option_type}. NO AUTO BUY will trigger.'
            })
        else:
            return jsonify({
                'success': False,
                'message': f'No auto position found for {strike} {option_type}'
            })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error in manual sell: {str(e)}'
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
        # 🚨 IMPROVED: Handle auto buy positions correctly in P&L calculation
        if pos.get('waiting_for_autobuy', False):
            # Position sold and waiting for auto buy - no current P&L
            current_pnl = 0
            display_qty = 0  # Don't show quantity for waiting positions
        else:
            # Active position - calculate normal P&L
            current_pnl = (pos['current_price'] - pos['buy_price']) * pos['qty']
            display_qty = pos['qty']
        
        positions_data.append({
            'id': pos['id'],
            'symbol': pos['symbol'],
            'strike': pos['strike'],
            'type': pos['type'],
            'qty': display_qty,  # Use display_qty instead of pos['qty']
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

# Profitable Stop Loss Re-entry Confirmation API Routes
@app.route('/api/reentry-confirmations', methods=['GET'])
def api_get_pending_confirmations():
    """Get all pending re-entry confirmations"""
    pending_confirmations = app_state.get('pending_reentry_confirmations', [])
    return jsonify({
        'success': True,
        'confirmations': pending_confirmations
    })

@app.route('/api/reentry-confirmation/respond', methods=['POST'])
def api_respond_reentry_confirmation():
    """Handle user response to re-entry confirmation"""
    data = request.get_json()
    confirmation_id = data.get('confirmation_id')
    user_decision = data.get('decision')  # 'accept' or 'reject'
    
    if not confirmation_id or user_decision not in ['accept', 'reject']:
        return jsonify({
            'success': False,
            'message': 'Invalid confirmation ID or decision'
        })
    
    # Find the confirmation
    pending_confirmations = app_state.get('pending_reentry_confirmations', [])
    confirmation = next((c for c in pending_confirmations if c['id'] == confirmation_id), None)
    
    if not confirmation:
        return jsonify({
            'success': False,
            'message': 'Confirmation not found'
        })
    
    # Find the corresponding position
    position = None
    for pos in app_state['paper_positions']:
        if pos.get('confirmation_id') == confirmation_id:
            position = pos
            break
    
    if not position:
        return jsonify({
            'success': False,
            'message': 'Position not found'
        })
    
    if user_decision == 'accept':
        # 👍 USER ACCEPTED: Execute re-entry buy at stop loss price
        reentry_price = confirmation['reentry_price']
        quantity = confirmation['quantity']
        lots = confirmation['lots']
        
        # Calculate total cost
        total_cost = reentry_price * quantity
        
        # Check trading mode and execute accordingly
        if app_state['paper_trading_enabled']:
            # 📄 PAPER TRADING RE-ENTRY
            if app_state['paper_wallet_balance'] < total_cost:
                return jsonify({
                    'success': False,
                    'message': f'Insufficient balance. Required: ₹{total_cost:.2f}'
                })
            
            # Deduct from paper wallet
            app_state['paper_wallet_balance'] -= total_cost
            
        else:
            # 🔴 LIVE TRADING RE-ENTRY: Place Zerodha buy order
            try:
                # Check if Zerodha is connected
                if not app_state.get('zerodha_connected', False) or not app_state.get('kite'):
                    return jsonify({
                        'success': False,
                        'message': 'Zerodha not connected. Cannot place live order.'
                    })
                
                # Build Zerodha symbol
                symbol = confirmation.get('symbol', 'NIFTY')
                strike = confirmation['strike']
                option_type = confirmation['option_type']
                expiry = position.get('expiry', '')
                
                # Convert to Zerodha tradingsymbol
                if isinstance(expiry, dict):
                    expiry = expiry.get('value', '') if expiry else ''
                elif not isinstance(expiry, str):
                    expiry = str(expiry) if expiry else ''
                
                # Build TrueData symbol and convert
                try:
                    if '-' in expiry:  # Format: "2025-08-07"
                        year, month, day = expiry.split('-')
                        yy = year[-2:]  # Take last 2 digits of year
                        expiry_td = f"{yy}{month}{day}"  # "250807"
                    else:
                        expiry_td = expiry
                    
                    td_symbol = f"{symbol}{expiry_td}{int(strike)}{option_type}"
                    tradingsymbol = td_to_zerodha_symbol(td_symbol)
                    
                    if not tradingsymbol:
                        # Fallback to CSV conversion
                        tradingsymbol, token, error = get_zerodha_symbol(td_symbol)
                        if not tradingsymbol:
                            raise Exception(f"Symbol conversion failed: {error}")
                    
                    print(f"💰 LIVE RE-ENTRY ORDER: {tradingsymbol} @ ₹{reentry_price}")
                    
                    # Place Zerodha buy order
                    order_id = app_state['kite'].place_order(
                        variety=app_state['kite'].VARIETY_REGULAR,
                        exchange=app_state['kite'].EXCHANGE_NFO,
                        tradingsymbol=tradingsymbol,
                        transaction_type=app_state['kite'].TRANSACTION_TYPE_BUY,
                        quantity=quantity,
                        order_type=app_state['kite'].ORDER_TYPE_MARKET,
                        product=app_state['kite'].PRODUCT_MIS
                    )
                    
                    print(f"✅ LIVE RE-ENTRY ORDER PLACED: {order_id}")
                    order_status = f"✅ Order ID: {order_id}"
                    
                except Exception as e:
                    print(f"❌ LIVE RE-ENTRY ORDER FAILED: {e}")
                    return jsonify({
                        'success': False,
                        'message': f'Failed to place live order: {str(e)}'
                    })
                
            except Exception as e:
                return jsonify({
                    'success': False,
                    'message': f'Live trading error: {str(e)}'
                })
            
        # Reset position for new entry (common for both paper and live)
        position['buy_price'] = reentry_price
        position['average_price'] = reentry_price
        position['current_price'] = reentry_price
        position['quantity'] = quantity
        position['qty'] = quantity
        position['total_cost'] = total_cost
        position['highest_price'] = reentry_price
        position['stop_loss_price'] = reentry_price - 10  # New stop loss 10 points below
        position['minimum_stop_loss'] = reentry_price - 10
        position['pnl'] = 0.0
        position['pnl_percentage'] = 0.0
        position['waiting_for_confirmation'] = False
        position['waiting_for_autobuy'] = False
        position['sell_triggered'] = False
        position['sell_in_progress'] = False
        position['entry_time'] = get_ist_now()
        position['last_update'] = get_ist_now()
        
        if app_state['paper_trading_enabled']:
            position['mode'] = 'Paper Running'
            
        # Add to appropriate orders and trade history
        if app_state['paper_trading_enabled']:
            # Paper trading orders and history
            order = {
                'id': f"paper_reentry_{len(app_state['paper_orders'])}_{int(time.time())}",
                'type': 'BUY',
                'action': 'Buy',
                'strike': position['strike'],
                'option_type': position.get('option_type', position.get('type')),
                'price': reentry_price,
                'quantity': quantity,
                'qty': quantity,
                'lots': lots,
                'total_value': total_cost,
                'pnl': 0,
                'timestamp': get_ist_timestamp(),
                'time': get_ist_time_formatted(),
                'status': 'COMPLETE',
                'reason': 'Profitable Re-entry (Paper)'
            }
            app_state['paper_orders'].append(order)
            
            # Add to paper trade history
            trade = {
                'buy_price': reentry_price,
                'price': reentry_price,
                'quantity': quantity,
                'qty': quantity,
                'lots': lots,
                'pnl': 0,
                'pnl_percentage': 0,
                'strike': position['strike'],
                'option_type': position.get('option_type', position.get('type')),
                'type': position.get('option_type', position.get('type')),
                'action': 'Buy',
                'timestamp': get_ist_timestamp(),
                'time': get_ist_time_formatted(),
                'reason': 'Profitable Re-entry (Paper)',
                'trading_mode': 'paper'
            }
            app_state['paper_trade_history'].append(trade)
            
        else:
            # Live trading history
            trade = {
                'action': f'Profitable Re-entry Buy',
                'type': position.get('option_type', position.get('type')),
                'strike': position['strike'],
                'qty': quantity,
                'price': reentry_price,
                'pnl': 0,
                'position_id': position.get('id', 'live_reentry'),
                'order_status': order_status,
                'time': get_ist_time_formatted(),
                'trading_mode': 'live'
            }
            app_state['trade_history'].append(trade)
            position['mode'] = 'Live Running'
        
        print(f"✅ USER ACCEPTED RE-ENTRY: {position['strike']} {position.get('option_type', position.get('type'))} @ ₹{reentry_price}")
        
        trading_mode = 'Paper' if app_state['paper_trading_enabled'] else 'Live'
        message = f'{trading_mode}: Re-entered {confirmation["option_type"]} {confirmation["strike"]} at ₹{reentry_price}'
    
    else:
        # 👎 USER REJECTED: Remove position from monitoring
        position['waiting_for_confirmation'] = False
        position['mode'] = 'User Rejected Re-entry'
        
        # Remove from paper positions
        if position in app_state['paper_positions']:
            app_state['paper_positions'].remove(position)
        
        print(f"❌ USER REJECTED RE-ENTRY: {position['strike']} {position.get('option_type', position.get('type'))} removed from monitoring")
        
        message = f'Rejected re-entry for {confirmation["option_type"]} {confirmation["strike"]}'
    
    # Remove confirmation from pending list
    app_state['pending_reentry_confirmations'].remove(confirmation)
    
    # Clear confirmation ID from position
    if 'confirmation_id' in position:
        del position['confirmation_id']
    
    return jsonify({
        'success': True,
        'message': message,
        'decision': user_decision
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

# Individual Position Cooldown Control API
@app.route('/api/position/toggle-individual-cooldown', methods=['POST'])
def api_toggle_individual_cooldown():
    """Toggle individual cooldown for a specific position"""
    try:
        data = request.get_json()
        position_id = data.get('position_id')
        strike = data.get('strike')
        option_type = data.get('option_type', data.get('type'))
        
        if not position_id and not (strike and option_type):
            return jsonify({
                'success': False,
                'error': 'Position ID or strike/option_type required'
            }), 400
        
        # Find position in both paper and auto positions
        target_position = None
        position_source = None
        
        # Search in paper positions first
        if app_state['paper_trading_enabled']:
            for pos in app_state['paper_positions']:
                if ((position_id and pos.get('id') == position_id) or 
                    (strike and option_type and 
                     str(pos.get('strike')) == str(strike) and 
                     pos.get('option_type', pos.get('type')) == option_type)):
                    target_position = pos
                    position_source = 'paper'
                    break
        
        # Search in auto positions
        if not target_position:
            for pos in app_state['auto_positions']:
                if ((position_id and pos.get('id') == position_id) or 
                    (strike and option_type and 
                     str(pos.get('strike')) == str(strike) and 
                     pos.get('type', pos.get('option_type')) == option_type)):
                    target_position = pos
                    position_source = 'auto'
                    break
        
        if not target_position:
            return jsonify({
                'success': False,
                'error': 'Position not found'
            }), 404
        
        # Toggle individual cooldown
        current_state = target_position.get('individual_cooldown_enabled', True)
        new_state = not current_state
        target_position['individual_cooldown_enabled'] = new_state
        
        # Also update the corresponding position in the other list (paper/auto sync)
        if position_source == 'paper':
            # Update corresponding auto position
            for auto_pos in app_state['auto_positions']:
                if (str(auto_pos.get('strike')) == str(target_position.get('strike')) and 
                    auto_pos.get('type', auto_pos.get('option_type')) == target_position.get('option_type', target_position.get('type'))):
                    auto_pos['individual_cooldown_enabled'] = new_state
                    break
        elif position_source == 'auto':
            # Update corresponding paper position
            for paper_pos in app_state['paper_positions']:
                if (str(paper_pos.get('strike')) == str(target_position.get('strike')) and 
                    paper_pos.get('option_type', paper_pos.get('type')) == target_position.get('type', target_position.get('option_type'))):
                    paper_pos['individual_cooldown_enabled'] = new_state
                    break
        
        # Send toast notification instead of console print
        status_text = 'ENABLED' if new_state else 'DISABLED'
        position_text = f"{target_position.get('strike')} {target_position.get('type', target_position.get('option_type'))}"
        
        return jsonify({
            'success': True,
            'message': f"✅ Individual cooldown {status_text.lower()} for position {position_text}",
            'individual_cooldown_enabled': new_state,
            'position_id': target_position.get('id'),
            'strike': target_position.get('strike'),
            'option_type': target_position.get('type', target_position.get('option_type'))
        })
        
    except Exception as e:
        print(f"❌ Error toggling individual cooldown: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    
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
        
        time.sleep(0.1)  # Update every 0.5 seconds for near real-time updates

@app.route('/api/auto-start-option-chain', methods=['POST'])
def api_auto_start_option_chain():
    """Auto-start option chain with default symbol and first available expiry"""
    try:
        symbol = 'NIFTY'  # Default symbol
        
        # Get first available expiry
        expiry_url = f"https://history.truedata.in/getSymbolExpiryList?symbol={symbol}&response=csv"
        headers = {
            "accept": "application/json",
            "authorization": "Bearer ump5ksCOXfao5QuWAJqFnFSCGBxVq4YjZrEGiWC2dXfjadn2U2lF4hCfys40LnT-rMI0E-IRD1pZO-hRTvHMFV6OBitR0kBdBKG3h5VEO8-wpLweQu5kWLYyxTidEkYXVxyxr3VjMftQ6LuH5aBP1iXT1ydMKm6rH4BqGzuMcgn3VsB2yKv-wKJIgFlvGa2FhI7lwbOKKvJnwyxtxXJPkpv5bWvfl1dF1fljV0UUwyyK2BsN4BJ-WA7WmAraOYhKZaHknTKwe-z1RrUkpYyZCQ"  # REPLACE THIS WITH YOUR REAL TOKEN
        }
        
        response = requests.get(expiry_url, headers=headers)
        if response.status_code == 200:
            expiry_list = response.text.strip().split('\n')[1:]
            expiry_list = [x.strip() for x in expiry_list if x.strip()]
            if expiry_list:
                expiry = expiry_list[0]  # Get first expiry
                
                # Ensure expiry is a string, not dict
                if isinstance(expiry, dict):
                    expiry = expiry.get('value', str(expiry))
                expiry = str(expiry)
                
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
    Convert TrueData symbol to Zerodha tradingsymbol using the official API method.
    This is a wrapper around get_zerodha_symbol() for backward compatibility.
    
    Supports two formats:
      - New format: SYMBOL + YYMMDD + STRIKE + CE/PE (e.g., NIFTY25102825800CE)
      - Legacy format: SYMBOL + YYMDD + STRIKE + CE/PE (e.g., NIFTY2573124500CE)
    
    Returns:
        Zerodha tradingsymbol string, or None if not found
    """
    try:
        if not isinstance(td_symbol, str):
            return None
        raw = td_symbol.strip().upper()
        print(f"[DEBUG] td_to_zerodha_symbol input: {raw}")
        
        # Use the new get_zerodha_symbol function
        tradingsymbol, instrument_token, error = get_zerodha_symbol(raw)
        
        if tradingsymbol:
            print(f"[SUCCESS] td_to_zerodha_symbol: {raw} -> {tradingsymbol}")
            return tradingsymbol
        else:
            print(f"[ERROR] td_to_zerodha_symbol failed for {raw}: {error}")
            return None
            
    except Exception as e:
        print(f"[ERROR] td_to_zerodha_symbol fatal for {td_symbol}: {e}")
        traceback.print_exc()
        return None

# Example usage in order placement:
# td_symbol = 'NIFTY2573124700CE'
# zerodha_symbol = td_to_zerodha_symbol(td_symbol)
# kite.place_order(tradingsymbol=zerodha_symbol, ...)

# Main entry point
if __name__ == '__main__':
    print("🚀 Starting Zerodha Live Options Trading App...")
    
    # Show initial trading mode
    if PAPER_TRADING_ENABLED:
        print("📄 STARTING IN PAPER TRADING MODE (Virtual ₹1,00,000 wallet)")
        print("💡 Use the toggle in the app to switch to live trading")
    else:
        print("⚡ STARTING IN LIVE TRADING MODE (Real money)")
        print("💡 Use the toggle in the app to switch to paper trading")
    
    # Initialize Zerodha connection
    initialize_kite()
    
    # Preload NFO instruments for faster order placement
    print("📦 Preloading NFO instruments from Zerodha...")
    try:
        fetch_nfo_instruments()
        print("✅ Instruments loaded successfully")
    except Exception as e:
        print(f"⚠️ Warning: Failed to preload instruments: {e}")
        print("   Instruments will be loaded on first order")
    
    # Start auto trading background thread
    auto_trading_thread = threading.Thread(target=auto_trading_background_task, daemon=True)
    auto_trading_thread.start()
    print("Auto trading background thread started")
    
    # Start Zerodha session monitor thread
    session_monitor_thread = threading.Thread(target=zerodha_session_monitor, daemon=True)
    session_monitor_thread.start()
    print("Zerodha session monitor started")
    
    # Run the Flask app without debug mode to prevent file monitoring issues
    socketio.run(app, debug=False, host='0.0.0.0', port=5000, use_reloader=False)
