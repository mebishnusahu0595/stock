import streamlit as st
import pandas as pd
from datetime import datetime as dt
from truedata import TD_live
import requests
import logging
import time
from streamlit_autorefresh import st_autorefresh
import os
import uuid

# --- Setup page config and title ---
st.set_page_config(page_title="Market Dashboard (Options & Stocks)", layout="wide")
st.title("📈 Market Dashboard (TrueData) | 💰 Simulated Trading & Real-Time Stocks")

# --- Simple Login System with Single Session Enforcement ---
SESSION_FILE = 'active_session.txt'
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = ''
if 'password' not in st.session_state:
    st.session_state.password = ''
if 'session_token' not in st.session_state:
    st.session_state.session_token = ''

VALID_USERNAME = 'admin'
VALID_PASSWORD = 'admin123'

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

active_session = get_active_session()

if not st.session_state.logged_in:
    st.subheader('🔒 Login Required')
    with st.form('login_form', clear_on_submit=False):
        username = st.text_input('Username')
        password = st.text_input('Password', type='password')
        submitted = st.form_submit_button('Login')
        if submitted:
            if username == VALID_USERNAME and password == VALID_PASSWORD:
                # Generate a new session token
                session_token = str(uuid.uuid4())
                set_active_session(username, session_token)
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.password = password
                st.session_state.session_token = session_token
                st.success('Login successful!')
                st.rerun()
            else:
                st.error('Invalid username or password.')
    st.stop()
else:
    # Check if this session is still the active one
    active_session = get_active_session()
    if not active_session or active_session['token'] != st.session_state.session_token:
        st.warning('You have been logged out because another device has logged in.')
        if st.button('🔄 Go to Login Page'):
            st.session_state.logged_in = False
            st.session_state.username = ''
            st.session_state.password = ''
            st.session_state.session_token = ''
            st.rerun()
        st.stop()

# --- Initialize TrueData client once, after login ---
if 'td_obj' not in st.session_state:
    st.session_state.td_obj = TD_live(
        'tdwsp690', 'bishnu@690',
        live_port=8084,
        log_level=logging.WARNING,
        compression=False
    )
td_obj = st.session_state.td_obj

# --- Simulated Portfolio Initialization ---
if 'balance' not in st.session_state:
    st.session_state.balance = 12876549.0
if 'positions' not in st.session_state:
    st.session_state.positions = []  # List of dicts
if 'trade_history' not in st.session_state:
    st.session_state.trade_history = []
if 'price_history' not in st.session_state:
    st.session_state.price_history = {}  # Track price history for trend analysis
if 'trend_analysis' not in st.session_state:
    st.session_state.trend_analysis = {}  # Store trend predictions

# --- Market Status Functions ---
def get_market_status():
    """Check if market is open or closed (Always uses IST timezone)"""
    from datetime import datetime, time
    import pytz
    
    # Always use IST timezone regardless of server location
    ist = pytz.timezone('Asia/Kolkata')
    now_ist = dt.now(ist)
    current_time = now_ist.time()
    current_day = now_ist.weekday()  # 0=Monday, 6=Sunday
    
    # Market timings (IST)
    market_open = time(9, 15)  # 9:15 AM
    market_close = time(15, 30)  # 3:30 PM
    
    # Check if it's weekend (Saturday=5, Sunday=6)
    if current_day >= 5:  # Saturday or Sunday
        return {
            "status": "CLOSED",
            "reason": "Weekend",
            "message": "Market is closed on weekends",
            "next_open": "Monday 9:15 AM IST",
            "current_ist": now_ist.strftime("%H:%M:%S IST")
        }
    
    # Check if it's outside trading hours on weekdays
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

# --- Lot sizes by symbol ---
LOT_SIZES = {
    "NIFTY": 75,
    "BANKNIFTY": 25,
    "SENSEX": 10,
    "SBIN": 3400,
    "RELIANCE": 500
}

# --- Robust Option Type Classification using symbol column ---
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

# --- Trend Analysis Functions ---
def analyze_price_trend(price_history, current_price, strike, option_type):
    """Analyze price trend and predict profit/loss probability"""
    if len(price_history) < 3:
        return {"trend": "INSUFFICIENT_DATA", "confidence": 0, "prediction": "WAIT"}
    
    prices = list(price_history)
    timestamps = list(range(len(prices)))
    
    # Calculate trend direction
    if len(prices) >= 5:
        recent_trend = sum(prices[-3:]) / 3 - sum(prices[-6:-3]) / 3 if len(prices) >= 6 else prices[-1] - prices[0]
        overall_trend = prices[-1] - prices[0]
        
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
        if option_type == "CE":  # Call options benefit from upward movement
            if trend in ["STRONG_UP", "UP"]:
                prediction = "PROFIT"
                confidence = min(confidence + 10, 95)
            elif trend in ["STRONG_DOWN", "DOWN"]:
                prediction = "LOSS"
                confidence = min(confidence + 5, 90)
            else:
                prediction = "NEUTRAL"
        else:  # Put options benefit from downward movement
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
            "recent_change": round(recent_trend, 2),
            "overall_change": round(overall_trend, 2)
        }
    
    return {"trend": "INSUFFICIENT_DATA", "confidence": 0, "prediction": "WAIT"}

def update_price_history(symbol, expiry, strike, option_type, current_price):
    """Update price history for trend analysis"""
    key = f"{symbol}_{expiry}_{strike}_{option_type}"
    current_time = dt.now()
    
    if key not in st.session_state.price_history:
        st.session_state.price_history[key] = []
    
    # Add current price with timestamp
    st.session_state.price_history[key].append({
        'price': current_price,
        'time': current_time
    })
    
    # Keep only last 30 minutes of data (assuming 3-second refresh)
    max_points = 600  # 30 minutes * 60 seconds / 3 seconds
    if len(st.session_state.price_history[key]) > max_points:
        st.session_state.price_history[key] = st.session_state.price_history[key][-max_points:]
    
    # Extract just prices for analysis
    prices = [p['price'] for p in st.session_state.price_history[key]]
    return analyze_price_trend(prices, current_price, strike, option_type)

