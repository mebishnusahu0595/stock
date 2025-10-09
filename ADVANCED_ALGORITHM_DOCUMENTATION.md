# ADVANCED TRADING ALGORITHM DOCUMENTATION
## Complete Guide to Stop Loss, Auto Buy, and Advanced Features

---

## 📋 TABLE OF CONTENTS
1. [System Overview](#system-overview)
2. [Trading Modes](#trading-modes)
3. [Advanced Algorithm](#advanced-algorithm)
4. [Stop Loss System](#stop-loss-system)
5. [Auto Buy Mechanism](#auto-buy-mechanism)
6. [Phase-Based Trading](#phase-based-trading)
7. [Paper Trading](#paper-trading)
8. [Configuration](#configuration)
9. [API Integration](#api-integration)
10. [Troubleshooting](#troubleshooting)

---

## 🎯 SYSTEM OVERVIEW

The **Stock Dashboard Trading Application** is a comprehensive automated options trading system built with Flask and integrated with Zerodha Kite Connect API. It features advanced algorithms for stop loss management, automated buying/selling, and real-time position monitoring.

### Key Features:
- **Advanced 3-Phase Algorithm** for progressive stop loss management
- **Paper Trading Mode** for risk-free testing
- **Real-time Options Monitoring** via TrueData API
- **Automated Buy/Sell Execution** with multiple protection layers
- **Web-based Dashboard** with live updates via WebSocket
- **Comprehensive Logging** and trade history tracking

---

## 🔄 TRADING MODES

### 1. Paper Trading Mode (Default)
- **Purpose**: Risk-free testing and algorithm validation
- **Features**: Virtual portfolio with ₹1,00,000 starting balance
- **Data Source**: Real market data via TrueData API
- **Execution**: Simulated trades with real-time price updates
- **Enable**: `PAPER_TRADING_ENABLED = True`

### 2. Live Trading Mode
- **Purpose**: Real money trading with Zerodha account
- **Features**: Direct order placement via Kite Connect API
- **Data Source**: Live market data from Zerodha
- **Execution**: Actual buy/sell orders on exchange
- **Enable**: `PAPER_TRADING_ENABLED = False`

---

## 🧠 ADVANCED ALGORITHM

The advanced algorithm implements a **3-Phase Progressive Stop Loss System** that adapts behavior based on profit levels.

### Algorithm Selection:
```python
app_state['trading_algorithm'] = 'advanced'  # or 'simple'
```

### Core Principles:
1. **Phase-Based Behavior**: Different rules for different profit ranges
2. **Progressive Protection**: Increasing minimum protection as profits grow
3. **Step-wise Trailing**: ₹10 incremental stop loss adjustments
4. **Smart Auto Buy**: Phase-specific auto buy trigger logic

---

## 🛡️ STOP LOSS SYSTEM

### Simple Algorithm (Legacy)
- **Logic**: Fixed ₹10 steps from highest price
- **Calculation**: `stop_loss = highest_price - 10`
- **Use Case**: Basic trailing stop loss

### Advanced Algorithm (Recommended)
- **Logic**: Phase-based progressive trailing with step-wise calculation
- **Calculation**: `stop_loss = buy_price + (profit_steps × 10)`
- **Protection**: Progressive minimum ensures profits are locked

#### Advanced Stop Loss Formula:
```python
profit = highest_price - manual_buy_price
profit_steps = int(profit // 10)  # Complete ₹10 steps
stop_loss = manual_buy_price + (profit_steps × 10)
```

#### Example Calculation:
```
Manual Buy: ₹500
Current High: ₹535
Profit: ₹535 - ₹500 = ₹35
Steps: ₹35 ÷ 10 = 3 complete steps
Stop Loss: ₹500 + (3 × 10) = ₹530
```

---

## 🤖 AUTO BUY MECHANISM

The auto buy feature automatically repurchases positions after stop loss triggers, enabling continuous trading with minimal manual intervention.

### Trigger Logic (Phase-Dependent):

#### Phase 1 Auto Buy:
- **Trigger**: Price reaches original manual buy price
- **Logic**: `current_price >= manual_buy_price`
- **Purpose**: Only buy back when position recovers to original level

#### Phase 2/3 Auto Buy:
- **Trigger**: Price reaches stop loss sell price ± ₹1 buffer
- **Logic**: `abs(current_price - last_stop_loss_price) <= 1`
- **Purpose**: Quick re-entry at stop loss level

### Auto Buy Protection:
- **Cooldown System**: Prevents excessive trading
- **Count Limits**: Maximum 5 auto buys per position
- **Time Delays**: Minimum intervals between trades
- **Volatility Buffers**: Price stability checks

---

## 🎯 PHASE-BASED TRADING

The advanced algorithm operates in three distinct phases, each with specific behaviors:

### Phase 1: Initial Growth (Buy to Buy+20)
**Range**: Manual buy price to manual buy price + ₹20

**Characteristics**:
- **Stop Loss**: Step-wise trailing from buy price
- **Minimum Protection**: Never below `buy_price - 10`
- **Auto Buy Trigger**: Original manual buy price
- **Progressive Minimum**: Not activated

**Example**:
```
Manual Buy: ₹500
Price Range: ₹500 to ₹520
Stop Loss: Step-wise (₹490, ₹500, ₹510, etc.)
Auto Buy: When price returns to ₹500
```

### Phase 2: Progressive Protection (Buy+20 to Buy+30)
**Range**: Manual buy price + ₹20 to manual buy price + ₹30

**Characteristics**:
- **Stop Loss**: Step-wise trailing from buy price
- **Minimum Protection**: Progressive minimum activated at manual buy price
- **Auto Buy Trigger**: Stop loss sell price
- **Progressive Minimum**: Activated to protect capital

**Example**:
```
Manual Buy: ₹500
Price Range: ₹520 to ₹530
Stop Loss: Step-wise with ₹500 minimum
Auto Buy: When price returns to stop loss level
Progressive Min: ₹500 (locks in breakeven)
```

### Phase 3: Advanced Trailing (After Buy+30)
**Range**: Above manual buy price + ₹30

**Characteristics**:
- **Stop Loss**: Full step-wise trailing algorithm
- **Minimum Protection**: Progressive minimum maintained
- **Auto Buy Trigger**: Stop loss sell price
- **Progressive Minimum**: Ensures profit protection

**Example**:
```
Manual Buy: ₹500
Price Range: Above ₹530
Stop Loss: Full algorithm with profit protection
Auto Buy: At stop loss level
Progressive Min: Protects accumulated profits
```

---

## 📊 PAPER TRADING

Paper trading provides a risk-free environment to test strategies and algorithms before deploying real money.

### Features:
- **Virtual Portfolio**: ₹1,00,000 starting balance
- **Real Market Data**: Live prices via TrueData API
- **Simulated Execution**: All trading logic without real orders
- **Performance Tracking**: P&L calculations and trade history
- **Algorithm Testing**: Full advanced algorithm support

### Paper Trading Configuration:
```python
# Enable paper trading
app_state['paper_trading_enabled'] = True

# Starting balance
app_state['paper_wallet_balance'] = 1000000.0  # ₹10 lakhs

# Paper positions tracking
app_state['paper_positions'] = []
```

### Paper vs Live Trading Differences:
| Feature | Paper Trading | Live Trading |
|---------|---------------|--------------|
| Execution | Simulated | Real orders |
| Data Source | TrueData API | Zerodha API |
| Risk | Zero | Real money |
| Latency | Minimal | Network dependent |
| Testing | Ideal | Production |

---

## ⚙️ CONFIGURATION

### Trading Algorithm Selection:
```python
# Choose algorithm type
app_state['trading_algorithm'] = 'advanced'  # or 'simple'
```

### Auto Trading Configuration:
```python
app_state['auto_trading_config'] = {
    'enabled': True,
    'auto_buy_buffer': 1,  # ±₹1 buffer for auto buy
    'max_auto_buy_count': 5,  # Maximum auto buys per position
    'cooldown_enabled': True,  # Enable cooldown protection
    'time_delay': 2.0,  # Minimum seconds between trades
}
```

### Stop Loss Configuration:
```python
# Advanced algorithm settings
TRAILING_STEP = 10  # ₹10 step increments
MINIMUM_PROFIT_FOR_TRAILING = 10  # Start trailing after ₹10 profit
PROGRESSIVE_MINIMUM_ACTIVATION = 20  # Activate at +₹20 profit
```

### API Configuration:
```python
# Zerodha Kite Connect
KITE_CONFIG = {
    'api_key': 'your_api_key',
    'api_secret': 'your_api_secret',
    'access_token': 'your_access_token'
}

# TrueData API
TRUEDATA_CONFIG = {
    'username': 'your_username',
    'password': 'your_password'
}
```

---

## 🔌 API INTEGRATION

### Zerodha Kite Connect (Live Trading)
- **Purpose**: Live market data and order execution
- **Authentication**: API key, secret, and access token
- **Features**: Order placement, position tracking, market data
- **Rate Limits**: 3 requests per second, 1000 per day

### TrueData API (Paper Trading)
- **Purpose**: Real-time options chain data
- **Authentication**: Username and password
- **Features**: Live option prices, strike data, market updates
- **Refresh Rate**: Every 100ms for real-time updates

### WebSocket Integration:
- **Technology**: Flask-SocketIO
- **Purpose**: Real-time dashboard updates
- **Events**: Position updates, trade notifications, price changes
- **Client Updates**: Automatic refresh without page reload

---

## 🚨 TROUBLESHOOTING

### Common Issues and Solutions:

#### 1. Stop Loss Not Updating
**Symptoms**: Stop loss shows incorrect values
**Solution**: 
- Check algorithm selection (`simple` vs `advanced`)
- Verify highest price tracking
- Ensure phase detection is correct

#### 2. Rapid Fire Auto Buy/Sell
**Symptoms**: Multiple trades per second
**Solution**:
- Enable cooldown protection
- Increase time delays
- Check auto buy trigger logic
- Verify Phase 1 vs Phase 2 logic

#### 3. Auto Buy at Wrong Price
**Symptoms**: Auto buy triggers at incorrect price levels
**Solution**:
- Check current phase (Phase 1 uses manual buy price)
- Verify stop loss calculation
- Ensure correct trigger logic for phase

#### 4. Paper Trading Not Working
**Symptoms**: Positions not updating in paper mode
**Solution**:
- Verify `paper_trading_enabled = True`
- Check TrueData API connection
- Ensure option matching logic is working
- Verify paper position tracking

#### 5. Live Trading Connection Issues
**Symptoms**: Orders not executing, connection errors
**Solution**:
- Verify Kite Connect API credentials
- Check access token validity
- Ensure sufficient API rate limits
- Validate account permissions

### Debug Mode:
```python
# Enable detailed logging
app.logger.setLevel(logging.DEBUG)

# Print debug information
DEBUG_MODE = True  # Shows detailed position tracking
```

### Log File Locations:
- **Application Logs**: Console output
- **Trade History**: `app_state['trade_history']`
- **Error Logs**: Exception traceback in console
- **Position Data**: Real-time position dictionaries

---

## 📈 PERFORMANCE MONITORING

### Key Metrics to Track:
1. **Win Rate**: Profitable trades / Total trades
2. **Average Profit**: Mean profit per winning trade
3. **Average Loss**: Mean loss per losing trade
4. **Maximum Drawdown**: Largest peak-to-trough decline
5. **Auto Buy Success Rate**: Successful auto buys / Total attempts

### Trade History Analysis:
```python
# Access trade history
trades = app_state['trade_history']

# Filter by action type
buys = [t for t in trades if t['action'] == 'Auto Buy']
sells = [t for t in trades if 'Sell' in t['action']]

# Calculate metrics
total_pnl = sum(t['pnl'] for t in trades)
win_rate = len([t for t in trades if t['pnl'] > 0]) / len(trades)
```

---

## 🔒 SECURITY CONSIDERATIONS

### API Security:
- **Never commit API keys** to version control
- **Use environment variables** for sensitive data
- **Implement token refresh** for expired access tokens
- **Monitor API usage** to avoid rate limit violations

### Trading Security:
- **Position limits**: Maximum number of concurrent positions
- **Loss limits**: Daily/weekly maximum loss thresholds
- **Time restrictions**: Trading hours and session limits
- **Manual overrides**: Emergency stop mechanisms

---

## 🚀 GETTING STARTED

### Installation:
```bash
# Clone repository
git clone <repository_url>
cd StockDashboard

# Create virtual environment
python -m venv stockdashboard
source stockdashboard/bin/activate  # Linux/Mac
# stockdashboard\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### Configuration:
1. **Set up API credentials** in `app.py`
2. **Choose trading mode** (paper/live)
3. **Select algorithm** (simple/advanced)
4. **Configure auto trading parameters**

### Running:
```bash
# Start the application
python app.py

# Access dashboard
http://localhost:5000
```

### Testing:
```bash
# Run algorithm tests
python test_ce55200_fix.py
python test_rapid_fire_fix.py

# Validate stop loss calculations
python test_auto_buy_stop_loss.py
```

---

## 📞 SUPPORT

For technical support or algorithm questions:
- **Review logs** for detailed error information
- **Test in paper mode** before live trading
- **Validate calculations** using provided test scripts
- **Monitor position phases** for correct behavior

**Remember**: Always test thoroughly in paper trading mode before deploying with real money. The financial markets involve substantial risk, and automated trading systems should be monitored regularly.

---

*This documentation covers the complete trading system. For specific implementation details, refer to the source code comments and test files.*