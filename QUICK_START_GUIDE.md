# QUICK START GUIDE
## Stock Dashboard Trading Application

### 🚀 INSTALLATION

#### 1. Prerequisites
```bash
# Ensure Python 3.8+ is installed
python3 --version

# Install pip if not available
sudo apt install python3-pip  # Ubuntu/Debian
```

#### 2. Environment Setup
```bash
# Navigate to project directory
cd /path/to/StockDashboard

# Create virtual environment
python3 -m venv stockdashboard

# Activate virtual environment
source stockdashboard/bin/activate  # Linux/Mac
# stockdashboard\Scripts\activate    # Windows
```

#### 3. Install Dependencies
```bash
# Install all required packages
pip install -r requirements.txt

# Verify installation
pip list
```

### ⚙️ CONFIGURATION

#### 1. API Setup (Live Trading)
Edit `app.py` and update:
```python
KITE_CONFIG = {
    'api_key': 'your_zerodha_api_key',
    'api_secret': 'your_zerodha_api_secret',
    'access_token': 'your_access_token'
}
```

#### 2. Trading Mode
```python
# For safe testing (recommended)
PAPER_TRADING_ENABLED = True

# For live trading (use with caution)
PAPER_TRADING_ENABLED = False
```

#### 3. Algorithm Selection
```python
# Advanced 3-phase algorithm (recommended)
app_state['trading_algorithm'] = 'advanced'

# Simple algorithm (legacy)
app_state['trading_algorithm'] = 'simple'
```

### 🏃 RUNNING THE APPLICATION

#### 1. Start the Server
```bash
# Activate virtual environment
source stockdashboard/bin/activate

# Run the application
python app.py
```

#### 2. Access Dashboard
```
URL: http://localhost:5000
Username: admin
Password: admin123
```

### 🧪 TESTING

#### 1. Test Algorithm
```bash
# Test stop loss calculations
python test_ce55200_fix.py

# Test rapid fire protection
python test_rapid_fire_fix.py

# Test auto buy logic
python test_auto_buy_stop_loss.py
```

#### 2. Paper Trading Test
1. Set `PAPER_TRADING_ENABLED = True`
2. Start application
3. Add manual positions
4. Monitor algorithm behavior
5. Check P&L calculations

### 📊 BASIC USAGE

#### 1. Add Position
- Click "Manual Buy"
- Enter strike price and quantity
- Select CE/PE option type
- Position will start monitoring

#### 2. Monitor Positions
- Real-time price updates
- Stop loss tracking
- Phase detection (1, 2, or 3)
- P&L calculations

#### 3. Auto Trading
- Auto sell at stop loss
- Auto buy back when triggered
- Cooldown protection
- Trade history logging

### 🔧 ALGORITHM BEHAVIOR

#### Phase 1 (Buy to Buy+20)
```
Example: Buy at ₹500
Range: ₹500 to ₹520
Stop Loss: ₹490, ₹500, ₹510 (step-wise)
Auto Buy: At ₹500 (original buy price)
```

#### Phase 2 (Buy+20 to Buy+30)
```
Example: Buy at ₹500, Current ₹525
Range: ₹520 to ₹530
Stop Loss: ₹510, ₹520 (with ₹500 minimum)
Auto Buy: At stop loss sell price
```

#### Phase 3 (After Buy+30)
```
Example: Buy at ₹500, Current ₹535
Range: Above ₹530
Stop Loss: Full algorithm with profit protection
Auto Buy: At stop loss sell price
```

### 🚨 IMPORTANT SAFETY TIPS

1. **Always start with paper trading**
2. **Test thoroughly before live trading**
3. **Monitor positions regularly**
4. **Set position limits**
5. **Keep emergency stop ready**

### 📝 COMMON COMMANDS

```bash
# Activate environment
source stockdashboard/bin/activate

# Install new package
pip install package_name

# Update requirements
pip freeze > requirements.txt

# Run application
python app.py

# Stop application
Ctrl + C
```

### 🔍 TROUBLESHOOTING

#### Application Won't Start
```bash
# Check Python version
python3 --version

# Check dependencies
pip list

# Reinstall requirements
pip install -r requirements.txt --force-reinstall
```

#### API Connection Issues
- Verify API credentials
- Check internet connection
- Ensure Zerodha account is active
- Validate access token

#### Wrong Stop Loss Calculations
- Check algorithm selection
- Verify phase detection
- Test with provided scripts
- Review position data

### 📞 NEED HELP?

1. **Check logs** in terminal output
2. **Run test scripts** to validate behavior
3. **Use paper trading** to debug issues
4. **Review documentation** for detailed explanations

---

**Ready to start trading!** 🎯

Remember: Start with paper trading, test thoroughly, and always monitor your positions!