# --- Sidebar for Trade History ---
with st.sidebar:
    st.markdown("### 📊 Trade History")
    
    # Clear history button
    if st.button("🗑️ Clear History", use_container_width=True):
        st.session_state.trade_history = []
        st.success("History cleared!")
    
    # Summary stats
    if st.session_state.trade_history:
        total_trades = len(st.session_state.trade_history)
        buy_trades = len([t for t in st.session_state.trade_history if t['action'] == 'Buy'])
        sell_trades = len([t for t in st.session_state.trade_history if t['action'] != 'Buy'])
        total_pnl = sum([t.get('pnl', 0) for t in st.session_state.trade_history if t['action'] != 'Buy'])
        
        st.markdown("#### 📈 Summary")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Trades", total_trades)
            st.metric("Buy Orders", buy_trades)
        with col2:
            st.metric("Sell Orders", sell_trades)
            st.metric("Total P&L", f"₹{total_pnl:.2f}", delta=f"{total_pnl:.2f}")
        
        st.markdown("---")
        
        # Filter options
        st.markdown("#### 🔍 Filters")
        show_filter = st.selectbox("Show:", ["All", "Buys Only", "Sells Only", "Profit Only", "Loss Only"])
        
        # Filtered history
        filtered_history = st.session_state.trade_history.copy()
        if show_filter == "Buys Only":
            filtered_history = [t for t in filtered_history if t['action'] == 'Buy']
        elif show_filter == "Sells Only":
            filtered_history = [t for t in filtered_history if t['action'] != 'Buy']
        elif show_filter == "Profit Only":
            filtered_history = [t for t in filtered_history if t.get('pnl', 0) > 0]
        elif show_filter == "Loss Only":
            filtered_history = [t for t in filtered_history if t.get('pnl', 0) < 0]
        
        # Display history (most recent first)
        st.markdown("#### 📋 Recent Trades")
        for i, trade in enumerate(reversed(filtered_history[-20:])):  # Show last 20 trades
            pnl = trade.get('pnl', 0)
            
            # Color coding based on action and P&L
            if trade['action'] == 'Buy':
                color = "🟢"
                pnl_text = ""
            elif pnl > 0:
                color = "💰"
                pnl_text = f" | P&L: +₹{pnl:.2f}"
            elif pnl < 0:
                color = "🔴"
                pnl_text = f" | P&L: -₹{abs(pnl):.2f}"
            else:
                color = "⚪"
                pnl_text = f" | P&L: ₹{pnl:.2f}"
            
            # Action type for sells
            action_detail = ""
            if trade['action'] == 'Stop Loss Sell':
                action_detail = " (🛑 Stop Loss)"
            elif trade['action'] == 'Manual Sell':
                action_detail = " (👤 Manual)"
            elif trade['action'] == 'Auto Sell':
                action_detail = " (🤖 Auto)"
            
            # Create expandable trade details
            with st.expander(f"{color} {trade['action']}{action_detail} - {trade['type']} {trade['strike']}{pnl_text}"):
                st.write(f"**Strike:** {trade['strike']}")
                st.write(f"**Type:** {trade['type']}")
                st.write(f"**Quantity:** {trade['qty']}")
                st.write(f"**Price:** ₹{trade['price']:.2f}")
                if pnl_text:
                    st.write(f"**P&L:** {pnl_text.split('P&L: ')[1]}")
                st.write(f"**Time:** {trade['time']}")
    else:
        st.info("No trades yet. Start trading to see history!")

# --- Real-time Profit/Loss Summary & Market Status ---
st.markdown("---")
pnl_col, market_col = st.columns(2)

with pnl_col:
    st.markdown("### 💰 Live P&L Summary")
    
    if st.session_state.positions:
        total_profit = 0
        total_loss = 0
        profit_positions = 0
        loss_positions = 0
        
        for pos in st.session_state.positions:
            if not pos.get('waiting_for_autobuy', False):  # Only count active positions
                current_pnl = (pos['current_price'] - pos['buy_price']) * pos['qty']
                if current_pnl > 0:
                    total_profit += current_pnl
                    profit_positions += 1
                elif current_pnl < 0:
                    total_loss += abs(current_pnl)  # Store as positive value
                    loss_positions += 1
        
        # Profit section
        if total_profit > 0:
            st.markdown(f"""
            <div style="
                background-color: #d4edda;
                border: 2px solid #28a745;
                border-radius: 8px;
                padding: 8px;
                margin: 3px 0;
            ">
                <h5 style="margin: 0; color: #155724;">🟢 Current Profit</h5>
                <h4 style="margin: 3px 0; color: #155724;">₹{total_profit:,.2f}</h4>
                <p style="margin: 0; color: #155724; font-size: 11px;">{profit_positions} positions in profit</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Loss section
        if total_loss > 0:
            st.markdown(f"""
            <div style="
                background-color: #f8d7da;
                border: 2px solid #dc3545;
                border-radius: 8px;
                padding: 8px;
                margin: 3px 0;
            ">
                <h5 style="margin: 0; color: #721c24;">🔴 Current Loss</h5>
                <h4 style="margin: 3px 0; color: #721c24;">₹{total_loss:,.2f}</h4>
                <p style="margin: 0; color: #721c24; font-size: 11px;">{loss_positions} positions in loss</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Overall summary
        net_pnl = total_profit - total_loss
        if net_pnl > 0:
            summary_color = "#28a745"
            summary_bg = "#d4edda"
            summary_icon = "📈"
            summary_text = "Net Profit"
        elif net_pnl < 0:
            summary_color = "#dc3545"
            summary_bg = "#f8d7da"
            summary_icon = "📉"
            summary_text = "Net Loss"
            net_pnl = abs(net_pnl)
        else:
            summary_color = "#6c757d"
            summary_bg = "#f8f9fa"
            summary_icon = "➡️"
            summary_text = "Break Even"
        
        st.markdown(f"""
        <div style="
            background-color: {summary_bg};
            border: 2px solid {summary_color};
            border-radius: 8px;
            padding: 6px;
            margin: 3px 0;
            text-align: center;
        ">
            <p style="margin: 0; color: {summary_color}; font-weight: bold; font-size: 13px;">
                {summary_icon} {summary_text}: ₹{net_pnl:,.2f}
            </p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("💭 No active positions to track P&L")

with market_col:
    st.markdown("### 📊 Market Status")
    
    # --- Market Status Card ---
    market_status = get_market_status()
    if market_status["status"] == "CLOSED":
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #ff6b6b 0%, #ee5a52 100%);
            color: white;
            padding: 12px;
            border-radius: 8px ;
            text-align: center;
            margin: 3px 0;
            border: 2px solid #d63031;
        ">
            <h4 style="margin: 0; font-size: 16px;">🚫 MARKET CLOSED</h4>
            <h5 style="margin: 3px 0; font-size: 14px;">{market_status["reason"]}</h5>
            <p style="margin: 0; opacity: 0.9; font-size: 12px;">{market_status["message"]}</p>
            <p style="margin: 3px 0; font-size: 11px; font-weight: bold;">Next Open: {market_status["next_open"]}</p>
            <p style="margin: 3px 0; font-size: 10px; opacity: 0.8;">Current IST: {market_status["current_ist"]}</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #00b894 0%, #00a085 100%);
            color: white;
            padding: 12px;
            border-radius: 8px;
            text-align: center;
            margin: 3px 0;
            border: 2px solid #00b894;
        ">
            <h4 style="margin: 0; font-size: 16px;">🟢 MARKET OPEN</h4>
            <h5 style="margin: 3px 0; font-size: 14px;">{market_status["reason"]}</h5>
            <p style="margin: 0; opacity: 0.9; font-size: 12px;">{market_status["message"]}</p>
            <p style="margin: 3px 0; font-size: 11px; font-weight: bold;">Closes at: {market_status["closes_at"]}</p>
            <p style="margin: 3px 0; font-size: 10px; opacity: 0.8;">Current IST: {market_status["current_ist"]}</p>
        </div>
        """, unsafe_allow_html=True)

# --- Wallet Information Section ---
st.markdown("---")
st.markdown("### 💰 Wallet & Portfolio Summary")

# Create compact wallet display
wallet_col1, wallet_col2, wallet_col3, wallet_col4, wallet_col5 = st.columns(5)

with wallet_col1:
    st.metric("💵 Balance", f"₹{st.session_state.balance:,.2f}")

with wallet_col2:
    total_invested = sum([pos['qty'] * pos['buy_price'] for pos in st.session_state.positions if not pos.get('waiting_for_autobuy', False)])
    st.metric("📈 Invested", f"₹{total_invested:,.2f}")

with wallet_col3:
    current_value = sum([pos['qty'] * pos['current_price'] for pos in st.session_state.positions if not pos.get('waiting_for_autobuy', False)])
    st.metric("💼 Current Value", f"₹{current_value:,.2f}")

with wallet_col4:
    total_pnl = current_value - total_invested
    delta_color = "normal" if total_pnl >= 0 else "inverse"
    st.metric("📊 Unrealized P&L", f"₹{total_pnl:,.2f}", delta=f"{total_pnl:,.2f}", delta_color=delta_color)

with wallet_col5:
    total_positions = len([pos for pos in st.session_state.positions if not pos.get('waiting_for_autobuy', False)])
    waiting_positions = len([pos for pos in st.session_state.positions if pos.get('waiting_for_autobuy', False)])
    st.metric("🎯 Positions", f"{total_positions} Active", delta=f"{waiting_positions} Waiting")

# Compact trade history summary
if st.session_state.trade_history:
    realized_pnl = sum([t.get('pnl', 0) for t in st.session_state.trade_history if t['action'] != 'Buy'])
    total_wallet_value = st.session_state.balance + current_value
    
    wallet_col6, wallet_col7, wallet_col8 = st.columns(3)
    with wallet_col6:
        st.metric("💎 Realized P&L", f"₹{realized_pnl:,.2f}")
    with wallet_col7:
        st.metric("🏦 Total Portfolio", f"₹{total_wallet_value:,.2f}")
    with wallet_col8:
        net_pnl = realized_pnl + total_pnl
        st.metric("🎯 Net P&L", f"₹{net_pnl:,.2f}", delta=f"{net_pnl:,.2f}")

# --- Tabs for Option Chain and Stock Dashboard ---
tab1, tab2 = st.tabs(["🔗 Option Chain", "📈 Stock Dashboard"])

with tab1:
    # --- Compact Symbol & Settings ---
    symbol_col1, symbol_col2, symbol_col3 = st.columns([2, 2, 1])
    
    with symbol_col1:
        symbols = list(LOT_SIZES.keys())
        selected_symbol = st.selectbox("📍 Symbol:", symbols, index=0)
        lot_size = LOT_SIZES[selected_symbol]
        st.caption(f"Lot Size: {lot_size}")
    
    # --- Fetch expiry list dynamically ---
    expiry_list = []
    expiry_error = False
    if selected_symbol:
        expiry_url = f"https://history.truedata.in/getSymbolExpiryList?symbol={selected_symbol}&response=csv"
        headers = {
            "accept": "application/json",
            "authorization": "Bearer _4ugzcfiCUaaTeobKl42aJ1CGNhx0Yz8ipBML3jheDmsXpt8f1I8GsmttvNBdvhWq9eCU-gxcg8rvZXaT70uBT5b4NvjKwDd5YslHryXsIxobOpQHnxRxyKUgGj2l2P_KHuC4lvokdRCQl9r3NptAxD2KBF-CjRGR1p3_9QmQcONoascxKNDodEtYIBXrrNfUnZbDU1UMdahN5CGRFqFxKRrq1hTgQBgl7mHkn3ZcmnYyY6Vsle5JhVul8q4bi-lwIgRyCHwRoCO0ZPb7pykMA"
        }
        try:
            response = requests.get(expiry_url, headers=headers)
            if response.status_code == 200:
                expiry_list = response.text.strip().split('\n')[1:]  # skip header row 
                expiry_list = [x.strip() for x in expiry_list if x.strip()]
            else:
                expiry_error = True
        except Exception:
            expiry_error = True

    if expiry_error:
        st.error("Failed to fetch expiry dates!")
        st.stop()

    with symbol_col2:
        # Convert strings to date objects for better UX
        parsed_expiries = []
        for exp_str in expiry_list:
            try:
                if '-' in exp_str:
                    parsed = dt.strptime(exp_str, '%Y-%m-%d').date()
                elif len(exp_str) == 8:
                    parsed = dt.strptime(exp_str, '%Y%m%d').date()
                else:
                    parsed = dt.strptime(exp_str, '%d-%b-%Y').date()
                parsed_expiries.append(parsed)
            except:
                continue
        
        if parsed_expiries:
            selected_expiry = st.selectbox("📅 Expiry:", parsed_expiries)
        else:
            st.error("No expiry dates available.")
            st.stop()
    
    with symbol_col3:
        refresh_interval = st.slider("🔄 Refresh (s):", 2, 10, 3, key="option_refresh")

    # --- Start option chain on symbol or expiry change ---
    if selected_symbol and selected_expiry:
        expiry_datetime = dt.combine(selected_expiry, dt.min.time())
        key = f"{selected_symbol}_{selected_expiry}"
        # Only start a new option chain if not already active
        if 'last_key' not in st.session_state or st.session_state.last_key != key:
            # Unsubscribe/stop previous option chain if exists
            if 'option_chain_obj' in st.session_state and hasattr(st.session_state['option_chain_obj'], 'stop'):
                try:
                    st.session_state['option_chain_obj'].stop()
                except Exception:
                    pass  # Ignore errors on stop
            try:
                st.info(f"Starting new option chain: {selected_symbol} | Expiry: {selected_expiry}")
                st.session_state.option_chain_obj = td_obj.start_option_chain(
                    selected_symbol, expiry=expiry_datetime, chain_length=10, bid_ask=True, greek=True
                )
                st.session_state.last_key = key
            except Exception as e:
                st.error(f"❌ Failed to start option chain: {str(e)}")
                st.stop()

    # --- Auto-refresh every N seconds ---
    st_autorefresh(interval=refresh_interval * 1000, key="datarefresh_option")

    # --- Get latest data from OptionChain object ---
    df_chain = pd.DataFrame()
    if 'option_chain_obj' in st.session_state:
        try:
            df_chain = st.session_state.option_chain_obj.get_option_chain()
            if not df_chain.empty:
                # --- Robust option type detection ---
                symbol_col = None
                for col in df_chain.columns:
                    if 'symbol' in col.strip().lower():
                        symbol_col = col
                        break
                if symbol_col is not None:
                    df_chain['option_type'] = df_chain[symbol_col].apply(extract_option_type)
                elif 'type' in [c.lower() for c in df_chain.columns]:
                    # Use 'type' column for CE/PE if present
                    type_col = [c for c in df_chain.columns if c.lower() == 'type'][0]
                    def map_type(val):
                        v = str(val).upper()
                        if 'CE' in v or 'CALL' in v:
                            return 'CE'
                        elif 'PE' in v or 'PUT' in v:
                            return 'PE'
                        else:
                            return 'UNK'
                    df_chain['option_type'] = df_chain[type_col].apply(map_type)
                else:
                    st.error(f"No symbol/type column found in option chain data! Columns available: {list(df_chain.columns)}")
                    st.dataframe(df_chain.head(10))
                    st.stop()
                df_chain['strike'] = pd.to_numeric(df_chain['strike'], errors='coerce')
                df_chain = df_chain.infer_objects(copy=False).fillna(0)
            else:
                df_chain = pd.DataFrame()
        except Exception as e:
            st.error(f"Error fetching data: {e}")

    # --- Show Live Option Chain (Compact) ---
    st.markdown("### 📊 Live Option Chain")
    if not df_chain.empty:
        # --- Enhanced Option Chain Layout (Compact) ---
        if 'underlying_value' in df_chain.columns:
            underlying = df_chain.iloc[0]['underlying_value']
        else:
            mid_index = len(df_chain) // 2
            underlying = df_chain.iloc[mid_index]['strike'] if not df_chain.empty else None

        # --- Compact Market Info ---
        market_col1, market_col2, market_col3, market_col4 = st.columns(4)
        with market_col1:
            st.metric("🎯 Underlying", f"₹{underlying:.2f}" if underlying else "N/A")
        with market_col2:
            total_rows = len(df_chain)
            st.metric("📋 Total Options", total_rows)
        with market_col3:
            ce_count = len(df_chain[df_chain['option_type'] == 'CE'])
            st.metric("📈 Calls (CE)", ce_count)
        with market_col4:
            pe_count = len(df_chain[df_chain['option_type'] == 'PE'])
            st.metric("📉 Puts (PE)", pe_count)

        # --- Compact Raw Data Table ---
        with st.expander("📋 Raw Option Chain Data", expanded=False):
            display_df = df_chain.copy()
            display_columns = ['strike', 'call_put', 'ltp', 'bid', 'ask', 'volume', 'oi']
            available_columns = [col for col in display_columns if col in display_df.columns]
            
            if available_columns:
                raw_display = display_df[available_columns].copy()
                column_rename = {
                    'strike': 'Strike', 'call_put': 'Type', 'ltp': 'LTP',
                    'bid': 'Bid', 'ask': 'Ask', 'volume': 'Vol', 'oi': 'OI'
                }
                raw_display.rename(columns=column_rename, inplace=True)
                if 'Strike' in raw_display.columns:
                    raw_display = raw_display.sort_values('Strike')
                st.dataframe(raw_display, use_container_width=True, height=200)
            else:
                st.dataframe(df_chain.head(5), use_container_width=True)
        
        # Find ATM strike (closest to underlying price)
        atm_strike = None
        if underlying is not None:
            df_chain['strike_diff'] = abs(df_chain['strike'] - underlying)
            atm_strike = df_chain.loc[df_chain['strike_diff'].idxmin(), 'strike']
        
        # Split into Calls and Puts based on ATM logic
        if atm_strike is not None:
            # Calls: ATM and below (ITM calls)
            call_strikes = df_chain[df_chain['strike'] <= atm_strike]['strike'].unique()
            calls = df_chain[
                (df_chain['option_type'] == 'CE') & 
                (df_chain['strike'].isin(call_strikes))
            ].sort_values('strike', ascending=False)  # Descending order for calls
            
            # Puts: ATM and above (ITM puts)  
            put_strikes = df_chain[df_chain['strike'] >= atm_strike]['strike'].unique()
            puts = df_chain[
                (df_chain['option_type'] == 'PE') & 
                (df_chain['strike'].isin(put_strikes))
            ].sort_values('strike')  # Ascending order for puts
            
            # ATM options (exact ATM strike)
            atm = df_chain[df_chain['strike'] == atm_strike]
        else:
            # Fallback to original logic if no underlying price
            calls = df_chain[df_chain['option_type'] == 'CE'].sort_values('strike')
            puts = df_chain[df_chain['option_type'] == 'PE'].sort_values('strike')
            atm = pd.DataFrame()

        # --- Compact Debug Information ---
        with st.expander("🔍 Debug & Analysis", expanded=False):
            debug_col1, debug_col2 = st.columns(2)
            
            with debug_col1:
                st.write(f"**Underlying:** ₹{underlying:.2f}" if underlying else "**Underlying:** N/A")
                st.write(f"**ATM Strike:** {atm_strike}")
                st.write(f"**Total Rows:** {len(df_chain)}")
                st.write(f"**Calls (≤ ATM):** {len(calls)}")
                st.write(f"**Puts (≥ ATM):** {len(puts)}")
                
                if 'call_put' in df_chain.columns:
                    st.write("**Raw Type Distribution:**")
                    st.write(df_chain['call_put'].value_counts().to_dict())
            
            with debug_col2:
                st.write("**Mapped Type Distribution:**")
                st.write(df_chain['option_type'].value_counts().to_dict())
                
                if atm_strike is not None:
                    call_strikes = calls['strike'].tolist() if not calls.empty else []
                    put_strikes = puts['strike'].tolist() if not puts.empty else []
                    st.write(f"**Call Strikes:** {call_strikes[:5]}..." if len(call_strikes) > 5 else f"**Call Strikes:** {call_strikes}")
                    st.write(f"**Put Strikes:** {put_strikes[:5]}..." if len(put_strikes) > 5 else f"**Put Strikes:** {put_strikes}")
            
            # Manual override for data issues
            st.markdown("**🛠️ Manual Override:**")
            override_col1, override_col2 = st.columns(2)
            with override_col1:
                if st.button("🔄 Swap Calls & Puts", use_container_width=True):
                    calls_temp = calls.copy()
                    calls = puts.copy()
                    puts = calls_temp.copy()
                    calls['option_type'] = 'CE'
                    puts['option_type'] = 'PE'
                    st.success("Swapped!")
            with override_col2:
                if st.button("🔄 Reset", use_container_width=True):
                    st.rerun()
        
        st.markdown("---")
        st.markdown("### 🔮 Smart Trading Indicator")
        
        # Update price history and get trend analysis for visible options
        trend_data = {}
        if not calls.empty or not puts.empty:
            # Analyze top 3 calls and puts for trend prediction
            for _, row in calls.head(3).iterrows():
                key = f"{selected_symbol}_{selected_expiry}_{row['strike']}_CE"
                analysis = update_price_history(selected_symbol, selected_expiry, row['strike'], 'CE', row['ltp'])
                trend_data[f"CE_{row['strike']}"] = analysis
            
            for _, row in puts.head(3).iterrows():
                key = f"{selected_symbol}_{selected_expiry}_{row['strike']}_PE"
                analysis = update_price_history(selected_symbol, selected_expiry, row['strike'], 'PE', row['ltp'])
                trend_data[f"PE_{row['strike']}"] = analysis
        
        # Display Smart Indicator Cards
        if trend_data:
            indicator_cols = st.columns(min(len(trend_data), 4))
            
            for idx, (option_key, analysis) in enumerate(list(trend_data.items())[:4]):
                if idx < len(indicator_cols):
                    with indicator_cols[idx]:
                        option_type, strike = option_key.split('_', 1)
                        
                        # Determine card color and icon based on prediction
                        if analysis['prediction'] == 'PROFIT':
                            card_color = "🟢"
                            bg_color = "#d4edda"
                            border_color = "#28a745"
                            pred_text = "📈 PROFIT LIKELY"
                        elif analysis['prediction'] == 'LOSS':
                            card_color = "🔴"
                            bg_color = "#f8d7da"
                            border_color = "#dc3545"
                            pred_text = "📉 LOSS LIKELY"
                        else:
                            card_color = "🟡"
                            bg_color = "#fff3cd"
                            border_color = "#ffc107"
                            pred_text = "⚪ NEUTRAL"
                        
                        # Trend direction icon
                        trend_icons = {
                            "STRONG_UP": "🚀",
                            "UP": "📈",
                            "SIDEWAYS": "➡️",
                            "DOWN": "📉",
                            "STRONG_DOWN": "🔻",
                            "INSUFFICIENT_DATA": "❓"
                        }
                        
                        trend_icon = trend_icons.get(analysis['trend'], "❓")
                        
                        # Create compact indicator card
                        st.markdown(f"""
                        <div style="
                            background-color: {bg_color};
                            border: 2px solid {border_color};
                            border-radius: 10px;
                            padding: 10px;
                            margin: 5px 0;
                            text-align: center;
                        ">
                            <h4 style=\"margin: 0; color: #111;\">{card_color} {strike} {option_type}</h4>
                            <p style=\"margin: 5px 0; font-weight: bold; color: #111;\">{pred_text}</p>
                            <p style=\"margin: 5px 0; font-size: 12px; color: #111;\">
                                {trend_icon} {analysis.get('trend', 'N/A').replace('_', ' ').title()}<br>
                                🎯 Confidence: {analysis.get('confidence', 'N/A')}%<br>
                                📊 Change: ₹{analysis.get('recent_change', 'N/A')}
                            </p>
                        </div>
                        """, unsafe_allow_html=True)
        
        # Overall Market Sentiment
        if trend_data:
            profit_predictions = sum(1 for analysis in trend_data.values() if analysis['prediction'] == 'PROFIT')
            loss_predictions = sum(1 for analysis in trend_data.values() if analysis['prediction'] == 'LOSS')
            total_predictions = len(trend_data)
            
            if profit_predictions > loss_predictions:
                overall_sentiment = "🟢 BULLISH"
                sentiment_desc = f"{profit_predictions}/{total_predictions} options showing profit signals"
            elif loss_predictions > profit_predictions:
                overall_sentiment = "🔴 BEARISH"
                sentiment_desc = f"{loss_predictions}/{total_predictions} options showing loss signals"
            else:
                overall_sentiment = "🟡 NEUTRAL"
                sentiment_desc = "Mixed signals in the market"
            
            st.markdown(f"""
            <div style="
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 15px;
                border-radius: 10px;
                text-align: center;
                margin: 10px 0;
            ">
                <h3 style="margin: 0;">📊 Market Sentiment</h3>
                <h2 style="margin: 5px 0;">{overall_sentiment}</h2>
                <p style="margin: 0; opacity: 0.9;">{sentiment_desc}</p>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("### 🛒 Trading Interface")
        col_call, col_atm, col_put = st.columns([3, 2, 3])

        # --- Compact Calls ---
        with col_call:
            st.markdown("#### 📈 Calls (CE)")
            st.caption(f"≤ {atm_strike} (ATM & Below)" if atm_strike else "All Calls")
            
            for _, row in calls.head(5).iterrows():  # Limit to 5 for compactness
                strike = row['strike']
                option_type = row['option_type']
                unique_key = f"{selected_symbol}_{selected_expiry}_{strike}_{option_type}"
                
                # Status indicator
                if atm_strike is not None:
                    if row['strike'] < atm_strike:
                        status = "🟢"
                    elif row['strike'] == atm_strike:
                        status = "🟡"
                    else:
                        status = "🔴"
                else:
                    status = "⚪"
                
                st.write(f"**{strike}** {status} ₹{row['ltp']:.1f}")
                
                # Create a form for each option to fix the submit button issue
                with st.form(key=f"form_ce_{unique_key}"):
                    c1, c2, c3 = st.columns([1, 1, 1])
                    
                    with c1:
                        qty_lots = st.number_input("Lots", min_value=1, max_value=10, value=1, label_visibility="collapsed")
                        total_qty = lot_size * qty_lots
                        st.caption(f"{total_qty} qty")
                    
                    with c2:
                        buy_submitted = st.form_submit_button("🟢 Buy", use_container_width=True)
                        if buy_submitted:
                            total_qty = lot_size * qty_lots
                            cost = total_qty * row['ltp']
                            if cost <= st.session_state.balance:
                                st.session_state.balance -= cost
                                st.session_state.positions.append({
                                    'strike': row['strike'], 'type': 'CE', 'qty': total_qty,
                                    'buy_price': row['ltp'], 'current_price': row['ltp'],
                                    'stop_loss_price': max(row['ltp'] - 10, 0), 'highest_price': row['ltp'],
                                    'first_buy_price': row['ltp']  # Store original buy price
                                })
                                st.success(f"✅ {total_qty} CE @ ₹{row['ltp']:.2f}")
                                st.session_state.trade_history.append({
                                    'action': 'Buy', 'type': 'CE', 'strike': row['strike'],
                                    'qty': total_qty, 'price': row['ltp'], 'pnl': 0,
                                    'time': dt.now().strftime('%Y-%m-%d %H:%M:%S')
                                })
                            else:
                                st.error("💸 Low balance!")
                    
                    with c3:
                        sell_submitted = st.form_submit_button("🔴 Sell", use_container_width=True)
                        if sell_submitted:
                            found = False
                            for idx, pos in enumerate(st.session_state.positions):
                                if pos['strike'] == row['strike'] and pos['type'] == 'CE':
                                    proceeds = pos['qty'] * row['ltp']
                                    st.session_state.balance += proceeds
                                    pnl = (row['ltp'] - pos['buy_price']) * pos['qty']
                                    st.session_state.trade_history.append({
                                        'action': 'Manual Sell', 'type': 'CE', 'strike': row['strike'],
                                        'qty': pos['qty'], 'price': row['ltp'], 'pnl': pnl,
                                        'time': dt.now().strftime('%Y-%m-%d %H:%M:%S')
                                    })
                                    st.session_state.positions.pop(idx)
                                    st.success(f"✅ Sold @ ₹{row['ltp']:.2f}")
                                    found = True
                                    break
                            if not found:
                                st.warning("❌ No position")

        # --- Compact ATM ---
        with col_atm:
            st.markdown("#### 🎯 ATM")
            st.caption(f"Strike: {atm_strike}" if atm_strike else "N/A")
            
            for i, row in atm.iterrows():
                option_label = "CE" if row['option_type'] == 'CE' else "PE"
                st.metric(
                    label=f"{atm_strike} {option_label}",
                    value=f"₹{row['ltp']:.2f}",
                    delta=None
                )
                
                # Additional compact metrics
                col_a, col_b = st.columns(2)
                with col_a:
                    if row.get('bid', 0) > 0:
                        st.caption(f"Bid: ₹{row['bid']:.1f}")
                with col_b:
                    if row.get('ask', 0) > 0:
                        st.caption(f"Ask: ₹{row['ask']:.1f}")
                
                if row.get('volume', 0) > 0:
                    st.caption(f"Vol: {row['volume']:,}")
                if row.get('oi', 0) > 0:
                    st.caption(f"OI: {row['oi']:,}")

        # --- Compact Puts ---
        with col_put:
            st.markdown("#### 📉 Puts (PE)")
            st.caption(f"≥ {atm_strike} (ATM & Above)" if atm_strike else "All Puts")
            
            for _, row in puts.head(5).iterrows():  # Limit to 5 for compactness
                strike = row['strike']
                option_type = row['option_type']
                unique_key = f"{selected_symbol}_{selected_expiry}_{strike}_{option_type}"
                
                # Status indicator for puts
                if atm_strike is not None:
                    if row['strike'] > atm_strike:
                        status = "🟢"
                    elif row['strike'] == atm_strike:
                        status = "🟡"
                    else:
                        status = "🔴"
                else:
                    status = "⚪"
                
                st.write(f"**{strike}** {status} ₹{row['ltp']:.1f}")
                
                # Create a form for each option to fix the submit button issue
                with st.form(key=f"form_pe_{unique_key}"):
                    c1, c2, c3 = st.columns([1, 1, 1])
                    
                    with c1:
                        qty_lots = st.number_input("Lots", min_value=1, max_value=10, value=1, label_visibility="collapsed")
                        total_qty = lot_size * qty_lots
                        st.caption(f"{total_qty} qty")
                    
                    with c2:
                        buy_submitted = st.form_submit_button("🟢 Buy", use_container_width=True)
                        if buy_submitted:
                            total_qty = lot_size * qty_lots
                            cost = total_qty * row['ltp']
                            if cost <= st.session_state.balance:
                                st.session_state.balance -= cost
                                st.session_state.positions.append({
                                    'strike': row['strike'], 'type': 'PE', 'qty': total_qty,
                                    'buy_price': row['ltp'], 'current_price': row['ltp'],
                                    'stop_loss_price': max(row['ltp'] - 10, 0), 'highest_price': row['ltp'],
                                    'first_buy_price': row['ltp']  # Store original buy price
                                })
                                st.success(f"✅ {total_qty} PE @ ₹{row['ltp']:.2f}")
                                st.session_state.trade_history.append({
                                    'action': 'Buy', 'type': 'PE', 'strike': row['strike'],
                                    'qty': total_qty, 'price': row['ltp'], 'pnl': 0,
                                    'time': dt.now().strftime('%Y-%m-%d %H:%M:%S')
                                })
                            else:
                                st.error("💸 Low balance!")
                    
                    with c3:
                        sell_submitted = st.form_submit_button("🔴 Sell", use_container_width=True)
                        if sell_submitted:
                            found = False
                            for idx, pos in enumerate(st.session_state.positions):
                                if pos['strike'] == row['strike'] and pos['type'] == 'PE':
                                    proceeds = pos['qty'] * row['ltp']
                                    st.session_state.balance += proceeds
                                    pnl = (row['ltp'] - pos['buy_price']) * pos['qty']
                                    st.session_state.trade_history.append({
                                        'action': 'Manual Sell', 'type': 'PE', 'strike': row['strike'],
                                        'qty': pos['qty'], 'price': row['ltp'], 'pnl': pnl,
                                        'time': dt.now().strftime('%Y-%m-%d %H:%M:%S')
                                    })
                                    st.session_state.positions.pop(idx)
                                    st.success(f"✅ Sold @ ₹{row['ltp']:.2f}")
                                    found = True
                                    break
                            if not found:
                                st.warning("❌ No position")

        # --- Compact Open Positions Table ---
        st.markdown('---')
        st.markdown('### 💼 Open Positions')
        
        pos_df = pd.DataFrame(st.session_state.positions)
        if not pos_df.empty:
            # Always recalculate P&L columns
            pos_df['P&L'] = (pos_df['current_price'] - pos_df['buy_price']) * pos_df['qty']
            pos_df['P&L %'] = ((pos_df['current_price'] - pos_df['buy_price']) / pos_df['buy_price']) * 100
            pos_df['P&L %'] = pos_df['P&L %'].round(2)

            # Compact control buttons
            btn_col1, btn_col2, btn_col3 = st.columns(3)
            with btn_col1:
                if st.button('🛑 Sell All', use_container_width=True):
                    total_proceeds = sum([pos['qty'] * pos['current_price'] for pos in st.session_state.positions])
                    st.session_state.balance += total_proceeds
                    st.session_state.positions.clear()
                    st.success(f"All sold! +₹{total_proceeds:,.2f}")

            with btn_col2:
                if st.button('🔄 Reset Stop Loss', use_container_width=True):
                    for pos in st.session_state.positions:
                        pos['stop_loss_price'] = max(pos['current_price'] - 10, 0)
                        pos['highest_price'] = pos['current_price']
                    st.success("Stop losses reset!")

            with btn_col3:
                show_mode = st.selectbox("Show:", ["All", "Running", "Waiting"], key="pos_filter", label_visibility="collapsed")

            # Compact table headers
            header_cols = st.columns([1.5,1,1,1.5,1.5,1.5,1.5,1.5,1,1.5,1])
            headers = ['Strike', 'Type', 'Qty', 'First Buy ₹', 'Buy ₹', 'Current ₹', 'Stop ₹', 'P&L ₹', 'P&L%', 'Mode', 'Sell']
            for col, name in zip(header_cols, headers):
                col.markdown(f"<b><small>{name}</small></b>", unsafe_allow_html=True)

            # --- Update current_price, highest_price, stop_loss_price, and repeat count for all open positions ---
            if not st.session_state.positions == []:
                if 'price_repeats' not in st.session_state:
                    st.session_state.price_repeats = {}
                
                positions_to_remove = []  # Track positions that should be removed
                for idx, pos in enumerate(st.session_state.positions):
                    match = df_chain[
                        (df_chain['strike'] == pos['strike']) &
                        (df_chain['option_type'] == pos['type'])
                    ]
                    if not match.empty:
                        old_price = pos['current_price']
                        pos['current_price'] = match.iloc[0]['ltp']
                        # Check for stop loss hit
                        if pos['current_price'] <= pos['stop_loss_price'] and pos['stop_loss_price'] > 0:
                            if not pos.get('waiting_for_autobuy', False):
                                # Mark as auto-sold, but keep in open positions with waiting flag
                                pnl = (pos['current_price'] - pos['buy_price']) * pos['qty']
                                st.session_state.balance += pos['qty'] * pos['current_price']
                                st.session_state.trade_history.append({
                                    'action': 'Stop Loss Sell',
                                    'type': pos['type'],
                                    'strike': pos['strike'],
                                    'qty': pos['qty'],
                                    'price': pos['current_price'],
                                    'pnl': pnl,
                                    'time': dt.now().strftime('%Y-%m-%d %H:%M:%S')
                                })
                                st.warning(f"🛑 Stop Loss Hit! Sold {pos['qty']} {pos['type']} {pos['strike']} at ₹{pos['current_price']:.2f} (P&L: ₹{pnl:.2f})")
                                pos['mode'] = 'Auto-Sell (Waiting for Auto-Buy)'
                                pos['waiting_for_autobuy'] = True
                                pos['sell_price'] = pos['current_price']
                                pos['last_stop_loss'] = pos['stop_loss_price']  # Store last stop loss
                            else:
                                # Already waiting for auto-buy, do nothing
                                pass
                            continue
                        # If waiting for auto-buy and price touches stop loss again, do auto-buy
                        if pos.get('waiting_for_autobuy', False):
                            cost = pos['qty'] * pos['current_price']
                            if st.session_state.balance >= cost:
                                st.session_state.balance -= cost
                                # Keep first_buy_price unchanged for tracking original purchase
                                if 'first_buy_price' not in pos:
                                    pos['first_buy_price'] = pos['buy_price']  # Backup if missing
                                pos['buy_price'] = pos['current_price']  # Update to auto-buy price
                                pos['current_price'] = pos['current_price']
                                # Auto-buy stop loss = auto-buy price (no minus 10)
                                pos['stop_loss_price'] = pos['current_price']  # Stop loss AT auto-buy price
                                pos['highest_price'] = pos['current_price']
                                pos['auto_bought'] = True
                                pos['mode'] = 'Running'
                                pos['waiting_for_autobuy'] = False
                                st.success(f"Auto-Buy: Bought {pos['qty']} {pos['type']} {pos['strike']} at ₹{pos['current_price']:.2f} (Stop Loss: ₹{pos['stop_loss_price']:.2f})")
                                st.session_state.trade_history.append({
                                    'action': 'Auto Buy',
                                    'type': pos['type'],
                                    'strike': pos['strike'],
                                    'qty': pos['qty'],
                                    'price': pos['current_price'],
                                    'pnl': 0,
                                    'time': dt.now().strftime('%Y-%m-%d %H:%M:%S')
                                })
                            else:
                                st.error(f"Auto-Buy failed: Not enough balance for {pos['qty']} {pos['type']} {pos['strike']} at ₹{pos['current_price']:.2f}")
                                positions_to_remove.append(idx)
                            continue
                        # Update highest price for trailing stop loss
                        if pos['current_price'] > pos['highest_price']:
                            pos['highest_price'] = pos['current_price']
                        
                        buy_price = pos['buy_price']
                        highest_price = pos['highest_price']
                        
                        # --- FIXED Trailing Stop Loss Logic ---
                        if pos.get('auto_bought'):
                            # For auto-bought positions, apply trailing stop loss from auto-buy price
                            auto_buy_price = pos['buy_price']  # This is the auto-buy price
                            highest_price_after_auto_buy = pos['highest_price']
                            
                            # Calculate profit from auto-buy price using HIGHEST price reached after auto-buy
                            profit_from_auto_buy = highest_price_after_auto_buy - auto_buy_price
                            
                            # Default stop loss for auto-buy is auto-buy price (no minus 10)
                            default_auto_buy_stop_loss = auto_buy_price
                            
                            if profit_from_auto_buy >= 10:
                                # For every ₹10 profit step from auto-buy price, move stop loss up by ₹10
                                profit_steps = int(profit_from_auto_buy // 10)  # How many ₹10 steps of profit
                                
                                # NEW LOGIC: Stop loss moves directly with profit steps from auto-buy price
                                # For 1st ₹10 profit step: stop loss = auto-buy + 10
                                # For 2nd ₹10 profit step: stop loss = auto-buy + 20
                                trailing_stop_loss_auto_buy = auto_buy_price + (profit_steps * 10)
                                
                                # Use trailing stop loss but ensure it's never below auto-buy price
                                pos['stop_loss_price'] = max(trailing_stop_loss_auto_buy, default_auto_buy_stop_loss, 0)
                            else:
                                # Less than ₹10 profit from auto-buy, keep stop loss at auto-buy price
                                pos['stop_loss_price'] = max(default_auto_buy_stop_loss, 0)
                        else:
                            # Initialize highest_price if not present
                            if 'highest_price' not in pos:
                                pos['highest_price'] = pos['buy_price']
                            
                            # Update highest price for trailing stop loss (only for running positions)
                            if pos['current_price'] > pos['highest_price']:
                                pos['highest_price'] = pos['current_price']
                            
                            buy_price = pos['buy_price']
                            highest_price = pos['highest_price']
                            
                            # Calculate profit from buy price using HIGHEST price reached
                            profit = highest_price - buy_price
                            
                            # Default stop loss is always buy_price - 10
                            default_stop_loss = buy_price - 10
                            
                            if profit >= 10:
                                # For every ₹10 profit step, move stop loss up by ₹10
                                profit_steps = int(profit // 10)  # How many ₹10 steps of profit
                                
                                # NEW LOGIC: Stop loss = buy_price + (profit_steps * 10) 
                                # Example: Buy ₹111.7, Current ₹133.1, Profit ₹21.4, Steps = 2
                                # Stop loss = 111.7 + (2 * 10) = ₹131.7
                                trailing_stop_loss = buy_price + (profit_steps * 10)
                                
                                # Ensure it's never below the default minimum (buy - 10)
                                pos['stop_loss_price'] = max(trailing_stop_loss, default_stop_loss, 0)
                            else:
                                # Less than ₹10 profit, use default stop loss (buy_price - 10)
                                pos['stop_loss_price'] = max(default_stop_loss, 0)
                        
                        # Debug for specific positions
                        if pos['strike'] in [25600, 25750]:
                            st.sidebar.write(f"**🔍 DEBUG {pos['strike']} {pos['type']}:**")
                            st.sidebar.write(f"Buy: ₹{buy_price:.1f}")
                            st.sidebar.write(f"Current: ₹{pos['current_price']:.1f}")
                            st.sidebar.write(f"Highest: ₹{highest_price:.1f}")
                            if pos.get('auto_bought'):
                                auto_buy_price = pos['buy_price']
                                profit_from_auto_buy = highest_price - auto_buy_price
                                st.sidebar.write(f"**AUTO-BOUGHT** at ₹{auto_buy_price:.1f}")
                                st.sidebar.write(f"Profit from Auto-Buy: ₹{profit_from_auto_buy:.1f}")
                                st.sidebar.write(f"Profit Steps: {int(profit_from_auto_buy // 10)}")
                                expected_stop = auto_buy_price + (int(profit_from_auto_buy // 10) * 10)
                                st.sidebar.write(f"Expected Stop: ₹{expected_stop:.1f}")
                            else:
                                profit = highest_price - buy_price
                                st.sidebar.write(f"Profit: ₹{profit:.1f}")
                                st.sidebar.write(f"Profit Steps: {int(profit // 10)}")
                                expected_stop = buy_price - 10 + (int(profit // 10) * 10)
                                st.sidebar.write(f"Expected Stop: ₹{expected_stop:.1f}")
                            st.sidebar.write(f"Actual Stop Loss: ₹{pos['stop_loss_price']:.1f}")
                            st.sidebar.write("---")
                        
                        # --- Ensure profit is added to wallet on stop loss sell ---
                        # This is already handled in the stop loss sell block above:
                        # st.session_state.balance += pos['qty'] * pos['current_price']
                        # st.session_state.trade_history.append({...})
                        # So, when price falls to stop loss (e.g., 150), profit (e.g., 50 per unit) is added to wallet.
                        
                        # --- Price Repeat Count Logic ---
                        key = f"{pos['strike']}_{pos['type']}_{pos['buy_price']}"
                        curr_price = pos['current_price']
                        
                        if key not in st.session_state.price_repeats:
                            st.session_state.price_repeats[key] = {'last': None, 'count': 0, 'seen': set()}
                        
                        if st.session_state.price_repeats[key]['last'] == curr_price:
                            # Same price as last update, no action needed
                            pass
                        else:
                            # New price detected
                            if curr_price in st.session_state.price_repeats[key]['seen']:
                                # This price has been seen before, increment repeat count
                                st.session_state.price_repeats[key]['count'] += 1
                            
                            # Add price to seen set and update last price
                            st.session_state.price_repeats[key]['seen'].add(curr_price)
                            st.session_state.price_repeats[key]['last'] = curr_price
                # Remove only those positions that failed auto-buy
                for idx in sorted(positions_to_remove, reverse=True):
                    st.session_state.positions.pop(idx)
                # Recreate pos_df after updating positions and recalculate all columns
                pos_df = pd.DataFrame(st.session_state.positions)
                if not pos_df.empty:
                    pos_df['P&L'] = (pos_df['current_price'] - pos_df['buy_price']) * pos_df['qty']
                    pos_df['P&L %'] = ((pos_df['current_price'] - pos_df['buy_price']) / pos_df['buy_price']) * 100
                    pos_df['P&L %'] = pos_df['P&L %'].round(2)
                    repeat_counts = []
                    for _, row in pos_df.iterrows():
                        key = f"{row['strike']}_{row['type']}_{row['buy_price']}"
                        repeat_counts.append(st.session_state.price_repeats.get(key, {}).get('count', 0))
                    pos_df['Price Repeats'] = repeat_counts

            # Filter positions based on selection
            filtered_positions = []
            for idx, pos in enumerate(st.session_state.positions):
                mode = pos.get('mode', 'Running')
                if show_mode == "All" or (show_mode == "Running" and mode == "Running") or (show_mode == "Waiting" and "Waiting" in mode):
                    filtered_positions.append((idx, pos))

            # Display filtered positions in compact format
            for original_idx, pos in filtered_positions:
                if original_idx < len(pos_df):
                    row = pos_df.iloc[original_idx]
                    mode = pos.get('mode', 'Running')
                    
                    # Get trend analysis for this position (commented out for space)
                    # pos_trend = update_price_history(selected_symbol, selected_expiry, pos['strike'], pos['type'], pos['current_price'])
                    
                    # Trend indicator (commented out for space)
                    # trend_icons = {
                    #     "STRONG_UP": "🚀", "UP": "📈", "SIDEWAYS": "➡️", 
                    #     "DOWN": "📉", "STRONG_DOWN": "🔻", "INSUFFICIENT_DATA": "❓"
                    # }
                    # trend_icon = trend_icons.get(pos_trend.get('trend', 'INSUFFICIENT_DATA'), "❓")
                    
                    # Color coding for P&L
                    pnl_color = "🟢" if row['P&L'] > 0 else "🔴" if row['P&L'] < 0 else "⚪"
                    mode_icon = "🏃" if mode == "Running" else "⏳"
                    
                    # Get first buy price, fallback to current buy price if missing
                    first_buy_price = pos.get('first_buy_price', pos['buy_price'])
                    
                    cols = st.columns([1.5,1,1,1.5,1.5,1.5,1.5,1.5,1,1.5,1])
                    cols[0].write(f"{row['strike']}")
                    cols[1].write(f"{row['type']}")
                    cols[2].write(f"{row['qty']}")
                    cols[3].write(f"₹{first_buy_price:.1f}")  # First Buy Price
                    cols[4].write(f"₹{row['buy_price']:.1f}")  # Current Buy Price (auto-buy price if auto-bought)
                    cols[5].write(f"₹{row['current_price']:.1f}")
                    cols[6].write(f"₹{pos['stop_loss_price']:.1f}")
                    cols[7].write(f"{pnl_color}₹{row['P&L']:.1f}")
                    cols[8].write(f"{row['P&L %']:.1f}%")
                    # cols[9].write(f"{trend_icon}")  # Commented out for space
                    cols[9].write(f"{mode_icon}{mode.split()[0] if ' ' in mode else mode}")
                    
                    with cols[10]:
                        # pos_trend = update_price_history(selected_symbol, selected_expiry, pos['strike'], pos['type'], pos['current_price'])
                        if st.button('🔴', key=f'sell_{original_idx}', help=f"Sell Position", use_container_width=True):
                            proceeds = row['qty'] * row['current_price']
                            st.session_state.balance += proceeds
                            pnl = row['P&L']
                            st.session_state.trade_history.append({
                                'action': 'Manual Sell', 'type': row['type'], 'strike': row['strike'],
                                'qty': row['qty'], 'price': row['current_price'], 'pnl': pnl,
                                'time': dt.now().strftime('%Y-%m-%d %H:%M:%S')
                            })
                            st.session_state.positions.pop(original_idx)
                            st.success(f"✅ Sold! +₹{proceeds:.2f}")
                            st.rerun()
        else:
            st.info("💭 No open positions. Start trading to see your portfolio here!")

        # --- Market Closed Card ---
        market_status = get_market_status()
        if market_status['status'] == "CLOSED":
            st.markdown("---")
            st.markdown(
                f"""
                <div style="
                    background-color: #f8d7da;
                    border: 2px solid #dc3545;
                    border-radius: 10px;
                    padding: 10px;
                    margin: 10px 0;
                    text-align: center;
                ">
                    <h4 style="margin: 0; color: #111;">
                        🔒 Market Closed
                    </h4>
                    <p style="margin: 5px 0; color: #111;">
                        {market_status['message']}<br>
                        <strong>Next Open:</strong> {market_status['next_open']}<br>
                        <small><strong>Current IST:</strong> {market_status['current_ist']}</small>
                    </p>
                </div>
                """, unsafe_allow_html=True)

with tab2:
    st.markdown("### 📈 Stock Dashboard")
    st.info("🚧 Stock dashboard coming soon!")
    
    # Compact placeholder
    feature_col1, feature_col2 = st.columns(2)
    with feature_col1:
        st.markdown("**📊 Planned Features:**")
        st.write("• Live stock prices")
        st.write("• Stock watchlist")
        st.write("• Technical indicators")
    with feature_col2:
        st.markdown("**🔧 Coming Soon:**")
        st.write("• Stock trading interface")
        st.write("• Portfolio analytics")
        st.write("• News integration")