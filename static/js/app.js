// Global variables
let socket;
let isLoggedIn = false;
let currentSymbol = 'NIFTY';
let currentExpiry = '';
let currentAlgorithm = 'simple'; // Default algorithm
let refreshInterval = 0.5; // Faster refresh rate for real-time prices
let refreshTimer;
let currentPositionView = 'zerodha'; // 'zerodha' or 'auto'
let zerodhaPositionsData = [];
let autoTradingPositionsData = [];
let lotSizes = {
    'NIFTY': 75,
    'BANKNIFTY': 35,
    'MIDCPNIFTY': 140,
    'SENSEX': 10,
    'SBIN': 3400,
    'RELIANCE': 500
};

// --- Live Trading with Zerodha Integration ---
let zerodhaConnected = false;
let tradingReady = false;
let paperTradingEnabled = false;

// DOM elements for Zerodha UI
const zerodhaConnectBtn = document.getElementById('zerodhaConnectBtn');
const zerodhaModal = document.getElementById('zerodhaModal');
const zerodhaStatus = document.getElementById('zerodhaStatus');
const zerodhaLoginBtn = document.getElementById('zerodhaLoginBtn');
const zerodhaInfo = document.getElementById('zerodhaInfo');
const zerodhaFunds = document.getElementById('zerodhaFunds');
const zerodhaPositions = document.getElementById('zerodhaPositions');
const zerodhaOrders = document.getElementById('zerodhaOrders');

// Initialize app
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
    setupSidebarToggle();
    
    // --- Reset Quantities Button ---
    const clearBtn = document.getElementById('clearQuantitiesBtn');
    if (clearBtn) {
        clearBtn.addEventListener('click', function() {
            // Remove all saved lot quantities from localStorage
            Object.keys(localStorage).forEach(key => {
                if (key.startsWith('qty_lots_')) {
                    localStorage.removeItem(key);
                }
            });
            // Reset all qty-input fields to 1 and update display
            const qtyInputs = document.querySelectorAll('.qty-input');
            qtyInputs.forEach(input => {
                input.value = 1;
                input.dispatchEvent(new Event('input', { bubbles: true }));
            });
        });
    }
});

function initializeApp() {
    // Initialize socket connection
    socket = io();
    
    // Setup socket event listeners
    setupSocketListeners();
    
    // Setup event listeners
    setupEventListeners();
    
    // Initialize paper trading toggle
    try {
        initializePaperTradingToggle();
    } catch (error) {
        console.error('Failed to initialize paper trading toggle:', error);
        showToast('⚠️ Paper trading toggle initialization failed', 'warning');
    }
    
    // Initialize cooldown toggle
    try {
        initializeCooldownToggle();
    } catch (error) {
        console.error('Failed to initialize cooldown toggle:', error);
        showToast('⚠️ Cooldown toggle initialization failed', 'warning');
    }
    
    // Check login status
    checkLoginStatus();
    
    // Check startup configuration
    checkStartupConfiguration();
    
    // Start real-time updates
    startRealtimeUpdates();
    
    // Initialize Zerodha connection
    checkZerodhaConnection();
    setupZerodhaModalListeners();
}

async function checkStartupConfiguration() {
    try {
        const response = await fetch('/api/startup-check');
        const data = await response.json();
        
        if (!data.ready) {
            showToast('⚠️ Setup Required: Please configure Zerodha API credentials', 'warning');
            console.log('Setup Status:', data.messages);
        } else {
            showToast('✅ Ready for Live Trading!', 'success');
            tradingReady = true;
        }
    } catch (error) {
        console.error('Error checking startup configuration:', error);
    }
}

function setupSocketListeners() {
    socket.on('connect', function() {
        console.log('Connected to server');
    });
    
    socket.on('disconnect', function() {
        console.log('Disconnected from server');
        showToast
    });
    
    socket.on('market_status_update', function(data) {
        updateMarketStatus(data);
    });
    
    socket.on('wallet_update', function(data) {
        updateWalletInfo(data);
    });
    
    socket.on('option_chain_update', function(data) {
        updateOptionChain(data);
    });
    
    socket.on('positions_update', function(data) {
        console.log('📊 Positions update received:', data);
        zerodhaPositionsData = data;
        if (currentPositionView === 'zerodha') {
            updatePositions(data);
            // Also update position view badge
            const zerodhaTab = document.querySelector('[data-view="zerodha"]');
            if (zerodhaTab && data.positions) {
                const activePositions = data.positions.filter(p => p.quantity > 0);
                zerodhaTab.textContent = `Zerodha Positions (${activePositions.length})`;
            }
        }
    });
    
    socket.on('auto_positions_update', function(data) {
        console.log('🤖 Auto positions update received:', data);
        autoTradingPositionsData = data;
        if (currentPositionView === 'auto') {
            updateAutoTradingPositions(data);
            // Also update position view badge
            const autoTab = document.querySelector('[data-view="auto"]');
            if (autoTab && data.positions) {
                autoTab.textContent = `Auto Trading (${data.positions.length})`;
            }
        }
    });
    
    socket.on('cooldown_status_update', function(data) {
        console.log('🔧 Cooldown status update received:', data);
        const toggle = document.getElementById('cooldownToggle');
        if (toggle) {
            toggle.checked = data.enabled;
            updateCooldownUI(data.enabled);
        }
        if (data.message) {
            const statusIcon = data.enabled ? '🛡️' : '⚡';
            showToast(`${statusIcon} ${data.message}`, 'info');
        }
    });
    
    // 💰 Profitable Re-entry Confirmation Request
    socket.on('reentry_confirmation_request', function(data) {
        console.log('💰 Re-entry confirmation request received:', data);
        showReentryConfirmationModal(data.confirmation, data.message);
    });
}

function setupEventListeners() {
    // Login form
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        console.log('Attaching login event handler');
        loginForm.addEventListener('submit', handleLogin);
        // Fallback: prevent default if JS is loaded but handler not working
        loginForm.onsubmit = function(e) {
            e.preventDefault();
            return false;
        };
    }
    
    // Logout button
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', handleLogout);
    }
    
    // Symbol selection
    const symbolSelect = document.getElementById('symbolSelect');
    if (symbolSelect) {
        symbolSelect.addEventListener('change', handleSymbolChange);
        loadSymbols();
    }
    
    // Expiry selection
    const expirySelect = document.getElementById('expirySelect');
    if (expirySelect) {
        expirySelect.addEventListener('change', handleExpiryChange);
    }
    
    // Algorithm selection
    const algorithmSelect = document.getElementById('algorithmSelect');
    if (algorithmSelect) {
        algorithmSelect.addEventListener('change', handleAlgorithmChange);
    }
    
    // Refresh interval
    const refreshSlider = document.getElementById('refreshInterval');
    if (refreshSlider) {
        refreshSlider.addEventListener('input', handleRefreshIntervalChange);
    }
    
    // Start option chain button
    const startOptionChainBtn = document.getElementById('startOptionChain');
    if (startOptionChainBtn) {
        startOptionChainBtn.addEventListener('click', startOptionChain);
    }
    
    // Position controls
    const sellAllBtn = document.getElementById('sellAllBtn');
    if (sellAllBtn) {
        sellAllBtn.addEventListener('click', sellAllPositions);
    }
    
    const resetStopLossBtn = document.getElementById('resetStopLossBtn');
    if (resetStopLossBtn) {
        resetStopLossBtn.addEventListener('click', resetStopLoss);
    }
    
    const positionFilter = document.getElementById('positionFilter');
    if (positionFilter) {
        positionFilter.addEventListener('change', handlePositionFilter);
    }
    
    // Position toggle buttons
    const zerodhaPositionsBtn = document.getElementById('zerodhaPositionsBtn');
    if (zerodhaPositionsBtn) {
        zerodhaPositionsBtn.addEventListener('click', () => togglePositionView('zerodha'));
    }
    
    const autoTradingPositionsBtn = document.getElementById('autoTradingPositionsBtn');
    if (autoTradingPositionsBtn) {
        autoTradingPositionsBtn.addEventListener('click', () => togglePositionView('auto'));
    }
    
    // Auto trading is always enabled - no toggle needed
    
    // Start Zerodha session monitoring
    startSessionMonitoring();
    
    // Trade history controls
    const clearHistoryBtn = document.getElementById('clearHistoryBtn');
    if (clearHistoryBtn) {
        clearHistoryBtn.addEventListener('click', clearTradeHistory);
    }
    
    const viewAllHistoryBtn = document.getElementById('viewAllHistoryBtn');
    if (viewAllHistoryBtn) {
        viewAllHistoryBtn.addEventListener('click', viewAllHistory);
    }
    
    const historyFilter = document.getElementById('historyFilter');
    if (historyFilter) {
        historyFilter.addEventListener('change', handleHistoryFilter);
    }
    
    // Strike dropdown event listeners
    const callStrikeSelect = document.getElementById('callStrikeSelect');
    if (callStrikeSelect) {
        callStrikeSelect.addEventListener('change', handleStrikeSelection);
    }
    
    const putStrikeSelect = document.getElementById('putStrikeSelect');
    if (putStrikeSelect) {
        putStrikeSelect.addEventListener('change', handleStrikeSelection);
    }
}

function checkLoginStatus() {
    // Check if user is logged in (could be stored in sessionStorage)
    const loginToken = sessionStorage.getItem('loginToken');
    if (loginToken) {
        isLoggedIn = true;
        showDashboard();
    } else {
        showLoginModal();
    }
}

function showLoginModal() {
    const loginModal = document.getElementById('loginModal');
    const dashboard = document.getElementById('dashboard');
    
    if (loginModal) loginModal.style.display = 'flex';
    if (dashboard) dashboard.style.display = 'none';
}

function showDashboard() {
    const loginModal = document.getElementById('loginModal');
    const dashboard = document.getElementById('dashboard');
    
    if (loginModal) loginModal.style.display = 'none';
    if (dashboard) dashboard.style.display = 'block';
    
    // Load initial data
    loadInitialData();
    
    // Check if trading is ready and show alert if not
    setTimeout(() => {
        if (!tradingReady || !zerodhaConnected) {
            showTradingAlert(
                'Setup Required',
                'Welcome to TradePro! To start live trading, please connect your Zerodha account. You can still view option chains and analyze market data without connecting.',
                true
            );
        }
    }, 1000); // Small delay to let the dashboard load first
}

async function handleLogin(event) {
    event.preventDefault();
    
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const errorDiv = document.getElementById('loginError');
    
    try {
        const response = await fetch('/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, password })
        });
        
        const data = await response.json();
        
        if (data.success) {
            sessionStorage.setItem('loginToken', data.token);
            isLoggedIn = true;
            showDashboard();
            showToast('Login successful!', 'success');
        } else {
            errorDiv.textContent = data.message || 'Invalid credentials';
        }
    } catch (error) {
        errorDiv.textContent = 'Login failed. Please try again.';
        console.error('Login error:', error);
    }
}

async function handleLogout() {
    try {
        const response = await fetch('/logout', { method: 'POST' });
        const data = await response.json();
        
        sessionStorage.removeItem('loginToken');
        isLoggedIn = false;
        showLoginModal();
        
        // Show appropriate message based on Zerodha disconnection
        if (data.zerodha_disconnected) {
            showToast('🔌 Logged out successfully. Zerodha connection disconnected for safety.', 'success');
        } else {
            showToast('Logged out successfully', 'info');
        }
        
        console.log('Logout:', data.message);
    } catch (error) {
        console.error('Logout error:', error);
        showToast('Logged out (connection error)', 'warning');
    }
}

function loadInitialData() {
    loadMarketStatus();
    loadWalletInfo();
    loadTradeHistory();
    loadPositions();
    loadCurrentAlgorithm();
    updateCurrentTime();
    
    // Auto-start option chain with default settings
    autoStartOptionChain();
    
    // Start real-time updates
    startRealtimeUpdates();
    
    // Also try to load option chain data directly via API
    setTimeout(loadOptionChainData, 2000);
    
    // Update time every second
    setInterval(updateCurrentTime, 1000);
}

async function loadCurrentAlgorithm() {
    try {
        const response = await fetch('/api/trading-algorithm');
        const data = await response.json();
        
        if (data.algorithm) {
            currentAlgorithm = data.algorithm;
            
            // Update algorithm select if element exists
            const algorithmSelect = document.getElementById('algorithmSelect');
            if (algorithmSelect) {
                algorithmSelect.value = currentAlgorithm;
                
                // Update descriptions
                const simpleDesc = document.getElementById('simpleDesc');
                const advancedDesc = document.getElementById('advancedDesc');
                
                if (currentAlgorithm === 'simple') {
                    if (simpleDesc) simpleDesc.style.display = 'block';
                    if (advancedDesc) advancedDesc.style.display = 'none';
                } else {
                    if (simpleDesc) simpleDesc.style.display = 'none';
                    if (advancedDesc) advancedDesc.style.display = 'block';
                }
            }
            
            console.log(`🧠 Loaded algorithm: ${currentAlgorithm}`);
        }
    } catch (error) {
        console.error('Error loading algorithm:', error);
    }
}

async function loadOptionChainData() {
    try {
        const response = await fetch('/api/option-chain-data');
        const data = await response.json();
        
        if (data.success) {
            console.log('Option chain data loaded:', data);
            updateOptionChain(data);
        } else {
            console.log('No option chain data available:', data.message);
        }
    } catch (error) {
        console.error('Error loading option chain data:', error);
    }
}

async function autoStartOptionChain() {
    try {
        const response = await fetch('/api/auto-start-option-chain', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (data.success) {
            console.log('Auto-started option chain successfully');
            showToast('Option chain started automatically', 'success');
            // Wait a bit then load the data
            setTimeout(loadOptionChainData, 3000);
        } else {
            console.log('Auto-start failed:', data.message);
            // Try manual start with default values
            await startDefaultOptionChain();
        }
    } catch (error) {
        console.error('Auto-start error:', error);
        // Try manual start with default values
        await startDefaultOptionChain();
    }
}

async function startDefaultOptionChain() {
    try {
        // Get first available expiry for NIFTY
        const expiryResponse = await fetch('/api/expiry-list/NIFTY');
        const expiries = await expiryResponse.json();
        
        if (expiries && expiries.length > 0) {
            // Handle both old format (string) and new format (object)
            const firstExpiry = typeof expiries[0] === 'object' ? expiries[0].value : expiries[0];
            
            const response = await fetch('/api/start-option-chain', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    symbol: 'NIFTY',
                    expiry: firstExpiry
                })
            });
            
            const data = await response.json();
            if (data.success) {
                console.log('Started default option chain');
                currentSymbol = 'NIFTY';
                currentExpiry = expiries[0];
                
                // Update the UI selects
                const symbolSelect = document.getElementById('symbolSelect');
                const expirySelect = document.getElementById('expirySelect');
                if (symbolSelect) symbolSelect.value = 'NIFTY';
                if (expirySelect) {
                    const firstExpiry = typeof expiries[0] === 'object' ? expiries[0].value : expiries[0];
                    const firstExpiryDisplay = typeof expiries[0] === 'object' ? expiries[0].display : expiries[0];
                    expirySelect.innerHTML = `<option value="${firstExpiry}" selected>${firstExpiryDisplay}</option>`;
                }
                
                // Wait a bit then load the data
                setTimeout(loadOptionChainData, 3000);
            }
        }
    } catch (error) {
        console.error('Default option chain start failed:', error);
    }
}

function loadSymbols() {
    const symbolSelect = document.getElementById('symbolSelect');
    if (!symbolSelect) return;
    
    // Clear existing options
    symbolSelect.innerHTML = '';
    
    Object.keys(lotSizes).forEach(symbol => {
        const option = document.createElement('option');
        option.value = symbol;
        option.textContent = `${symbol} (Lot: ${lotSizes[symbol]})`;
        if (symbol === currentSymbol) option.selected = true;
        symbolSelect.appendChild(option);
    });
    
    // Load expiry list for current symbol
    loadExpiryList();
}

async function handleSymbolChange() {
    const symbolSelect = document.getElementById('symbolSelect');
    currentSymbol = symbolSelect.value;
    
    // Load expiry list for selected symbol
    await loadExpiryList();
}

async function loadExpiryList() {
    const expirySelect = document.getElementById('expirySelect');
    try {
        const response = await fetch(`/api/expiry-list/${currentSymbol}`);
        const expiries = await response.json();
        
        console.log('Expiry API response:', expiries);
        
        expirySelect.innerHTML = '<option value="">Select Expiry</option>';
        
        if (Array.isArray(expiries) && expiries.length > 0) {
            expiries.forEach(expiry => {
                const option = document.createElement('option');
                // Handle both old format (string) and new format (object)
                if (typeof expiry === 'object' && expiry.value && expiry.display) {
                    option.value = expiry.value;
                    option.textContent = expiry.display;
                } else {
                    // Handle string format or fallback
                    option.value = expiry;
                    option.textContent = expiry;
                }
                expirySelect.appendChild(option);
            });
            
            // Select the first expiry by default
            const firstExpiry = typeof expiries[0] === 'object' ? expiries[0].value : expiries[0];
            expirySelect.value = firstExpiry;
            currentExpiry = firstExpiry;
            
            console.log('Loaded', expiries.length, 'expiry dates. Selected:', firstExpiry);
        } else if (expiries.error) {
            console.error('Expiry API error:', expiries.error);
            showToast('Failed to load expiry dates: ' + expiries.error, 'error');
        } else {
            console.warn('No expiry dates available for symbol:', currentSymbol);
            showToast('No expiry dates available for this symbol', 'warning');
        }
    } catch (error) {
        console.error('Error loading expiry list:', error);
        showToast('Failed to load expiry list: ' + error.message, 'error');
        
        // Show fallback message in dropdown
        expirySelect.innerHTML = '<option value="">Failed to load expiry dates</option>';
    }
}

function handleExpiryChange() {
    const expirySelect = document.getElementById('expirySelect');
    currentExpiry = expirySelect.value;
}

function handleAlgorithmChange() {
    const algorithmSelect = document.getElementById('algorithmSelect');
    currentAlgorithm = algorithmSelect.value;
    
    // Update algorithm descriptions
    const simpleDesc = document.getElementById('simpleDesc');
    const advancedDesc = document.getElementById('advancedDesc');
    
    if (currentAlgorithm === 'simple') {
        if (simpleDesc) simpleDesc.style.display = 'block';
        if (advancedDesc) advancedDesc.style.display = 'none';
    } else {
        if (simpleDesc) simpleDesc.style.display = 'none';
        if (advancedDesc) advancedDesc.style.display = 'block';
    }
    
    // Send algorithm change to backend
    updateTradingAlgorithm(currentAlgorithm);
    
    // Show toast notification
    const algoName = currentAlgorithm === 'simple' ? 'Simple Stop Loss' : 'Advanced Trailing Stop Loss';
    showToast(`🧠 Algorithm changed to: ${algoName}`, 'info');
}

async function updateTradingAlgorithm(algorithm) {
    try {
        const response = await fetch('/api/trading-algorithm', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                algorithm: algorithm
            })
        });
        
        const data = await response.json();
        if (data.success) {
            console.log(`✅ Algorithm updated to: ${algorithm}`);
        } else {
            console.error('❌ Failed to update algorithm:', data.error);
        }
    } catch (error) {
        console.error('❌ Error updating algorithm:', error);
    }
}

function handleRefreshIntervalChange() {
    const refreshSlider = document.getElementById('refreshInterval');
    const refreshValue = document.getElementById('refreshValue');
    
    refreshInterval = parseFloat(refreshSlider.value);
    refreshValue.textContent = refreshInterval + 's';
    
    // Restart refresh timer with new interval
    if (refreshTimer) {
        clearInterval(refreshTimer);
    }
    startRealtimeUpdates();
}

function handleStrikeSelection(event) {
    const selectedStrike = event.target.value;
    const isCallDropdown = event.target.id === 'callStrikeSelect';
    
    if (!selectedStrike) return;
    
    console.log(`Strike selected: ${selectedStrike} (${isCallDropdown ? 'CE' : 'PE'})`);
    
    // Find the option item with matching strike
    const targetContainer = isCallDropdown ? 'callsOptions' : 'putsOptions';
    const container = document.getElementById(targetContainer);
    
    if (!container) return;
    
    // Find the option item with matching strike
    const optionItems = container.querySelectorAll('.option-item');
    let targetItem = null;
    
    optionItems.forEach(item => {
        const strikeElement = item.querySelector('.option-strike');
        if (strikeElement && parseFloat(strikeElement.textContent) === parseFloat(selectedStrike)) {
            targetItem = item;
        }
    });
    
    if (targetItem) {
        // Scroll to the selected option with smooth animation
        targetItem.scrollIntoView({
            behavior: 'smooth',
            block: 'center'
        });
        
        // Add highlight effect
        targetItem.style.transform = 'scale(1.02)';
        targetItem.style.boxShadow = '0 8px 25px rgba(59, 130, 246, 0.3)';
        targetItem.style.border = '2px solid var(--accent-color)';
        
        // Remove highlight after 2 seconds
        setTimeout(() => {
            targetItem.style.transform = '';
            targetItem.style.boxShadow = '';
            targetItem.style.border = '';
        }, 2000);
        
        showToast(`Scrolled to ${selectedStrike} ${isCallDropdown ? 'CE' : 'PE'}`, 'success');
    } else {
        showToast(`Option ${selectedStrike} ${isCallDropdown ? 'CE' : 'PE'} not found in current view`, 'warning');
    }
    
    // Reset dropdown selection
    event.target.value = '';
}

async function startOptionChain() {
    if (!currentSymbol || !currentExpiry) {
        showToast('Please select symbol and expiry', 'warning');
        return;
    }
    
    showLoading(true);
    
    try {
        const response = await fetch('/api/start-option-chain', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                symbol: currentSymbol,
                expiry: currentExpiry
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('Option chain started successfully', 'success');
            // The real-time updates will handle the data
        } else {
            showToast(data.message || 'Failed to start option chain', 'error');
        }
    } catch (error) {
        console.error('Error starting option chain:', error);
        showToast('Failed to start option chain', 'error');
    } finally {
        showLoading(false);
    }
}

function startRealtimeUpdates() {
    if (refreshTimer) {
        clearInterval(refreshTimer);
    }
    
    refreshTimer = setInterval(() => {
        if (isLoggedIn) {
            loadMarketStatus();
            loadWalletInfo();
            loadPositions();
            loadTradeHistory();
            loadOptionChainData(); // Add this to regularly fetch option chain data
        }
    }, refreshInterval * 1000);
}

// Add live refresh for positions table
let positionsRefreshTimer;
function startPositionsLiveRefresh() {
    if (positionsRefreshTimer) clearInterval(positionsRefreshTimer);
    positionsRefreshTimer = setInterval(() => {
        loadPositions();
    }, 500); // 0.5 sec refresh - as requested
}
function stopPositionsLiveRefresh() {
    if (positionsRefreshTimer) clearInterval(positionsRefreshTimer);
}
// Call this after DOM ready
if (document.readyState === 'complete' || document.readyState === 'interactive') {
    startPositionsLiveRefresh();
} else {
    window.addEventListener('DOMContentLoaded', startPositionsLiveRefresh);
}

async function loadMarketStatus() {
    try {
        const response = await fetch('/api/market-status');
        const data = await response.json();
        updateMarketStatus(data);
    } catch (error) {
        console.error('Error loading market status:', error);
    }
}

function updateMarketStatus(data) {
    const statusCard = document.getElementById('marketStatusCard');
    const status = document.getElementById('marketStatus');
    const reason = document.getElementById('marketReason');
    const message = document.getElementById('marketMessage');
    const nextOpen = document.getElementById('marketNextOpen');
    const currentTime = document.getElementById('marketCurrentTime');
    
    if (status) status.textContent = `${data.status === 'OPEN' ? '🟢' : '🚫'} MARKET ${data.status}`;
    if (reason) reason.textContent = data.reason;
    if (message) message.textContent = data.message;
    if (nextOpen) nextOpen.textContent = data.status === 'OPEN' ? `Closes at: ${data.closes_at}` : `Next Open: ${data.next_open}`;
    if (currentTime) currentTime.textContent = `Current IST: ${data.current_ist}`;
    
    if (statusCard) {
        if (data.status === 'OPEN') {
            statusCard.classList.add('open');
        } else {
            statusCard.classList.remove('open');
        }
    }
}

async function loadWalletInfo() {
    try {
        const response = await fetch('/api/wallet-info');
        const data = await response.json();
        updateWalletInfo(data);
    } catch (error) {
        console.error('Error loading wallet info:', error);
    }
}

function updateWalletInfo(data) {
    // Update UI elements based on trading mode
    const portfolioTitle = document.getElementById('portfolioTitle');
    const portfolioDataSource = document.getElementById('portfolioDataSource');
    const resetWalletBtn = document.getElementById('resetPaperWalletBtn');
    const balanceMode = document.getElementById('balanceMode');
    
    if (data && data.mode === 'paper') {
        // Paper Trading Mode
        if (portfolioTitle) portfolioTitle.textContent = 'Paper Trading Summary';
        if (portfolioDataSource) portfolioDataSource.textContent = 'Virtual Portfolio';
        if (resetWalletBtn) resetWalletBtn.style.display = 'inline-block';
        if (balanceMode) balanceMode.textContent = 'PAPER TRADING';
        
        const elements = {
            'walletBalance': data.wallet_balance,
            'walletInvested': data.total_investment || 0,
            'walletCurrentValue': data.current_value || 0,
            'walletUnrealizedPnl': data.unrealized_pnl || 0,
            'walletRealizedPnl': data.realized_pnl || 0,
            'walletTotalPortfolio': (data.wallet_balance || 0) + (data.current_value || 0),
            'walletNetPnl': (data.unrealized_pnl || 0) + (data.realized_pnl || 0)
        };
        
        Object.keys(elements).forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                const value = elements[id];
                element.textContent = `₹${formatNumber(value)}`;
                
                // Add paper trading styling
                element.classList.add('paper-mode');
            }
        });
        
        // Update positions metric
        const positionsElement = document.getElementById('walletPositions');
        if (positionsElement) {
            positionsElement.innerHTML = `${data.total_positions || 0} Active<br><small>Paper Positions</small>`;
        }
        
        // Update P&L summary for paper trading
        updatePnlSummary({
            unrealized_pnl: data.unrealized_pnl || 0,
            realized_pnl: data.realized_pnl || 0,
            total_positions: data.total_positions || 0
        });
        
    } else {
        // Live Trading Mode
        if (portfolioTitle) portfolioTitle.textContent = 'Live Portfolio Summary';
        if (portfolioDataSource) portfolioDataSource.textContent = 'Zerodha Live Data';
        if (resetWalletBtn) resetWalletBtn.style.display = 'none';
        if (balanceMode) balanceMode.textContent = 'LIVE TRADING';
        
        if (data) {
            const elements = {
                'walletBalance': data.balance,
                'walletInvested': data.invested,
                'walletCurrentValue': data.current_value,
                'walletUnrealizedPnl': data.unrealized_pnl,
                'walletRealizedPnl': data.realized_pnl,
                'walletTotalPortfolio': data.total_wallet_value,
                'walletNetPnl': data.net_pnl
            };
            
            Object.keys(elements).forEach(id => {
                const element = document.getElementById(id);
                if (element) {
                    const value = elements[id];
                    element.textContent = `₹${formatNumber(value)}`;
                    
                    // Remove paper trading styling
                    element.classList.remove('paper-mode');
                }
            });
            
            // Update positions metric
            const positionsElement = document.getElementById('walletPositions');
            if (positionsElement) {
                positionsElement.innerHTML = `${data.total_positions} Active<br><small>${data.waiting_positions} Waiting</small>`;
            }
            
            // Update P&L summary
            updatePnlSummary(data);
        }
    }
}

function updatePnlSummary(data) {
    const profitCard = document.getElementById('profitCard');
    const lossCard = document.getElementById('lossCard');
    const netPnlCard = document.getElementById('netPnlCard');
    const noPnlMessage = document.getElementById('noPnlMessage');
    
    const totalProfit = Math.max(0, data.unrealized_pnl);
    const totalLoss = Math.abs(Math.min(0, data.unrealized_pnl));
    const netPnl = data.net_pnl;
    
    if (data.total_positions > 0) {
        if (noPnlMessage) noPnlMessage.style.display = 'none';
        
        if (totalProfit > 0) {
            if (profitCard) {
                profitCard.style.display = 'block';
                document.getElementById('profitAmount').textContent = `₹${formatNumber(totalProfit)}`;
                document.getElementById('profitPositions').textContent = `${data.total_positions} positions in profit`;
            }
        } else {
            if (profitCard) profitCard.style.display = 'none';
        }
        
        if (totalLoss > 0) {
            if (lossCard) {
                lossCard.style.display = 'block';
                document.getElementById('lossAmount').textContent = `₹${formatNumber(totalLoss)}`;
                document.getElementById('lossPositions').textContent = `${data.total_positions} positions in loss`;
            }
        } else {
            if (lossCard) lossCard.style.display = 'none';
        }
        
        if (netPnlCard) {
            netPnlCard.style.display = 'block';
            const netPnlText = document.getElementById('netPnlText');
            if (netPnlText) {
                const icon = netPnl > 0 ? '📈' : netPnl < 0 ? '📉' : '➡️';
                const text = netPnl > 0 ? 'Net Profit' : netPnl < 0 ? 'Net Loss' : 'Break Even';
                netPnlText.textContent = `${icon} ${text}: ₹${formatNumber(Math.abs(netPnl))}`;
            }
        }
    } else {
        if (profitCard) profitCard.style.display = 'none';
        if (lossCard) lossCard.style.display = 'none';
        if (netPnlCard) netPnlCard.style.display = 'none';
        if (noPnlMessage) noPnlMessage.style.display = 'block';
    }
}

function updateOptionChain(data) {
    console.log('updateOptionChain called with data:', data);
    
    if (!data.success) {
        console.error('Option chain update failed:', data.message);
        return;
    }
    
    console.log('Updating option chain with:', {
        underlying: data.underlying,
        atm_strike: data.atm_strike,
        calls: data.calls?.length || 0,
        puts: data.puts?.length || 0,
        total_options: data.total_options
    });
    
    // Update option metrics
    const underlyingPrice = document.getElementById('underlyingPrice');
    const totalOptions = document.getElementById('totalOptions');
    const callsCount = document.getElementById('callsCount');
    const putsCount = document.getElementById('putsCount');
    
    if (underlyingPrice) {
        underlyingPrice.textContent = data.underlying ? `₹${data.underlying.toFixed(2)}` : 'N/A';
        console.log('Updated underlying price:', underlyingPrice.textContent);
    }
    if (totalOptions) {
        totalOptions.textContent = data.total_options || 0;
        console.log('Updated total options:', totalOptions.textContent);
    }
    if (callsCount) {
        callsCount.textContent = data.ce_count || 0;
        console.log('Updated calls count:', callsCount.textContent);
    }
    if (putsCount) {
        putsCount.textContent = data.pe_count || 0;
        console.log('Updated puts count:', putsCount.textContent);
    }
    
    // Update calls
    console.log('Updating calls with data:', data.calls);
    updateOptionsColumn('callsOptions', data.calls, 'CE');
    
    // Update puts
    console.log('Updating puts with data:', data.puts);
    updateOptionsColumn('putsOptions', data.puts, 'PE');
    
    // Update ATM
    console.log('Updating ATM with data:', data.atm);
    updateAtmOptions(data.atm, data.atm_strike);
    
    // Update strike dropdowns
    updateStrikeDropdowns(data.calls, data.puts);
}

function updateStrikeDropdowns(calls, puts) {
    console.log('Updating strike dropdowns with calls:', calls?.length || 0, 'puts:', puts?.length || 0);
    
    // Update calls dropdown
    const callDropdown = document.getElementById('callStrikeSelect');
    if (callDropdown && calls && calls.length > 0) {
        // Clear existing options except the first placeholder
        callDropdown.innerHTML = '<option value="">Select Strike...</option>';
        
        // Add call options sorted by strike
        const sortedCalls = [...calls].sort((a, b) => a.strike - b.strike);
        sortedCalls.forEach(call => {
            const option = document.createElement('option');
            option.value = call.strike;
            option.textContent = `${call.strike} CE - ₹${call.ltp}`;
            callDropdown.appendChild(option);
        });
        
        console.log(`Added ${sortedCalls.length} call options to dropdown`);
    }
    
    // Update puts dropdown
    const putDropdown = document.getElementById('putStrikeSelect');
    if (putDropdown && puts && puts.length > 0) {
        // Clear existing options except the first placeholder
        putDropdown.innerHTML = '<option value="">Select Strike...</option>';
        
        // Add put options sorted by strike
        const sortedPuts = [...puts].sort((a, b) => a.strike - b.strike);
        sortedPuts.forEach(put => {
            const option = document.createElement('option');
            option.value = put.strike;
            option.textContent = `${put.strike} PE - ₹${put.ltp}`;
            putDropdown.appendChild(option);
        });
        
        console.log(`Added ${sortedPuts.length} put options to dropdown`);
    }
}

function updateOptionsColumn(containerId, options, optionType) {
    console.log(`updateOptionsColumn called for ${containerId} with ${options?.length || 0} options of type ${optionType}`);
    
    const container = document.getElementById(containerId);
    if (!container) {
        console.error(`Container ${containerId} not found`);
        return;
    }
    
    if (!options || options.length === 0) {
        console.log(`No options for ${containerId}, showing info message`);
        container.innerHTML = '<div class="info-message">No options available</div>';
        return;
    }
    
    console.log(`Processing ${options.length} options for ${containerId}:`, options);
    
    // Check if container already has option items
    const existingItems = container.querySelectorAll('.option-item');
    const newOptions = options.slice(0, 5);
    
    // If structure matches, just update prices instead of recreating everything
    if (existingItems.length === newOptions.length) {
        let structureMatches = true;
        
        // Check if strikes match
        for (let i = 0; i < newOptions.length; i++) {
            const existingStrike = existingItems[i].querySelector('.option-strike');
            if (!existingStrike || parseFloat(existingStrike.textContent) !== newOptions[i].strike) {
                structureMatches = false;
                break;
            }
        }
        
        if (structureMatches) {
            // Just update prices and values, don't recreate cards
            updateOptionPricesOnly(existingItems, newOptions, optionType);
            console.log(`Updated prices only for ${containerId}`);
            return;
        }
    }
    
    // Structure doesn't match, recreate everything
    container.innerHTML = '';
    
    newOptions.forEach((option, index) => {
        console.log(`Creating option item ${index} for ${containerId}:`, option);
        const optionItem = createOptionItem(option, optionType);
        container.appendChild(optionItem);
    });
    
    console.log(`Recreated ${containerId} with ${container.children.length} option items`);
    
    // Restore saved quantities after updating options
    restoreQuantities();
}

function updateOptionPricesOnly(existingItems, newOptions, optionType) {
    /**
     * Update only prices and calculated values without recreating the entire option card
     */
    for (let i = 0; i < existingItems.length && i < newOptions.length; i++) {
        const item = existingItems[i];
        const option = newOptions[i];
        
        // Update price
        const priceElement = item.querySelector('.option-price');
        if (priceElement) {
            const newPrice = option.ltp || 0;
            priceElement.textContent = `₹${newPrice.toFixed(2)}`;
            
            // Add highlight effect for price change
            priceElement.classList.add('highlight-update');
            setTimeout(() => {
                priceElement.classList.remove('highlight-update');
            }, 500);
        }
        
        // Update bid/ask if exists
        const bidElement = item.querySelector('.bid');
        const askElement = item.querySelector('.ask');
        if (bidElement && option.bid !== undefined) {
            bidElement.textContent = `Bid: ₹${(option.bid || 0).toFixed(2)}`;
        }
        if (askElement && option.ask !== undefined) {
            askElement.textContent = `Ask: ₹${(option.ask || 0).toFixed(2)}`;
        }
        
        // Update calculated values (total qty and total value)
        const strike = option.strike;
        const price = option.ltp || 0;
        const lotSize = lotSizes[currentSymbol] || 75;
        const inputId = `lots_${strike}_${optionType}`;
        const totalQtyId = `total_qty_${strike}_${optionType}`;
        const totalValueId = `total_value_${strike}_${optionType}`;
        
        // Get current lot quantity
        const lotsInput = item.querySelector(`#${inputId}`);
        if (lotsInput) {
            const lots = parseInt(lotsInput.value) || 1;
            const totalQty = lots * lotSize;
            const totalValue = totalQty * price;
            
            // Update total qty display
            const totalQtyElement = item.querySelector(`#${totalQtyId}`);
            if (totalQtyElement) {
                totalQtyElement.textContent = totalQty;
            }
            
            // Update total value display
            const totalValueElement = item.querySelector(`#${totalValueId}`);
            if (totalValueElement) {
                totalValueElement.textContent = `₹${totalValue.toFixed(0)}`;
                
                // Add highlight effect for value change
                totalValueElement.classList.add('highlight-update');
                setTimeout(() => {
                    totalValueElement.classList.remove('highlight-update');
                }, 500);
            }
            
            // Update button onclick handlers with new price
            const buyButton = item.querySelector('.btn-buy');
            const sellButton = item.querySelector('.btn-sell');
            
            if (buyButton) {
                buyButton.setAttribute('onclick', `buyOptionWithLots(${strike}, '${optionType}', ${price}, '${inputId}', this)`);
            }
            
            if (sellButton) {
                sellButton.setAttribute('onclick', `sellOption(${strike}, '${optionType}', ${price})`);
            }
        }
    }
}

function createOptionItem(option, optionType) {
    const div = document.createElement('div');
    div.className = 'option-item';
    
    const strike = option.strike;
    const price = option.ltp || 0;
    const bid = option.bid || 0;
    const ask = option.ask || 0;
    const lotSize = lotSizes[currentSymbol] || 75;
    const inputId = `lots_${strike}_${optionType}`;
    const totalQtyId = `total_qty_${strike}_${optionType}`;
    const totalValueId = `total_value_${strike}_${optionType}`;
    
    // Get saved quantity value or default to 1
    const savedQty = getSavedQuantity(inputId) || 1;
    const totalQty = savedQty * lotSize;
    const totalValue = totalQty * price;
    
    div.innerHTML = `
        <div class="option-header">
            <span class="option-strike">${strike}</span>
            <span class="option-price">₹${price.toFixed(2)}</span>
        </div>
        
        <div class="option-info">
            <div class="lot-info">
                <span class="label">Lot Size:</span>
                <span class="value">${lotSize}</span>
            </div>
            <div class="total-qty-info">
                <span class="label">Total Qty:</span>
                <span class="value total-qty" id="${totalQtyId}">${totalQty}</span>
            </div>
            <div class="total-value-info">
                <span class="label">Total Value:</span>
                <span class="value total-value" id="${totalValueId}">₹${totalValue.toFixed(0)}</span>
            </div>
        </div>
        
        <div class="option-controls">
            <div class="qty-selector-container">
                <label class="qty-label">Lots:</label>
                <div class="qty-selector">
                    <button type="button" class="qty-btn qty-minus" onclick="adjustQuantity('${inputId}', -1)" title="Decrease lots">
                        <i class="fas fa-minus"></i>
                    </button>
                    <input type="number" class="qty-input" value="${savedQty}" min="1" max="20" id="${inputId}" 
                           onchange="updateQuantityDisplay('${inputId}', ${lotSize}, ${price}, '${totalQtyId}', '${totalValueId}')"
                           oninput="updateQuantityDisplay('${inputId}', ${lotSize}, ${price}, '${totalQtyId}', '${totalValueId}')">
                    <button type="button" class="qty-btn qty-plus" onclick="adjustQuantity('${inputId}', 1)" title="Increase lots">
                        <i class="fas fa-plus"></i>
                    </button>
                </div>
            </div>
            
            <div class="action-buttons">
                <button class="btn btn-buy" onclick="buyOptionWithLots(${strike}, '${optionType}', ${price}, '${inputId}', this)" title="Buy ${optionType} ${strike}">
                    <i class="fas fa-arrow-up"></i>
                    Buy
                </button>
                <button class="btn btn-sell" onclick="sellOption(${strike}, '${optionType}', ${price})" title="Sell ${optionType} ${strike}">
                    <i class="fas fa-arrow-down"></i>
                    Sell
                </button>
            </div>
        </div>
        
        ${bid > 0 || ask > 0 ? `
            <div class="option-details">
                <span class="bid-ask">
                    <span class="bid">Bid: ₹${bid.toFixed(2)}</span>
                    <span class="ask">Ask: ₹${ask.toFixed(2)}</span>
                </span>
            </div>
        ` : ''}
    `;
    
    return div;
}

async function buyOptionWithLots(strike, optionType, price, lotsInputId, buttonElement) {
    const lotsInput = document.getElementById(lotsInputId);
    const lots = lotsInput ? parseInt(lotsInput.value) : 1;
    
    // Use the passed button element
    const buyButton = buttonElement;
    
    if (buyButton) {
        buyButton.disabled = true;
        buyButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Buying...';
        buyButton.classList.add('loading');
    }
    
    // Add visual feedback
    if (lotsInput) {
        lotsInput.classList.add('qty-updated');
        setTimeout(() => lotsInput.classList.remove('qty-updated'), 300);
    }
    
    // Calculate total value for display
    const lotSize = lotSizes[currentSymbol] || 75;
    const totalQty = lots * lotSize;
    const totalValue = totalQty * price;
    
    // Show quick feedback and place order directly
    console.log(`Placing order: ${lots} lot${lots > 1 ? 's' : ''} of ${optionType} ${strike}`);
    console.log(`Lot Size: ${lotSize}, Total Quantity: ${totalQty}, Price: ₹${price.toFixed(2)}, Total Value: ₹${totalValue.toFixed(0)}`);
    
    try {
        // Direct buy without confirmation
        await buyOption(strike, optionType, price, lots);
    } finally {
        // Restore button state
        if (buyButton) {
            buyButton.disabled = false;
            buyButton.innerHTML = '<i class="fas fa-arrow-up"></i> Buy';
            buyButton.classList.remove('loading');
        }
    }
}

function updateAtmPricesOnly(atmOptions, atmStrike) {
    const container = document.getElementById('atmOptions');
    if (!container) return false;
    
    if (!atmOptions || atmOptions.length === 0) {
        return false; // Structure changed, need full update
    }
    
    const existingItems = container.querySelectorAll('.atm-item');
    
    // Check if structure matches
    if (existingItems.length !== atmOptions.length) {
        return false; // Different number of items, need full update
    }
    
    // Update prices for each existing item
    atmOptions.forEach((option, index) => {
        const item = existingItems[index];
        if (!item) return false;
        
        const optionType = option.option_type;
        const price = option.ltp || 0;
        const bid = option.bid || 0;
        const ask = option.ask || 0;
        
        // Verify this is the correct item
        const label = item.querySelector('.metric-label');
        const expectedLabel = `${atmStrike} ${optionType}`;
        if (!label || label.textContent !== expectedLabel) {
            return false; // Structure mismatch
        }
        
        // Update the price
        const priceElement = item.querySelector('.metric-value');
        if (priceElement) {
            const newPrice = `₹${price.toFixed(2)}`;
            if (priceElement.textContent !== newPrice) {
                priceElement.textContent = newPrice;
                // Add visual feedback for price change
                priceElement.style.backgroundColor = '#e3f2fd';
                setTimeout(() => {
                    priceElement.style.backgroundColor = '';
                }, 500);
            }
        }
        
        // Update bid/ask if present
        const detailsDiv = item.querySelector('.atm-details');
        if (bid > 0 || ask > 0) {
            if (detailsDiv) {
                const bidDiv = detailsDiv.children[0];
                const askDiv = detailsDiv.children[1];
                if (bidDiv) bidDiv.textContent = `Bid: ₹${bid.toFixed(1)}`;
                if (askDiv) askDiv.textContent = `Ask: ₹${ask.toFixed(1)}`;
            }
        }
    });
    
    return true; // Successfully updated prices only
}

function updateAtmOptions(atmOptions, atmStrike) {
    const container = document.getElementById('atmOptions');
    if (!container) return;
    
    if (!atmOptions || atmOptions.length === 0) {
        container.innerHTML = '<div class="info-message">No ATM options</div>';
        return;
    }
    
    // Try price-only update first
    if (updateAtmPricesOnly(atmOptions, atmStrike)) {
        return; // Successfully updated prices only
    }
    
    // Full update needed
    container.innerHTML = '';
    
    atmOptions.forEach(option => {
        const div = document.createElement('div');
        div.className = 'atm-item';
        
        const optionType = option.option_type;
        const price = option.ltp || 0;
        const bid = option.bid || 0;
        const ask = option.ask || 0;
        
        div.innerHTML = `
            <div class="metric-label">${atmStrike} ${optionType}</div>
            <div class="metric-value">₹${price.toFixed(2)}</div>
            ${bid > 0 || ask > 0 ? `
                <div class="atm-details">
                    <div>Bid: ₹${bid.toFixed(1)}</div>
                    <div>Ask: ₹${ask.toFixed(1)}</div>
                </div>
            ` : ''}
        `;
        
        container.appendChild(div);
    });
}

async function buyOption(strike, optionType, price, lots = 1) {
    // Check if trading is ready (paper trading or live trading with Zerodha)
    if (!window.paperTradingEnabled && (!tradingReady || !zerodhaConnected)) {
        showTradingAlert(
            'Trading Not Ready',
            'Please complete Zerodha setup first to start trading, or enable Paper Trading mode to practice with virtual money.',
            true
        );
        return;
    }
    
    // Show immediate loading feedback
    const loadingToast = showLoadingToast(`🔄 Placing ${optionType} ${strike} buy order...`);
    
    try {
        const response = await fetch('/api/buy-option', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                strike: strike,
                option_type: optionType,
                price: price,
                lots: lots,
                symbol: currentSymbol,
                expiry: currentExpiry
            })
        });
        
        const data = await response.json();
        
        // Hide loading toast
        hideLoadingToast(loadingToast);
        
        if (data.success) {
            // Show detailed success notification
            const orderDetails = {
                strike: strike,
                optionType: optionType,
                price: price,
                lots: lots,
                orderId: data.order_id,
                cost: data.cost || (price * lots * getLotSize(currentSymbol))
            };
            
            showOrderSuccessNotification('BUY', orderDetails);
            
            // Auto-refresh positions and trade history
            setTimeout(() => {
                loadPositions();
                loadTradeHistory();
            }, 1000);
            
            // Trigger sound notification
            playNotificationSound('success');
            
        } else {
            showOrderErrorNotification('BUY', {
                strike: strike,
                optionType: optionType,
                error: data.message
            });
            playNotificationSound('error');
        }
    } catch (error) {
        // Hide loading toast
        hideLoadingToast(loadingToast);
        
        console.error('Error buying option:', error);
        showOrderErrorNotification('BUY', {
            strike: strike,
            optionType: optionType,
            error: 'Network error - please check connection'
        });
        playNotificationSound('error');
    }
}

async function sellOption(strike, optionType, price) {
    // Check if trading is ready (paper trading or live trading with Zerodha)
    if (!window.paperTradingEnabled && (!tradingReady || !zerodhaConnected)) {
        showTradingAlert(
            'Trading Not Ready',
            'Please complete Zerodha setup first to start trading, or enable Paper Trading mode to practice with virtual money.',
            true
        );
        return;
    }
    
    // Show immediate loading feedback
    const loadingToast = showLoadingToast(`🔄 Placing ${optionType} ${strike} sell order...`);
    
    try {
        const response = await fetch('/api/sell-option', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                strike: strike,
                option_type: optionType,
                price: price,
                symbol: currentSymbol,
                expiry: currentExpiry
            })
        });
        
        const data = await response.json();
        
        // Hide loading toast
        hideLoadingToast(loadingToast);
        
        if (data.success) {
            // Show detailed success notification
            const orderDetails = {
                strike: strike,
                optionType: optionType,
                price: price,
                orderId: data.order_id,
                pnl: data.pnl
            };
            
            showOrderSuccessNotification('SELL', orderDetails);
            
            // Auto-refresh positions and trade history
            setTimeout(() => {
                loadPositions();
                loadTradeHistory();
            }, 1000);
            
            // Trigger sound notification
            playNotificationSound('success');
            
        } else {
            showOrderErrorNotification('SELL', {
                strike: strike,
                optionType: optionType,
                error: data.message
            });
            playNotificationSound('error');
        }
    } catch (error) {
        // Hide loading toast
        hideLoadingToast(loadingToast);
        
        console.error('Error selling option:', error);
        showOrderErrorNotification('SELL', {
            strike: strike,
            optionType: optionType,
            error: 'Network error - please check connection'
        });
        playNotificationSound('error');
    }
}

async function loadPositions() {
    try {
        const response = await fetch('/api/positions');
        const data = await response.json();
        updatePositions(data);
    } catch (error) {
        console.error('Error loading positions:', error);
    }
}

// Store last known positions for comparison
let lastPositionsData = [];

// --- updatePositions - Optimized for live updates ---
function updatePositions(data) {
    const container = document.getElementById('positionsTable');
    if (!container) return;
    
    // Handle different response formats
    let positions = [];
    if (data && data.success && Array.isArray(data.positions)) {
        positions = data.positions;
    } else if (Array.isArray(data)) {
        positions = data;
    } else {
        console.log('No positions data or unexpected format:', data);
        container.innerHTML = '<div class="info-message">No open positions</div>';
        return;
    }
    
    if (positions.length === 0) {
        container.innerHTML = '<div class="info-message">No open positions</div>';
        lastPositionsData = [];
        return;
    }
    
    // Only show positions with quantity > 0 OR positions waiting for auto-buy
    const filtered = positions.filter(pos => {
        const qty = pos.qty !== undefined ? pos.qty : pos.quantity;
        return qty > 0 || pos.waiting_for_autobuy === true;
    });
    
    // Check if we need to rebuild the entire table (structure changed)
    const needsRebuild = hasStructureChanged(lastPositionsData, filtered);
    
    if (needsRebuild) {
        // Full rebuild only when structure changes
        buildCompleteTable(container, filtered);
    } else {
        // Quick update of dynamic values only
        updateDynamicValues(filtered);
    }
    
    // Store current data for next comparison
    lastPositionsData = JSON.parse(JSON.stringify(filtered));
    
    // Always update cooldown controls to ensure sold positions are removed
    updateCooldownControls(filtered);
}

// Check if table structure has changed (positions added/removed)
function hasStructureChanged(oldPositions, newPositions) {
    if (oldPositions.length !== newPositions.length) {
        console.log(`🔄 Structure changed: position count ${oldPositions.length} → ${newPositions.length}`);
        return true;
    }
    
    // Check if same positions exist
    for (let i = 0; i < newPositions.length; i++) {
        const newPos = newPositions[i];
        const newKey = getPositionKey(newPos);
        
        const oldPos = oldPositions.find(p => getPositionKey(p) === newKey);
        if (!oldPos) {
            console.log(`🔄 Structure changed: new position ${newKey}`);
            return true;
        }
        
        // Check if status changed (waiting_for_autobuy, sold, etc.)
        // Explicitly cast to boolean to avoid undefined vs false issues
        if (!!oldPos.waiting_for_autobuy !== !!newPos.waiting_for_autobuy) {
            console.log(`🔄 Structure changed: ${newKey} waiting status changed (Auto Buy Triggered)`);
            return true;
        }
        
        // Check if stop loss changed significantly (might indicate manual update)
        const oldSL = oldPos.stop_loss_price || oldPos.stop_loss || 0;
        const newSL = newPos.stop_loss_price || newPos.stop_loss || 0;
        if (Math.abs(oldSL - newSL) > 5) {
            console.log(`🔄 Structure changed: ${newKey} stop loss changed significantly ${oldSL} → ${newSL}`);
            return true;
        }
    }
    
    return false;
}

// Get unique key for position
function getPositionKey(pos) {
    // Try multiple approaches to create a consistent key
    if (pos.tradingsymbol) {
        return pos.tradingsymbol;
    } else if (pos.strike && (pos.type || pos.option_type)) {
        const strike = pos.strike;
        const type = pos.type || pos.option_type;
        
        // Handle different formats that might come from the server
        // If strike is a number, format it consistently
        let formattedStrike = strike;
        if (typeof strike === 'number') {
            // If it's a whole number, don't include .0
            formattedStrike = strike % 1 === 0 ? parseInt(strike) : strike;
        }
        
        // Generate key in the format that matches the frontend display
        // This should match how the symbol is displayed in the table
        return `${type}${formattedStrike}`;
    } else if (pos.symbol) {
        return pos.symbol;
    } else if (pos.id) {
        return pos.id;
    } else {
        // Fallback - create key from available data
        const strike = pos.strike || 'unknown';
        const type = pos.type || pos.option_type || 'unknown';
        return `${type}${strike}`;
    }
}

// Build complete table (only when structure changes)
function buildCompleteTable(container, positions) {
    console.log('🔄 Rebuilding positions table structure');
    
    // Table header
    let html = `
        <div class="position-row position-header">
            <div>Symbol</div>
            <div>Qty</div>
            <div>Avg Buy ₹</div>
            <div>Current ₹</div>
            <div>P&L ₹</div>
            <div>Stop Loss</div>
            <div>Realized P&L</div>
            <div>Exchange</div>
            <div>Product</div>
            <div>Auto Buy Count</div>
            <div>Sell</div>
        </div>
    `;
    
    positions.forEach((pos, index) => {
        const positionKey = getPositionKey(pos);
        const rowId = `pos-row-${positionKey.replace(/[^a-zA-Z0-9]/g, '_')}`;
        
        // Calculate initial values
        let pnl = calculatePnL(pos);
        const pnlClass = pnl > 0 ? 'profit' : pnl < 0 ? 'loss' : '';
        
        // Get symbol and sell parameters
        const symbolData = getSymbolAndSellParams(pos);
        
        html += `
            <div id="${rowId}" class="position-row ${pnlClass}" data-symbol="${pos.tradingsymbol || symbolData.symbol}" data-position-key="${positionKey}">
                <div class="symbol-cell" title="${pos.tradingsymbol || symbolData.symbol}">${symbolData.symbol}</div>
                <div class="qty-cell">${pos.waiting_for_autobuy ? (pos.original_quantity || 0) : (pos.quantity !== undefined ? pos.quantity : pos.qty || '-')}</div>
                <div class="avg-price-cell">₹${pos.average_price !== undefined ? Number(pos.average_price).toFixed(2) : pos.buy_price !== undefined ? Number(pos.buy_price).toFixed(2) : '-'}</div>
                <div class="current-price-cell">₹${pos.last_price !== undefined ? Number(pos.last_price).toFixed(2) : pos.current_price !== undefined ? Number(pos.current_price).toFixed(2) : '-'}</div>
                <div class="pnl-cell ${pnlClass}">₹${pnl !== undefined ? Number(pnl).toFixed(2) : '-'}</div>
                <div class="stop-loss-cell" style="color: #ff6b6b; font-weight: bold;">${getStopLossDisplay(pos)}</div>
                <div class="realized-pnl-cell">₹${pos.realized_pnl !== undefined ? Number(pos.realized_pnl).toFixed(2) : '-'}</div>
                <div class="exchange-cell">${pos.exchange || 'NFO'}</div>
                <div class="product-cell">${pos.waiting_for_autobuy ? '<span style="color: #ff9800; font-weight: bold;">PENDING</span>' : (pos.product || pos.type || '-')}</div>
                <div class="auto-buy-count-cell" style="color: #ff9800; font-weight: bold;">${pos.auto_buy_count !== undefined ? pos.auto_buy_count : 0}</div>
                <div class="sell-cell">${getSellButtonHtml(pos, symbolData)}</div>
            </div>
        `;
    });
    
    container.innerHTML = html;
    
    // Attach event handlers to sell buttons
    attachSellButtonHandlers();
}

// Update only dynamic values (prices, PnL) - FAST UPDATE
function updateDynamicValues(positions) {
    positions.forEach(pos => {
        const positionKey = getPositionKey(pos);
        const rowId = `pos-row-${positionKey.replace(/[^a-zA-Z0-9]/g, '_')}`;
        const row = document.getElementById(rowId);
        
        if (!row) return; // Row doesn't exist, will be handled in next full rebuild
        
        // --- Update Quantity (Crucial for Auto Buy transition) ---
        const qtyCell = row.querySelector('.qty-cell');
        if (qtyCell) {
            // Determine correct quantity to display
            const displayQty = pos.waiting_for_autobuy ? (pos.original_quantity || 0) : (pos.quantity !== undefined ? pos.quantity : pos.qty || '-');
            
            // Only update if changed
            if (qtyCell.textContent != displayQty) {
                console.log(`⚡ Fast Update: Quantity changed for ${positionKey} (${qtyCell.textContent} -> ${displayQty})`);
                qtyCell.textContent = displayQty;
                // Green flash effect for auto-buy visual feedback
                qtyCell.style.backgroundColor = '#d4edda'; 
                setTimeout(() => { qtyCell.style.backgroundColor = ''; }, 1000);
            }
        }

        // ---  Update Product/Status Cell (Remove "PENDING" text) ---
        const productCell = row.querySelector('.product-cell');
        if (productCell) {
            const newContent = pos.waiting_for_autobuy ? '<span style="color: #ff9800; font-weight: bold;">PENDING</span>' : (pos.product || pos.type || '-');
            if (productCell.innerHTML !== newContent) {
                productCell.innerHTML = newContent;
            }
        }

        // --- Update Sell Button (Switch "Cancel" -> "Sell") ---
        const sellCell = row.querySelector('.sell-cell');
        if (sellCell) {
             // Check if state changed from waiting to active (or vice versa)
             // We store the state in a data attribute to check against new state
             const wasWaiting = row.getAttribute('data-waiting') === 'true';
             const isWaiting = !!pos.waiting_for_autobuy;

             if (wasWaiting !== isWaiting) {
                 console.log(`⚡ Fast Update: Switching buttons for ${positionKey}`);
                 // Get symbol data needed for button generation
                 const symbolData = getSymbolAndSellParams(pos);
                 const newButtonHtml = getSellButtonHtml(pos, symbolData);
                 
                 sellCell.innerHTML = newButtonHtml;
                 row.setAttribute('data-waiting', isWaiting);
                 
                 // Re-attach handlers for this specific row since we replaced innerHTML
                 attachSellButtonHandlers(); 
             }
        }

        

        // Update current price
        const currentPriceCell = row.querySelector('.current-price-cell');
        if (currentPriceCell) {
            const currentPrice = pos.last_price !== undefined ? Number(pos.last_price) : pos.current_price !== undefined ? Number(pos.current_price) : 0;
            const newPriceText = `₹${currentPrice.toFixed(2)}`;
            
            // Only update if changed (performance optimization)
            if (currentPriceCell.textContent !== newPriceText) {
                currentPriceCell.textContent = newPriceText;
                // Flash animation for price change
                currentPriceCell.style.background = '#fffacd';
                setTimeout(() => {
                    currentPriceCell.style.background = '';
                }, 300);
            }
        }
        
        // Update P&L and row class
        const pnl = calculatePnL(pos);
        const pnlClass = pnl > 0 ? 'profit' : pnl < 0 ? 'loss' : '';
        
        const pnlCell = row.querySelector('.pnl-cell');
        if (pnlCell) {
            const newPnlText = `₹${pnl !== undefined ? Number(pnl).toFixed(2) : '-'}`;
            if (pnlCell.textContent !== newPnlText) {
                pnlCell.textContent = newPnlText;
                pnlCell.className = `pnl-cell ${pnlClass}`;
            }
        }
        
        // Update row class for profit/loss styling
        row.className = `position-row ${pnlClass}`;
        
        // Update stop loss if it changed (but preserve user input state)
        const stopLossCell = row.querySelector('.stop-loss-cell');
        if (stopLossCell) {
            const currentInput = stopLossCell.querySelector('.stop-loss-input');
            let needsUpdate = false;
            
            // Get current stop loss value from position data
            let newStopLossValue = 0;
            if (pos.stop_loss_price !== undefined && pos.stop_loss_price !== null && pos.stop_loss_price !== 'No SL' && pos.stop_loss_price !== '-') {
                // Extract numeric value if it's a string like "₹204.80"
                if (typeof pos.stop_loss_price === 'string') {
                    const match = pos.stop_loss_price.match(/[\d.]+/);
                    newStopLossValue = match ? Number(match[0]) : 0;
                } else {
                    newStopLossValue = Number(pos.stop_loss_price);
                }
            } else if (pos.stop_loss !== undefined && pos.stop_loss !== null && pos.stop_loss > 0) {
                newStopLossValue = Number(pos.stop_loss);
            }
            
            // Handle stop loss updates more carefully
            if (currentInput && newStopLossValue > 0) {
                const currentInputValue = parseFloat(currentInput.value) || 0;
                const originalValue = parseFloat(currentInput.getAttribute('data-original-value')) || 0;
                
                // Check if user recently updated the value (don't override immediately)
                const inputChangedRecently = Math.abs(currentInputValue - originalValue) > 0.01;
                const algorithmWantsChange = Math.abs(newStopLossValue - currentInputValue) > 0.5; // Increased threshold to avoid flicker
                
                // Always update the original value to match server data
                currentInput.setAttribute('data-original-value', newStopLossValue.toFixed(2));
                
                if (algorithmWantsChange && !inputChangedRecently) {
                    // Algorithm changed stop loss and user hasn't made recent changes
                    currentInput.value = newStopLossValue.toFixed(2);
                    
                    // Subtle visual feedback that algorithm updated it
                    currentInput.style.borderColor = '#28a745'; // Green border
                    setTimeout(() => {
                        currentInput.style.borderColor = '#ddd';
                    }, 1000);
                } else if (!inputChangedRecently && currentInputValue === 0) {
                    // Initial load - set the value
                    currentInput.value = newStopLossValue.toFixed(2);
                }
            } else if (!currentInput || newStopLossValue === 0) {
                // No input exists or no stop loss - rebuild this cell
                needsUpdate = true;
            }
            
            if (needsUpdate) {
                stopLossCell.innerHTML = getStopLossDisplay(pos);
                // Reattach handlers for this specific cell
                attachStopLossHandlersForCell(stopLossCell);
            }
        }
        
        // Update auto buy count
        const autoBuyCountCell = row.querySelector('.auto-buy-count-cell');
        if (autoBuyCountCell) {
            autoBuyCountCell.textContent = pos.auto_buy_count !== undefined ? pos.auto_buy_count : 0;
        }
        
        // Update realized P&L
        const realizedPnLCell = row.querySelector('.realized-pnl-cell');
        if (realizedPnLCell) {
            realizedPnLCell.textContent = `₹${pos.realized_pnl !== undefined ? Number(pos.realized_pnl).toFixed(2) : '-'}`;
        }
    });
}

// Helper functions
function calculatePnL(pos) {
    let pnl = pos.pnl;
    if (pnl === undefined) pnl = pos.current_pnl;
    if (pnl === undefined && pos.last_price !== undefined && pos.average_price !== undefined && pos.quantity !== undefined) {
        pnl = (Number(pos.last_price) - Number(pos.average_price)) * Number(pos.quantity);
    }
    return pnl;
}

function getStopLossDisplay(pos) {
    const positionKey = getPositionKey(pos);
    const stopLossId = `sl-input-${positionKey.replace(/[^a-zA-Z0-9]/g, '_')}`;
    
    // 🔥 FIXED: Parse stop loss from string or number
    let stopLossValue = 0;
    
    // Try stop_loss_price first (can be string like "₹204.80" or number)
    if (pos.stop_loss_price !== undefined && pos.stop_loss_price !== null && 
        pos.stop_loss_price !== 'No SL' && pos.stop_loss_price !== '-') {
        
        if (typeof pos.stop_loss_price === 'string') {
            // Extract number from string like "₹204.80"
            const match = pos.stop_loss_price.match(/[\d.]+/);
            stopLossValue = match ? parseFloat(match[0]) : 0;
        } else {
            stopLossValue = Number(pos.stop_loss_price);
        }
    }
    
    // Fallback to stop_loss field
    if (stopLossValue === 0 && pos.stop_loss !== undefined && pos.stop_loss !== null && pos.stop_loss > 0) {
        if (typeof pos.stop_loss === 'string') {
            const match = pos.stop_loss.match(/[\d.]+/);
            stopLossValue = match ? parseFloat(match[0]) : 0;
        } else {
            stopLossValue = Number(pos.stop_loss);
        }
    }
    
    // 🔥 DEBUG: Log what we received
    if (stopLossValue === 0) {
        console.log(`⚠️ No valid stop loss for ${pos.tradingsymbol || pos.strike}:`, {
            stop_loss_price: pos.stop_loss_price,
            stop_loss: pos.stop_loss,
            parsed: stopLossValue
        });
    }
    
    if (stopLossValue > 0) {
        return `
            <div class="stop-loss-container" style="display: flex; align-items: center; gap: 3px; min-width: 120px;">
                <span style="color: #ff6b6b; font-weight: bold; font-size: 13px;">₹</span>
                <input type="number" 
                       id="${stopLossId}" 
                       class="stop-loss-input" 
                       value="${stopLossValue.toFixed(2)}" 
                       min="0" 
                       step="0.05"
                       data-position-key="${positionKey}"
                       data-original-value="${stopLossValue.toFixed(2)}"
                       style="width: 75px; padding: 4px 6px; border: 1px solid #ddd; border-radius: 4px; font-size: 13px; font-weight: 600; background: #f9f9f9; text-align: center; color: #333;"
                       title="Click to edit stop loss (Algorithm will override when conditions are met)">
                <button class="update-sl-btn" 
                        data-position-key="${positionKey}" 
                        data-input-id="${stopLossId}"
                        style="padding: 4px 7px; font-size: 12px; font-weight: bold; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; min-width: 24px; height: 28px; display: flex; align-items: center; justify-content: center;"
                        title="Update stop loss">✓</button>
            </div>
        `;
    } else if (pos.tradingsymbol) {
        return '<span style="color: #ff9800; font-size: 13px; font-weight: 600;">No SL</span>';
    }
    return '<span style="font-size: 13px; color: #666;">-</span>';
}

function getSymbolAndSellParams(pos) {
    let symbol = pos.tradingsymbol || pos.symbol || '-';
    let sellStrike = pos.strike;
    let sellOptionType = pos.type || pos.option_type;
    
    // For Zerodha positions, extract strike and option type from tradingsymbol
    if (pos.tradingsymbol && !sellStrike) {
        const match = pos.tradingsymbol.match(/(\d+)(CE|PE)$/);
        if (match) {
            sellStrike = parseInt(match[1]);
            sellOptionType = match[2];
        }
    }
    
    // Create consistent symbol format
    if (pos.strike && (pos.type || pos.option_type)) {
        const strike = pos.strike;
        const type = pos.type || pos.option_type;
        
        // Format strike consistently (remove .0 for whole numbers)
        let formattedStrike = strike;
        if (typeof strike === 'number') {
            formattedStrike = strike % 1 === 0 ? parseInt(strike) : strike;
        }
        
        symbol = `${type}${formattedStrike}`;
    }
    
    return { symbol, sellStrike, sellOptionType };
}

function getSellButtonHtml(pos, symbolData) {
    const sellPrice = pos.last_price !== undefined ? Number(pos.last_price) : pos.current_price !== undefined ? Number(pos.current_price) : 0;
    
    if (pos.waiting_for_autobuy) {
        // Create position key for cancel button - try multiple approaches
        let positionKey = pos.id; // First try ID if available
        
        if (!positionKey && pos.strike && (pos.type || pos.option_type)) {
            // Use strike-type format
            positionKey = `${pos.strike}-${pos.type || pos.option_type}`;
        }
        
        if (!positionKey && (pos.tradingsymbol || pos.symbol)) {
            // Extract from symbol like "CE56800" -> "56800-CE"
            const symbol = pos.tradingsymbol || pos.symbol;
            const match = symbol.match(/([CP]E)(\d+)/);
            if (match) {
                const type = match[1];
                const strike = match[2];
                positionKey = `${strike}-${type}`;
            }
        }
        
        if (!positionKey) {
            // Fallback - use symbol as key
            positionKey = pos.tradingsymbol || pos.symbol || 'unknown';
        }
        
        console.log(`🔑 Generated position key for cancel: ${positionKey} from`, pos);
        return `<button class="btn btn-warning btn-sm cancel-pending-btn" data-position-key="${positionKey}" title="Cancel pending auto-buy/sell">Cancel</button>`;
    } else if (symbolData.sellStrike && symbolData.sellOptionType && sellPrice > 0) {
        return `<button class="btn btn-danger btn-sm sell-position-btn" data-strike="${symbolData.sellStrike}" data-option-type="${symbolData.sellOptionType}" data-price="${sellPrice}" title="Sell ${symbolData.sellStrike} ${symbolData.sellOptionType}">Sell</button>`;
    } else if (pos.tradingsymbol) {
        const currentPrice = pos.last_price || pos.ltp || pos.average_price || 0;
        return `<button class="btn btn-warning btn-sm manual-sell-btn" data-symbol="${pos.tradingsymbol}" data-price="${currentPrice}" title="Manual sell ${pos.tradingsymbol}">Manual</button>`;
    } else {
        return `<button class="btn btn-secondary btn-sm" disabled title="Cannot determine sell parameters">N/A</button>`;
    }
}

// Attach stop loss handlers for specific cell (used during dynamic updates)
function attachStopLossHandlersForCell(cell) {
    const updateBtn = cell.querySelector('.update-sl-btn');
    const input = cell.querySelector('.stop-loss-input');
    
    if (updateBtn) {
        updateBtn.addEventListener('click', function() {
            const positionKey = this.getAttribute('data-position-key');
            const inputId = this.getAttribute('data-input-id');
            updateManualStopLoss(positionKey, inputId);
        });
    }
    
    if (input) {
        input.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                const positionKey = this.getAttribute('data-position-key');
                const inputId = this.id;
                updateManualStopLoss(positionKey, inputId);
            }
        });
        
        input.addEventListener('input', function() {
            const value = parseFloat(this.value);
            const originalValue = parseFloat(this.getAttribute('data-original-value'));
            
            if (Math.abs(value - originalValue) > 0.01) {
                this.style.background = '#fff3cd';
                this.style.borderColor = '#ffc107';
            } else {
                this.style.background = '#f9f9f9';
                this.style.borderColor = '#ddd';
            }
        });
    }
}

// Attach event handlers to sell buttons and stop loss inputs (called after full rebuild)
function attachSellButtonHandlers() {
    // Handle regular sell buttons
    document.querySelectorAll('.sell-position-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const strike = this.getAttribute('data-strike');
            const optionType = this.getAttribute('data-option-type');
            const price = this.getAttribute('data-price');
            sellPosition(parseInt(strike), optionType, parseFloat(price));
        });
    });
    
    // Handle manual sell buttons
    document.querySelectorAll('.manual-sell-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const symbol = this.getAttribute('data-symbol');
            const price = this.getAttribute('data-price');
            manualSell(symbol, parseFloat(price));
        });
    });
    
    // Handle cancel pending buttons
    document.querySelectorAll('.cancel-pending-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const positionKey = this.getAttribute('data-position-key');
            // Disable button immediately to prevent double-requests
            this.disabled = true;
            this.innerText = 'Cancelling...';
            cancelPendingPosition(positionKey).then(() => {
                // nothing here, server will emit updates
            }).catch(() => {
                // Re-enable on error
                this.disabled = false;
                this.innerText = 'Cancel';
            });
        });
    });
    
    // Handle cancel pending buttons
    document.querySelectorAll('.cancel-pending-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const positionKey = this.getAttribute('data-position-key');
            cancelPendingPosition(positionKey);
        });
    });
    
    // Handle stop loss update buttons
    document.querySelectorAll('.update-sl-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const positionKey = this.getAttribute('data-position-key');
            const inputId = this.getAttribute('data-input-id');
            updateManualStopLoss(positionKey, inputId);
        });
    });
    
    // Handle Enter key press on stop loss inputs
    document.querySelectorAll('.stop-loss-input').forEach(input => {
        input.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                const positionKey = this.getAttribute('data-position-key');
                const inputId = this.id;
                updateManualStopLoss(positionKey, inputId);
            }
        });
        
        // Handle input validation
        input.addEventListener('input', function() {
            const value = parseFloat(this.value);
            const originalValue = parseFloat(this.getAttribute('data-original-value'));
            
            // Change input style based on whether value changed
            if (Math.abs(value - originalValue) > 0.01) {
                this.style.background = '#fff3cd'; // Light yellow background for changed value
                this.style.borderColor = '#ffc107'; // Yellow border
            } else {
                this.style.background = '#f9f9f9'; // Original background
                this.style.borderColor = '#ddd'; // Original border
            }
        });
    });
}

function updateCooldownControls(positions) {
    const container = document.getElementById('cooldownControlsTable');
    if (!container) return;
    
    if (!positions || positions.length === 0) {
        container.innerHTML = `
            <div class="cooldown-control-row cooldown-control-header">
                <div>Symbol</div>
                <div>Strike & Type</div>
                <div>Status</div>
                <div>Cooldown Toggle</div>
            </div>
            <div class="info-message">
                <i class="fas fa-info-circle"></i>
                No positions available for cooldown control
            </div>
        `;
        // Clear recent toggle states when no positions
        Object.keys(recentToggleStates).forEach(key => {
            delete recentToggleStates[key];
        });
        return;
    }
    
    // Create a set of current position keys to check if position still exists
    const currentPositionKeys = new Set();
    const currentPositionButtonIds = new Set();
    positions.forEach(pos => {
        const positionKey = `${pos.id || pos.strike}-${pos.type || pos.option_type}`;
        const positionId = pos.id || `${pos.strike}-${pos.type || pos.option_type}`;
        const cooldownToggleId = `cooldown-control-${positionId}`;
        currentPositionKeys.add(positionKey);
        currentPositionButtonIds.add(cooldownToggleId);
    });
    
    // Store current button states only for positions that still exist
    const currentButtonStates = {};
    const existingButtons = container.querySelectorAll('.cooldown-control-btn');
    existingButtons.forEach(btn => {
        const btnId = btn.id;
        if (btnId && currentPositionButtonIds.has(btnId)) {
            const isOn = btn.classList.contains('cooldown-btn-on');
            currentButtonStates[btnId] = isOn;
            console.log(`💾 Stored button state for existing position ${btnId}: ${isOn}`);
        } else if (btnId) {
            console.log(`🗑️ Ignoring button state for removed position ${btnId}`);
        }
    });
    
    // Clean up recent toggle states for positions that no longer exist
    Object.keys(recentToggleStates).forEach(key => {
        if (!currentPositionKeys.has(key)) {
            delete recentToggleStates[key];
            console.log(`🧹 Removed recent toggle state for sold position: ${key}`);
        }
    });
    
    let html = `
        <div class="cooldown-control-row cooldown-control-header">
            <div>Symbol</div>
            <div>Strike & Type</div>
            <div>Status</div>
            <div>Cooldown Toggle</div>
        </div>
    `;
    
    positions.forEach(pos => {
        const symbol = pos.tradingsymbol || `${pos.strike}${pos.type || pos.option_type}` || '-';
        const strikeType = `${pos.strike} ${pos.type || pos.option_type}`;
        
        // Static status - not dependent on auto_buy_count to reduce updates
        let status = 'Active';
        let statusClass = 'status-running';
        
        // Check if this position has a recent toggle state that should override backend data
        const positionKey = `${pos.id || pos.strike}-${pos.type || pos.option_type}`;
        let individualCooldownEnabled = pos.individual_cooldown_enabled !== undefined ? pos.individual_cooldown_enabled : true;
        
        // If we have a recent toggle state, use that instead of backend data
        if (recentToggleStates[positionKey] !== undefined) {
            individualCooldownEnabled = recentToggleStates[positionKey];
            console.log(`🔄 Using recent toggle state for ${positionKey}: ${individualCooldownEnabled}`);
        }
        
        const positionId = pos.id || `${pos.strike}-${pos.type || pos.option_type}`;
        const cooldownToggleId = `cooldown-control-${positionId}`;
        
        // Check if we had a previous button state and preserve it (only for existing positions)
        if (currentButtonStates[cooldownToggleId] !== undefined) {
            individualCooldownEnabled = currentButtonStates[cooldownToggleId];
            console.log(`🔄 Preserving existing button state for ${cooldownToggleId}: ${individualCooldownEnabled}`);
        }
        
        html += `
            <div class="cooldown-control-row">
                <div class="symbol-cell">${symbol}</div>
                <div class="strike-type-cell">${strikeType}</div>
                <div class="status-cell ${statusClass}">${status}</div>
                <div class="cooldown-control-button-container">
                    <button class="cooldown-control-btn ${individualCooldownEnabled ? 'cooldown-btn-on' : 'cooldown-btn-off'}" 
                            id="${cooldownToggleId}" 
                            onclick="toggleIndividualCooldownButton('${pos.id || ''}', '${pos.strike}', '${pos.type || pos.option_type}', ${individualCooldownEnabled}, this)">
                        <span class="cooldown-btn-icon">${individualCooldownEnabled ? '🔴' : '🟢'}</span>
                        <span class="cooldown-btn-text">${individualCooldownEnabled ? 'ON' : 'OFF'}</span>
                    </button>
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

// Manual Stop Loss Update Function
async function updateManualStopLoss(positionKey, inputId) {
    const input = document.getElementById(inputId);
    if (!input) return;
    
    const newStopLoss = parseFloat(input.value);
    const originalValue = parseFloat(input.getAttribute('data-original-value'));
    
    console.log(`🔧 Updating stop loss: ${positionKey} -> ₹${newStopLoss}`);
    
    // Validate input
    if (isNaN(newStopLoss) || newStopLoss <= 0) {
        showToast('Please enter a valid stop loss price', 'error');
        input.value = originalValue.toFixed(2);
        return;
    }
    
    // Check if value actually changed
    if (Math.abs(newStopLoss - originalValue) < 0.01) {
        showToast('Stop loss value unchanged', 'info');
        return;
    }
    
    try {
        // Show loading state
        input.disabled = true;
        input.style.background = '#e9ecef';
        
        console.log(`📤 Sending request: position_key=${positionKey}, new_stop_loss=${newStopLoss}`);
        
        const response = await fetch('/api/update-manual-stop-loss', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                position_key: positionKey,
                new_stop_loss: newStopLoss
            })
        });
        
        const data = await response.json();
        console.log(`📥 Response:`, data);
        
        if (data.success) {
            showToast(data.message || `Stop loss updated to ₹${newStopLoss.toFixed(2)}`, 'success');
            
            // Update the original value to prevent unnecessary API calls
            input.setAttribute('data-original-value', newStopLoss.toFixed(2));
            input.style.background = '#d4edda'; // Light green for success
            input.style.borderColor = '#28a745'; // Green border
            
            // Reset style after 2 seconds
            setTimeout(() => {
                input.style.background = '#f9f9f9';
                input.style.borderColor = '#ddd';
            }, 2000);
            
            // Refresh positions to get updated data
            setTimeout(() => {
                loadPositions();
            }, 500);
            
        } else {
            showToast(data.message || 'Failed to update stop loss', 'error');
            // Reset to original value
            input.value = originalValue.toFixed(2);
            input.style.background = '#f8d7da'; // Light red for error
            input.style.borderColor = '#dc3545'; // Red border
        }
        
    } catch (error) {
        console.error('Error updating stop loss:', error);
        showToast('Network error while updating stop loss', 'error');
        // Reset to original value
        input.value = originalValue.toFixed(2);
        input.style.background = '#f8d7da';
        input.style.borderColor = '#dc3545';
    } finally {
        // Re-enable input
        input.disabled = false;
    }
}

async function sellPosition(strike, optionType, price) {
    console.log(`Selling position: ${strike} ${optionType} @ ₹${price}`);
    await sellOption(strike, optionType, price);
}

async function manualSell(tradingsymbol, currentPrice = 0) {
    const confirmed = confirm(`Are you sure you want to sell ${tradingsymbol}?`);
    if (!confirmed) return;
    
    try {
        const response = await fetch('/api/sell-individual-position', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                tradingsymbol: tradingsymbol,
                current_price: currentPrice
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast(data.message, 'success');
            // Update wallet info if paper trading
            if (data.mode === 'paper') {
                updateWalletInfo();
            }
            // Refresh positions after successful sell
            setTimeout(() => {
                loadPositions();
            }, 1000);
        } else {
            showToast(data.message, 'error');
        }
    } catch (error) {
        console.error('Error in manual sell:', error);
        showToast('Failed to sell position', 'error');
    }
}

// Cancel pending position (stop auto buy/sell)
async function cancelPendingPosition(positionKey) {
    if (!positionKey) return;
    const confirmed = confirm('Are you sure you want to cancel this pending position? This will prevent further auto buy/sell for this position.');
    if (!confirmed) return;

    try {
        const resp = await fetch('/api/cancel-pending-position', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ position_key: positionKey })
        });
        const data = await resp.json();
        if (data.success) {
            showToast(data.message, 'success');
            setTimeout(() => { window.location.reload(); }, 800);
        } else {
            console.error('Cancel failed:', data);
            let msg = data.message || 'Failed to cancel pending position';
            if (data.available_keys) msg += '\nAvailable keys: ' + data.available_keys.join(', ');
            showToast(msg, 'error');
        }
    } catch (err) {
        console.error('Network error cancelling pending position:', err);
        showToast('Network error cancelling pending position', 'error');
    }
}

// 🚨 Cancel pending position (stop auto buy/sell)
async function cancelPendingPosition(positionKey) {
    if (!positionKey) return;
    
    const confirmed = confirm('Are you sure you want to cancel this pending position? This will prevent further auto buy/sell for this position.');
    if (!confirmed) return;
    
    try {
        const response = await fetch('/api/cancel-pending-position', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ position_key: positionKey })
        });
        const data = await response.json();
        if (data.success) {
            showToast(data.message, 'success');
            setTimeout(() => {
                loadPositions();
            }, 1000);
        } else {
            showToast(data.message, 'error');
        }
    } catch (error) {
        console.error('Error cancelling pending position:', error);
        showToast('Failed to cancel pending position', 'error');
    }
}

async function sellAllPositions() {
    if (!confirm('Are you sure you want to sell all positions?')) {
        return;
    }
    
    try {
        const response = await fetch('/api/sell-all-positions', {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast(`All positions sold! Proceeds: ₹${formatNumber(data.proceeds)}`, 'success');
        } else {
            showToast('Failed to sell all positions', 'error');
        }
    } catch (error) {
        console.error('Error selling all positions:', error);
        showToast('Failed to sell all positions', 'error');
    }
}

// Debounce for cooldown toggles to prevent rapid clicking
let toggleDebounce = {};
// Track recent toggle states to prevent refresh conflicts
let recentToggleStates = {};

// Individual Cooldown Button Toggle Function (New Simple Button Approach)
async function toggleIndividualCooldownButton(positionId, strike, optionType, currentState, buttonElement) {
    console.log(`🟡 Button toggle called: positionId=${positionId}, strike=${strike}, optionType=${optionType}, currentState=${currentState}`);
    
    const toggleKey = `${positionId || strike}-${optionType}`;
    const positionKey = `${positionId || strike}-${optionType}`;
    
    // Prevent rapid clicking - debounce for 1 second
    if (toggleDebounce[toggleKey]) {
        console.log('🚫 Button debounced - please wait before clicking again');
        return false;
    }
    
    toggleDebounce[toggleKey] = true;
    
    // Disable button temporarily
    if (buttonElement) {
        buttonElement.disabled = true;
        buttonElement.innerHTML = '<span class="cooldown-btn-icon">⏳</span><span class="cooldown-btn-text">WAIT</span>';
    }
    
    // Set expected new state immediately in recentToggleStates
    const expectedNewState = !currentState;
    recentToggleStates[positionKey] = expectedNewState;
    console.log(`🔄 Set recent toggle state for ${positionKey}: ${expectedNewState}`);
    
    // Clear the recent toggle state after 10 seconds to allow backend data to take over
    setTimeout(() => {
        delete recentToggleStates[positionKey];
        console.log(`🧹 Cleared recent toggle state for ${positionKey}`);
    }, 10000);
    
    setTimeout(() => {
        delete toggleDebounce[toggleKey];
        if (buttonElement) {
            buttonElement.disabled = false;
        }
    }, 1000);
    
    try {
        console.log(`🔄 Sending API request to toggle cooldown for ${strike} ${optionType}: Current=${currentState}`);
        
        const requestData = {
            position_id: positionId,
            strike: strike,
            option_type: optionType
        };
        console.log(`📤 Request data:`, requestData);
        
        const response = await fetch('/api/position/toggle-individual-cooldown', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        });
        
        console.log(`📥 Response status: ${response.status}`);
        const data = await response.json();
        console.log(`📥 Response data:`, data);
        
        if (data.success) {
            const newState = data.individual_cooldown_enabled;
            
            // Update the recent toggle state with actual backend response
            recentToggleStates[positionKey] = newState;
            
            // Update button immediately
            if (buttonElement) {
                buttonElement.className = `cooldown-control-btn ${newState ? 'cooldown-btn-on' : 'cooldown-btn-off'}`;
                buttonElement.innerHTML = `
                    <span class="cooldown-btn-icon">${newState ? '🔴' : '🟢'}</span>
                    <span class="cooldown-btn-text">${newState ? 'ON' : 'OFF'}</span>
                `;
                // Update onclick with new state
                buttonElement.setAttribute('onclick', 
                    `toggleIndividualCooldownButton('${positionId}', '${strike}', '${optionType}', ${newState}, this)`);
            }
            
            // Show compact toast notification
            const toggleStatus = newState ? 'enabled' : 'disabled';
            const toggleIcon = newState ? '🔴' : '🟢';
            const compactMessage = `${toggleIcon} ${strike} ${optionType} cooldown ${toggleStatus}`;
            showToast(compactMessage, 'success');
            console.log(`✅ Cooldown toggled: ${data.strike} ${data.option_type} = ${newState ? 'ON' : 'OFF'}`);
            
            // DO NOT refresh immediately - let the periodic refresh handle it
            // The recentToggleStates will preserve the correct state during refresh
            
        } else {
            console.error(`❌ API returned error:`, data.error);
            showToast(data.error || 'Failed to toggle cooldown', 'error');
            
            // Revert the recent toggle state
            delete recentToggleStates[positionKey];
            
            // Reset button to original state
            if (buttonElement) {
                buttonElement.className = `cooldown-control-btn ${currentState ? 'cooldown-btn-on' : 'cooldown-btn-off'}`;
                buttonElement.innerHTML = `
                    <span class="cooldown-btn-icon">${currentState ? '🔴' : '🟢'}</span>
                    <span class="cooldown-btn-text">${currentState ? 'ON' : 'OFF'}</span>
                `;
            }
        }
    } catch (error) {
        console.error('❌ Error toggling cooldown:', error);
        showToast('Failed to toggle cooldown', 'error');
        
        // Revert the recent toggle state
        delete recentToggleStates[positionKey];
        
        // Reset button to original state
        if (buttonElement) {
            buttonElement.className = `cooldown-control-btn ${currentState ? 'cooldown-btn-on' : 'cooldown-btn-off'}`;
            buttonElement.innerHTML = `
                <span class="cooldown-btn-icon">${currentState ? '🔴' : '🟢'}</span>
                <span class="cooldown-btn-text">${currentState ? 'ON' : 'OFF'}</span>
            `;
        }
    }
}

// Individual Cooldown Toggle Function (Old Toggle Switch - keeping for backup)
async function toggleIndividualCooldown(positionId, strike, optionType, enabled, toggleElement) {
    console.log(`🟡 Toggle function called: positionId=${positionId}, strike=${strike}, optionType=${optionType}, enabled=${enabled}`);
    
    const toggleKey = `${positionId || strike}-${optionType}`;
    
    // Prevent rapid clicking - debounce for 1 second
    if (toggleDebounce[toggleKey]) {
        console.log('🚫 Toggle debounced - please wait before clicking again');
        // Revert the toggle immediately if debounced
        if (toggleElement) {
            toggleElement.checked = !enabled;
        }
        return false;
    }
    
    toggleDebounce[toggleKey] = true;
    setTimeout(() => {
        delete toggleDebounce[toggleKey];
    }, 1000);
    
    try {
        console.log(`🔄 Sending API request to toggle individual cooldown for ${strike} ${optionType}: ${enabled ? 'ENABLED' : 'DISABLED'}`);
        
        const requestData = {
            position_id: positionId,
            strike: strike,
            option_type: optionType
        };
        console.log(`📤 Request data:`, requestData);
        
        const response = await fetch('/api/position/toggle-individual-cooldown', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        });
        
        console.log(`📥 Response status: ${response.status}`);
        const data = await response.json();
        console.log(`📥 Response data:`, data);
        
        if (data.success) {
            showToast(data.message, 'success');
            console.log(`✅ Individual cooldown toggled for ${data.strike} ${data.option_type}: ${data.individual_cooldown_enabled ? 'ENABLED' : 'DISABLED'}`);
            
            // Refresh positions and cooldown controls after successful toggle
            setTimeout(() => {
                loadPositions();
            }, 500);
        } else {
            console.error(`❌ API returned error:`, data.error);
            // Revert the toggle if the request failed
            if (toggleElement) {
                toggleElement.checked = !enabled;
            }
            showToast(data.error || 'Failed to toggle individual cooldown', 'error');
        }
    } catch (error) {
        console.error('❌ Error toggling individual cooldown:', error);
        // Revert the toggle if there was an error
        if (toggleElement) {
            toggleElement.checked = !enabled;
        }
        showToast('Failed to toggle individual cooldown', 'error');
    }
}

async function resetStopLoss() {
    showToast('Stop loss reset functionality coming soon', 'info');
}

function handlePositionFilter() {
    // Position filtering logic would go here
    loadPositions();
}

async function loadTradeHistory() {
    try {
        console.log('Loading trade history...'); // Debug log
        const response = await fetch('/api/trade-history');
        const data = await response.json();
        console.log('Trade history response:', data); // Debug log
        updateTradeHistory(data);
    } catch (error) {
        console.error('Error loading trade history:', error);
    }
}

function updateTradeHistory(historyData) {
    // Handle both old and new API response formats
    const trades = historyData.trades || historyData;
    const mode = historyData.trading_mode || historyData.mode || 'Unknown';
    const totalTrades = historyData.total_trades || trades.length;
    
    if (!trades || trades.length === 0) {
        document.getElementById('tradeHistoryList').innerHTML = 
            `<div class="info-message">
                <i class="fas fa-info-circle"></i>
                No ${mode === 'Paper Trading' ? 'paper trading' : 'trading'} history yet
            </div>`;
        updateHistorySummary([]);
        return;
    }
    
    updateHistorySummary(trades, mode, totalTrades);
    
    const container = document.getElementById('tradeHistoryList');
    if (!container) return;
    
    container.innerHTML = '';
    
    // Add trading mode header
    const modeHeader = document.createElement('div');
    modeHeader.className = 'history-mode-header';
    modeHeader.innerHTML = `
        <div class="mode-info">
            <i class="fas ${mode === 'Paper Trading' ? 'fa-clipboard' : 'fa-chart-line'}"></i>
            <span>${mode} History (${totalTrades} trades)</span>
        </div>
    `;
    container.appendChild(modeHeader);
    
    // Show ALL trades in reverse order (most recent first) - no limit
    const recentTrades = trades.slice().reverse();
    
    recentTrades.forEach((trade, index) => {
        const div = document.createElement('div');
        div.className = 'history-item';
        
        // Add trading mode indicator class
        if (trade.trading_mode === 'paper') {
            div.classList.add('paper-trade');
        } else if (trade.trading_mode === 'live') {
            div.classList.add('live-trade');
        }
        
        if (trade.action === 'Buy') {
            div.classList.add('buy');
        } else if (trade.pnl > 0) {
            div.classList.add('profit');
        } else if (trade.pnl < 0) {
            div.classList.add('loss');
        }
        
        const pnlText = trade.action === 'Buy' ? '' : ` | P&L: ₹${trade.pnl.toFixed(2)}`;
        const modeIcon = trade.trading_mode === 'paper' ? 
            '<i class="fas fa-clipboard mode-icon paper-icon" title="Paper Trading"></i>' : 
            '<i class="fas fa-chart-line mode-icon live-icon" title="Live Trading"></i>';
        
        div.innerHTML = `
            <div class="history-header">
                ${getTradeIcon(trade)} ${trade.action} - ${trade.type} ${trade.strike} ${modeIcon}
            </div>
            <div class="history-details">
                Qty: ${trade.qty || trade.quantity || 'N/A'} | Price: ₹${(trade.price || 0).toFixed(2)}${pnlText}<br>
                Time: ${trade.time || trade.timestamp || 'N/A'}
                ${trade.reason ? `<br><small>Reason: ${trade.reason}</small>` : ''}
            </div>
        `;
        
        container.appendChild(div);
    });
}

/**
 * Format a number for display (handles undefined/null/NaN gracefully).
 * @param {number} num
 * @returns {string}
 */
function formatNumber(num) {
    if (num === undefined || num === null || isNaN(num)) return '0.00';
    if (num >= 10000000) {
        return (num / 10000000).toFixed(2) + 'Cr';
    } else if (num >= 100000) {
        return (num / 100000).toFixed(2) + 'L';
    } else if (num >= 1000) {
        return (num / 1000).toFixed(2) + 'K';
    } else {
        return Number(num).toFixed(2);
    }
}

/**
 * Update the trade history summary section (total trades, P&L, etc).
 * @param {Array} history
 * @param {string} mode
 * @param {number} totalCount
 */
function updateHistorySummary(history, mode = 'Unknown', totalCount = 0) {
    try {
        const trades = Array.isArray(history) ? history : [];
        const totalTrades = totalCount || trades.length;
        const buyTrades = trades.filter(t => t.action === 'Buy').length;
        const sellTrades = trades.filter(t => t.action !== 'Buy').length;
        const totalPnl = trades.filter(t => t.action !== 'Buy').reduce((sum, t) => sum + (t.pnl || 0), 0);
        
        // Calculate profit/loss trades
        const profitTrades = trades.filter(t => t.action !== 'Buy' && (t.pnl || 0) > 0).length;
        const lossTrades = trades.filter(t => t.action !== 'Buy' && (t.pnl || 0) < 0).length;
        
        // Update summary elements with mode-specific styling
        if (document.getElementById('totalTrades')) {
            document.getElementById('totalTrades').textContent = totalTrades;
            document.getElementById('totalTrades').className = mode === 'Paper Trading' ? 'metric-value paper-mode' : 'metric-value';
        }
        if (document.getElementById('buyTrades'))
            document.getElementById('buyTrades').textContent = buyTrades;
        if (document.getElementById('sellTrades'))
            document.getElementById('sellTrades').textContent = sellTrades;
        if (document.getElementById('historyTotalPnl')) {
            const pnlElement = document.getElementById('historyTotalPnl');
            pnlElement.textContent = `₹${formatNumber(totalPnl)}`;
            pnlElement.className = totalPnl >= 0 ? 'metric-value profit' : 'metric-value loss';
            if (mode === 'Paper Trading') {
                pnlElement.classList.add('paper-mode');
            }
        }
        
        // Add trading mode indicator if summary header exists
        const summaryHeader = document.querySelector('.history-summary h3');
        if (summaryHeader) {
            const modeText = mode === 'Paper Trading' ? ' (Paper Trading)' : 
                           mode === 'Live Trading' ? ' (Live Trading)' : '';
            if (!summaryHeader.textContent.includes('(')) {
                summaryHeader.textContent = summaryHeader.textContent.replace('Summary', `Summary${modeText}`);
            }
        }
        
        // Update additional metrics if elements exist
        if (document.getElementById('profitTrades'))
            document.getElementById('profitTrades').textContent = profitTrades;
        if (document.getElementById('lossTrades'))
            document.getElementById('lossTrades').textContent = lossTrades;
        if (document.getElementById('winRate') && sellTrades > 0) {
            const winRate = ((profitTrades / sellTrades) * 100).toFixed(1);
            document.getElementById('winRate').textContent = `${winRate}%`;
        }
        
    } catch (err) {
        console.error('Error updating history summary:', err);
    }
}

// Sidebar toggle logic
function setupSidebarToggle() {
    const sidebar = document.querySelector('.sidebar');
    const mainContent = document.querySelector('.main-content');
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebarClose = document.getElementById('sidebarClose');
    if (!sidebar || !mainContent || !sidebarToggle || !sidebarClose) return;

    function openSidebar() {
        sidebar.classList.remove('collapsed');
        mainContent.classList.remove('expanded');
        sidebarToggle.style.display = 'none';
    }
    function closeSidebar() {
        sidebar.classList.add('collapsed');
        mainContent.classList.add('expanded');
        sidebarToggle.style.display = 'block';
    }
    sidebarToggle.addEventListener('click', openSidebar);
    sidebarClose.addEventListener('click', closeSidebar);
    // Start with sidebar open on desktop, collapsed on mobile
    if (window.innerWidth < 900) {
        closeSidebar();
    } else {
        openSidebar();
    }
}

// Zerodha Integration Functions

let zerodhaModalRefreshTimer = null;

function setupZerodhaModalListeners() {
    if (zerodhaConnectBtn) {
        zerodhaConnectBtn.addEventListener('click', () => {
            zerodhaModal.style.display = 'flex';
            updateZerodhaModal();
            // Start periodic refresh while modal is open
            if (zerodhaModalRefreshTimer) clearInterval(zerodhaModalRefreshTimer);
            zerodhaModalRefreshTimer = setInterval(updateZerodhaModal, 500);
        });
    }
    if (zerodhaLoginBtn) {
        zerodhaLoginBtn.addEventListener('click', (e) => {
            e.preventDefault();
            window.open('/api/zerodha/login', '_blank');
        });
    }
    // Close modal on background click
    if (zerodhaModal) {
        zerodhaModal.addEventListener('click', (e) => {
            if (e.target === zerodhaModal) {
                zerodhaModal.style.display = 'none';
                if (zerodhaModalRefreshTimer) clearInterval(zerodhaModalRefreshTimer);
            }
        });
    }
    // Also stop refresh when modal is closed by close button
    const closeBtn = document.getElementById('closeZerodhaModal');
    if (closeBtn) {
        closeBtn.addEventListener('click', () => {
            zerodhaModal.style.display = 'none';
            if (zerodhaModalRefreshTimer) clearInterval(zerodhaModalRefreshTimer);
        });
    }
}

// Update Zerodha modal to show API key/access token status and errors
function updateZerodhaModal() {
    if (zerodhaStatus) {
        zerodhaStatus.textContent = zerodhaConnected ? '🟢 Zerodha: Connected' : '🔴 Zerodha: Disconnected';
        zerodhaStatus.className = zerodhaConnected ? 'status-indicator connected' : 'status-indicator disconnected';
    }
    if (zerodhaLoginBtn) {
        zerodhaLoginBtn.style.display = zerodhaConnected ? 'none' : 'inline-block';
    }
    // Fetch and update API key/access token status
    fetch('/api/zerodha/status')
        .then(res => res.json())
        .then(data => {
            const apiKeyStatus = document.getElementById('apiKeyStatus');
            const accessTokenStatus = document.getElementById('accessTokenStatus');
            const zerodhaError = document.getElementById('zerodhaError');
            if (apiKeyStatus) {
                apiKeyStatus.textContent = data.api_key_configured ? '🟢 API Key: Configured' : '🔴 API Key: Not Configured';
            }
            if (accessTokenStatus) {
                if (!data.access_token) {
                    accessTokenStatus.textContent = '🔴 Access Token: Not Available';
                } else if (data.access_token_expired) {
                    accessTokenStatus.textContent = '🟠 Access Token: Expired';
                } else {
                    accessTokenStatus.textContent = '🟢 Access Token: Active';
                }
            }
            // Show error if any
            if (zerodhaError) {
                if (!data.api_key_configured) {
                    zerodhaError.textContent = 'API Key is not configured. Please check backend settings.';
                } else if (!data.access_token) {
                    zerodhaError.textContent = 'Access token is missing. Please login to Zerodha.';
                } else if (data.access_token_expired) {
                    zerodhaError.textContent = 'Access token has expired. Please re-login to Zerodha.';
                } else if (!data.connected) {
                    zerodhaError.textContent = 'Zerodha is not connected. Please check your connection.';
                } else {
                    zerodhaError.textContent = '';
                }
            }
        })
        .catch(() => {
            const zerodhaError = document.getElementById('zerodhaError');
            if (zerodhaError) zerodhaError.textContent = 'Unable to fetch Zerodha status.';
        });
}

async function checkZerodhaConnection() {
    try {
        const res = await fetch('/api/zerodha/status');
        const data = await res.json();
        zerodhaConnected = data.connected;
        tradingReady = data.trading_enabled;
        
        if (data.connected) {
            showToast('✅ Zerodha Connected - Live Trading Ready!', 'success');
            fetchZerodhaLiveData();
            // Hide trading alert if it's showing
            hideTradingAlert();
        } else {
            showToast(`⚠️ Zerodha Setup Required: ${data.message}`, 'warning');
        }
        
        updateZerodhaModal();
    } catch (err) {
        zerodhaConnected = false;
        tradingReady = false;
        updateZerodhaModal();
        console.error('Error checking Zerodha connection:', err);
    }
}

// Fetch and display Zerodha data
async function fetchZerodhaLiveData() {
    if (!zerodhaConnected) return;
    fetchZerodhaFunds();
    fetchZerodhaPositions();
    fetchZerodhaOrders();
}

async function fetchZerodhaFunds() {
    try {
        const res = await fetch('/api/zerodha/funds');
        const data = await res.json();
        if (zerodhaFunds) {
            zerodhaFunds.textContent = `₹${formatNumber(data.available)}`;
        }
    } catch (err) {
        if (zerodhaFunds) zerodhaFunds.textContent = 'Error';
    }
}

async function fetchZerodhaPositions() {
    try {
        const res = await fetch('/api/zerodha/positions');
        const data = await res.json();
        if (zerodhaPositions) {
            zerodhaPositions.textContent = data.positions ? data.positions.length : 0;
        }
    } catch (err) {
        if (zerodhaPositions) zerodhaPositions.textContent = 'Error';
    }
}

function renderZerodhaPositions(positions) {
    if (!positions || positions.length === 0) return '<div>No positions</div>';
    let html = '<table class="live-table"><tr><th>Symbol</th><th>Qty</th><th>Avg Price</th><th>P&L</th></tr>';
    positions.forEach(pos => {
        html += `<tr><td>${pos.tradingsymbol}</td><td>${pos.quantity}</td><td>₹${pos.average_price}</td><td>₹${pos.pnl}</td></tr>`;
    });
    html += '</table>';
    return html;
}

async function fetchZerodhaOrders() {
    try {
        const res = await fetch('/api/zerodha/orders');
        const data = await res.json();
        if (zerodhaOrders) {
            zerodhaOrders.textContent = data.orders ? data.orders.length : 0;
        }
    } catch (err) {
        if (zerodhaOrders) zerodhaOrders.textContent = 'Error';
    }
}

function renderZerodhaOrders(orders) {
    if (!orders || orders.length === 0) return '<div>No orders</div>';
    let html = '<table class="live-table"><tr><th>Order ID</th><th>Symbol</th><th>Status</th><th>Qty</th><th>Price</th></tr>';
    orders.forEach(order => {
        html += `<tr><td>${order.order_id}</td><td>${order.tradingsymbol}</td><td>${order.status}</td><td>${order.quantity}</td><td>₹${order.price}</td></tr>`;
    });
    html += '</table>';
    return html;
}

// Trading Alert Functions
function showTradingAlert(title, message, showSetupButton = true) {
    const modal = document.getElementById('tradingAlertModal');
    const titleElement = document.getElementById('alertTitle');
    const messageElement = document.getElementById('alertMessage');
    const setupBtn = document.getElementById('setupZerodhaBtn');
    const dismissBtn = document.getElementById('dismissAlertBtn');
    
    if (!modal) return;
    
    titleElement.textContent = title;
    messageElement.textContent = message;
    
    if (showSetupButton) {
        setupBtn.style.display = 'inline-flex';
    } else {
        setupBtn.style.display = 'none';
    }
    
    modal.style.display = 'flex';
    
    // Setup event listeners
    setupBtn.onclick = () => {
        modal.style.display = 'none';
        zerodhaModal.style.display = 'flex';
    };
    
    dismissBtn.onclick = () => {
        modal.style.display = 'none';
    };
    
    // Close on outside click
    modal.onclick = (e) => {
        if (e.target === modal) {
            modal.style.display = 'none';
        }
    };
}

function hideTradingAlert() {
    const modal = document.getElementById('tradingAlertModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

// Quantity management functions
function getSavedQuantity(inputId) {
    const saved = localStorage.getItem(`qty_${inputId}`);
    return saved ? parseInt(saved) : null;
}

function saveQuantity(inputId, quantity) {
    localStorage.setItem(`qty_${inputId}`, quantity.toString());
}

function updateQuantityDisplay(inputId, lotSize, price, totalQtyId, totalValueId) {
    const input = document.getElementById(inputId);
    if (!input) return;
    
    const lots = parseInt(input.value) || 1;
    const totalQty = lots * lotSize;
    const totalValue = totalQty * price;
    
    // Update display elements
    const totalQtyElement = document.getElementById(totalQtyId);
    const totalValueElement = document.getElementById(totalValueId);
    
    if (totalQtyElement) {
        totalQtyElement.textContent = totalQty;
        totalQtyElement.classList.add('highlight-update');
        setTimeout(() => totalQtyElement.classList.remove('highlight-update'), 500);
    }
    
    if (totalValueElement) {
        totalValueElement.textContent = `₹${totalValue.toFixed(0)}`;
        totalValueElement.classList.add('highlight-update');
        setTimeout(() => totalValueElement.classList.remove('highlight-update'), 500);
    }
    
    // Save the quantity
    saveQuantity(inputId, lots);
}

// Utility function to adjust quantity with +/- buttons
function adjustQuantity(inputId, change) {
    const input = document.getElementById(inputId);
    if (!input) return;
    
    let currentValue = parseInt(input.value) || 1;
    let newValue = currentValue + change;
    
    // Ensure value stays within bounds
    const min = parseInt(input.min) || 1;
    const max = parseInt(input.max) || 20;
    
    if (newValue < min) newValue = min;
    if (newValue > max) newValue = max;
    
    input.value = newValue;
    
    // Trigger input event to update display
    input.dispatchEvent(new Event('input', { bubbles: true }));
    
    // Add visual feedback
    input.classList.add('qty-updated');
    setTimeout(() => input.classList.remove('qty-updated'), 200);
}

// Restore saved quantities after page refresh or option chain updates
function restoreQuantities() {
    // Restore all saved quantities after option chain update
    setTimeout(() => {
        const qtyInputs = document.querySelectorAll('.qty-input');
        qtyInputs.forEach(input => {
            const savedQty = getSavedQuantity(input.id);
            if (savedQty && savedQty !== parseInt(input.value)) {
                input.value = savedQty;
                // Trigger update display
                input.dispatchEvent(new Event('input', { bubbles: true }));
            }
        });
    }, 100);
}

// Show or hide a loading overlay
function showLoading(show) {
    let loadingDiv = document.getElementById('loadingOverlay');
    if (!loadingDiv) {
        loadingDiv = document.createElement('div');
        loadingDiv.id = 'loadingOverlay';
        loadingDiv.style.position = 'fixed';
        loadingDiv.style.top = 0;
        loadingDiv.style.left = 0;
        loadingDiv.style.width = '100vw';
        loadingDiv.style.height = '100vh';
        loadingDiv.style.background = 'rgba(255,255,255,0.6)';
        loadingDiv.style.zIndex = 9999;
        loadingDiv.style.display = 'flex';
        loadingDiv.style.alignItems = 'center';
        loadingDiv.style.justifyContent = 'center';
        loadingDiv.innerHTML = '<div style="font-size:2rem;color:#1976d2;"><span class="spinner-border"></span> Loading...</div>';
        document.body.appendChild(loadingDiv);
    }
    loadingDiv.style.display = show ? 'flex' : 'none';
}

// Show toast notifications
function showToast(message, type = 'info') {
    // Create toast container if it doesn't exist
    let toastContainer = document.getElementById('toastContainer');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toastContainer';
        toastContainer.style.position = 'fixed';
        toastContainer.style.top = '20px';
        toastContainer.style.right = '20px';
        toastContainer.style.zIndex = 10000;
        toastContainer.style.display = 'flex';
        toastContainer.style.flexDirection = 'column';
        toastContainer.style.gap = '10px';
        document.body.appendChild(toastContainer);
    }

    // Create toast element
    const toast = document.createElement('div');
    toast.style.background = getToastColor(type);
    toast.style.color = 'white';
    toast.style.padding = '8px 16px'; // Reduced padding for compact look
    toast.style.borderRadius = '6px'; // Smaller border radius
    toast.style.boxShadow = '0 2px 8px rgba(0,0,0,0.2)'; // Lighter shadow
    toast.style.maxWidth = '280px'; // Smaller max width
    toast.style.fontSize = '13px'; // Smaller font
    toast.style.fontWeight = '500';
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    toast.style.transition = 'all 0.3s ease';
    toast.innerHTML = `
        <div style="display: flex; align-items: center; gap: 6px;">
            <span style="font-size: 14px;">${getToastIcon(type)}</span>
            <span>${message}</span>
        </div>
    `;

    toastContainer.appendChild(toast);

    // Animate in
    setTimeout(() => {
        toast.style.opacity = '1';
        toast.style.transform = 'translateX(0)';
    }, 10);

    // Auto remove after 3 seconds (reduced from 4)
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    }, 3000); // Reduced from 4000 to 3000ms
}

function getToastColor(type) {
    switch (type) {
        case 'success': return '#4caf50';
        case 'error': return '#f44336';
        case 'warning': return '#ff9800';
        case 'info': return '#2196f3';
        default: return '#2196f3';
    }
}

function getToastIcon(type) {
    switch (type) {
        case 'success': return '✅';
        case 'error': return '❌';
        case 'warning': return '⚠️';
        case 'info': return 'ℹ️';
        default: return 'ℹ️';
    }
}

// Utility functions for debugging
window.debugApp = {
    socket,
    currentSymbol,
    currentExpiry,
    refreshInterval,
    isLoggedIn,
    lotSizes
};

function togglePositionView(view) {
    currentPositionView = view;
    
    // Update toggle button styles
    const zerodhaBtn = document.getElementById('zerodhaPositionsBtn');
    const autoBtn = document.getElementById('autoTradingPositionsBtn');
    
    if (zerodhaBtn && autoBtn) {
        zerodhaBtn.classList.toggle('active', view === 'zerodha');
        autoBtn.classList.toggle('active', view === 'auto');
    }
    
    // Display the appropriate positions
    if (view === 'zerodha') {
        updatePositions(zerodhaPositionsData);
    } else if (view === 'auto') {
        updateAutoTradingPositions(autoTradingPositionsData);
    }
}

function updateAutoTradingPositions(data) {
    const container = document.getElementById('positionsTable');
    if (!container) return;
    
    // Handle different response formats
    let positions = [];
    if (data && data.success && Array.isArray(data.positions)) {
        positions = data.positions;
    } else if (Array.isArray(data)) {
        positions = data;
    } else {
        console.log('No auto trading positions data or unexpected format:', data);
        container.innerHTML = '<div class="info-message">No auto trading positions</div>';
        return;
    }
    
    if (positions.length === 0) {
        container.innerHTML = '<div class="info-message">No auto trading positions</div>';
        return;
    }
    
    let html = `
        <div class="position-row position-header">
            <div>Strike</div>
            <div>Type</div>
            <div>Qty</div>
            <div>Buy ₹</div>
            <div>Current ₹</div>
            <div>Stop ₹</div>
            <div>Current P&L</div>
            <div>Total P&L</div>
            <div>Auto Sell Count</div>
            <div>Auto Buy Count</div>
            <div>Mode</div>
            <div>Actions</div>
        </div>
    `;
    
    positions.forEach(position => {
        const currentPnlClass = position.current_pnl > 0 ? 'profit' : position.current_pnl < 0 ? 'loss' : '';
        const totalPnlClass = position.total_pnl > 0 ? 'profit' : position.total_pnl < 0 ? 'loss' : '';
        const modeClass = position.waiting_for_autobuy ? 'waiting' : 'running';
        
        html += `
            <div class="position-row ${modeClass}">
                <div>${position.strike}</div>
                <div>${position.type}</div>
                <div>${position.qty}</div>
                <div>₹${position.buy_price.toFixed(2)}</div>
                <div>₹${position.current_price.toFixed(2)}</div>
                <div>₹${position.stop_loss_price.toFixed(2)}</div>
                <div class="${currentPnlClass}">₹${position.current_pnl.toFixed(2)}</div>
                <div class="${totalPnlClass}">₹${position.total_pnl.toFixed(2)}</div>
                <div class="auto-sell-count">${position.auto_sell_count || 0}</div>
                <div class="auto-buy-count-cell" style="color: #ff9800; font-weight: bold;">${position.auto_buy_count || 0}</div>
                <div class="mode-badge ${modeClass}">${position.mode}</div>
                <div>
                    ${!position.waiting_for_autobuy ? 
                        `<div class="action-buttons">
                            <button class="btn btn-danger btn-small" onclick="manualAutoSell('${position.id}')" title="Trigger auto sell (will allow auto buy)">Auto Sell</button>
                            <button class="btn btn-warning btn-small" onclick="manualSellAutoPosition('${position.id}')" title="Manual sell and remove completely (no auto buy)">Manual Sell</button>
                        </div>` :
                        '<span class="waiting-text">Waiting for Auto Buy</span>'
                    }
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

async function manualSellAutoPosition(positionId) {
    if (!confirm('Are you sure you want to manually sell this position?\n\nThis will completely remove the position and NO AUTO BUY will trigger.')) {
        return;
    }
    
    try {
        const response = await fetch('/api/manual-sell-auto-position', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                position_id: positionId
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast(data.message, 'success');
            // Refresh auto positions
            loadAutoPositions();
        } else {
            showToast(data.message, 'error');
        }
        
    } catch (error) {
        console.error('Error in manual sell auto position:', error);
        showToast('Error selling auto position', 'error');
    }
}

async function manualAutoSell(positionId) {
    if (!confirm('Are you sure you want to trigger manual auto sell for this position?')) {
        return;
    }
    
    try {
        const response = await fetch('/api/manual-trigger-auto-sell', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                position_id: positionId
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showMessage(data.message, 'success');
        } else {
            showMessage(data.message, 'error');
        }
        
    } catch (error) {
        console.error('Error triggering manual auto sell:', error);
        showToast('Error triggering manual auto sell', 'error');
    }
}

// Missing utility functions
function showMessage(message, type = 'info') {
    showToast(message, type);
}

function getTradeIcon(trade) {
    if (trade.action === 'Buy') return '🟢';
    if (trade.action === 'Sell') return '🔴';
    if (trade.action.includes('Auto')) return '🤖';
    return '📊';
}

function updateCurrentTime() {
    const timeElement = document.getElementById('currentTime');
    if (timeElement) {
        const now = new Date();
        const istTime = now.toLocaleString('en-IN', { 
            timeZone: 'Asia/Kolkata',
            hour12: false,
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
        timeElement.textContent = `IST: ${istTime}`;
    }
}

async function clearTradeHistory() {
    if (!confirm('Are you sure you want to clear trade history?')) return;
    try {
        // Get current trading mode from API
        const statusResponse = await fetch('/api/paper-trading/status');
        const statusData = await statusResponse.json();
        const mode = statusData.paper_trading_enabled ? 'paper' : 'live';
        
        const response = await fetch('/api/clear-history', { 
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ mode: mode })
        });
        const data = await response.json();
        
        console.log('Clear history response:', data); // Debug log
        
        if (data.success) {
            showToast(data.message, 'success');
            loadTradeHistory();
        } else {
            console.error('Clear history failed:', data); // Debug log
            showToast(data.message || 'Failed to clear history', 'error');
        }
    } catch (error) {
        console.error('Error clearing history:', error);
        showToast('Failed to clear history', 'error');
    }
}

async function viewAllHistory() {
    try {
        const response = await fetch('/api/trade-history/all');
        const data = await response.json();
        
        if (data.trades && data.trades.length > 0) {
            updateTradeHistory(data);
            showToast(`Loaded ${data.total_trades} trades (${data.paper_trades} paper + ${data.live_trades} live)`, 'info');
        } else {
            showToast('No trade history found', 'info');
        }
    } catch (error) {
        console.error('Error loading all history:', error);
        showToast('Failed to load history', 'error');
    }
}

function handleHistoryFilter() {
    loadTradeHistory();
}

// Auto Trading Functions - AUTO TRADING IS ALWAYS ENABLED
// No need for toggle functions since auto trading is always active

// Zerodha Session Monitoring
let sessionCheckInterval = null;
let lastSessionStatus = null;

function startSessionMonitoring() {
    console.log('🔐 Starting Zerodha session monitoring...');
    
    // Check immediately
    checkSessionStatus();
    
    // Then check every 2 minutes
    sessionCheckInterval = setInterval(checkSessionStatus, 120000); // 2 minutes
}

async function checkSessionStatus() {
    try {
        // Skip session check if paper trading is enabled
        const paperTradingToggle = document.getElementById('paperTradingToggle');
        const isPaperTradingEnabled = paperTradingToggle && paperTradingToggle.checked;
        
        if (isPaperTradingEnabled) {
            console.log('📄 Paper Trading enabled - skipping Zerodha session check');
            return;
        }
        
        const response = await fetch('/api/zerodha/session-status');
        const data = await response.json();
        
        // Update session status in UI
        updateSessionStatusUI(data);
        
        // Handle session changes
        if (lastSessionStatus && lastSessionStatus.connected !== data.connected) {
            if (data.connected) {
                showToast('✅ Zerodha session restored!', 'success');
            } else {
                showToast('⚠️ Zerodha session disconnected!', 'warning');
            }
        }
        
        lastSessionStatus = data;
        
    } catch (error) {
        console.error('Session status check failed:', error);
        updateSessionStatusUI({
            connected: false,
            status: 'error',
            message: 'Status check failed'
        });
    }
}

function updateSessionStatusUI(sessionData) {
    // Update Zerodha status indicator
    const zerodhaStatus = document.getElementById('zerodhaStatus');
    if (zerodhaStatus) {
        const statusClass = sessionData.connected ? 'connected' : 'disconnected';
        const statusText = sessionData.connected ? 
            `✅ ${sessionData.user_name || 'Connected'}` : 
            `❌ ${sessionData.message || 'Disconnected'}`;
        
        zerodhaStatus.className = `status-indicator ${statusClass}`;
        zerodhaStatus.textContent = statusText;
        zerodhaStatus.title = `Status: ${sessionData.status} | Last check: ${sessionData.last_check || 'Never'}`;
    }
    
    // Show session expired notification (only if not in paper trading mode)
    if (sessionData.status === 'session_expired') {
        // Check if paper trading is enabled
        const paperTradingToggle = document.getElementById('paperTradingToggle');
        const isPaperTradingEnabled = paperTradingToggle && paperTradingToggle.checked;
        
        if (!isPaperTradingEnabled) {
            console.log('🔒 Session expired - showing modal (Live Trading mode)');
            showSessionExpiredModal();
        } else {
            console.log('📄 Session expired but Paper Trading is enabled - ignoring');
        }
    }
}

function showSessionExpiredModal() {
    // Create and show session expired modal
    const existingModal = document.getElementById('sessionExpiredModal');
    if (existingModal) {
        existingModal.style.display = 'flex';
        return;
    }
    
    const modal = document.createElement('div');
    modal.id = 'sessionExpiredModal';
    modal.className = 'modal';
    modal.style.display = 'flex';
    modal.innerHTML = `
        <div class="modal-content">
            <div class="session-expired-container">
                <div class="modal-header">
                    <i class="fas fa-exclamation-triangle" style="color: #f59e0b;"></i>
                    <h2>Session Expired</h2>
                    <p>Your Zerodha session has expired. Please login again to continue trading.</p>
                </div>
                <div class="modal-actions">
                    <button onclick="refreshZerodhaSession()" class="btn btn-primary">
                        <i class="fas fa-refresh"></i>
                        Try Reconnect
                    </button>
                    <button onclick="redirectToZerodhaLogin()" class="btn btn-warning">
                        <i class="fas fa-sign-in-alt"></i>
                        Fresh Login
                    </button>
                    <button onclick="closeSessionModal()" class="btn btn-secondary">
                        <i class="fas fa-times"></i>
                        Dismiss
                    </button>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
}

async function refreshZerodhaSession() {
    try {
        showToast('🔄 Attempting to restore session...', 'info');
        
        const response = await fetch('/api/zerodha/refresh-session', {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('✅ Session restored successfully!', 'success');
            closeSessionModal();
            // Recheck status immediately
            checkSessionStatus();
        } else {
            showToast(`❌ ${data.message}`, 'error');
            if (data.action === 'login_required') {
                // Auto-redirect to login after a delay
                setTimeout(() => {
                    redirectToZerodhaLogin();
                }, 2000);
            }
        }
    } catch (error) {
        console.error('Session refresh failed:', error);
        showToast('❌ Session refresh failed', 'error');
    }
}

function redirectToZerodhaLogin() {
    closeSessionModal();
    window.location.href = '/api/zerodha/login';
}

function closeSessionModal() {
    const modal = document.getElementById('sessionExpiredModal');
    if (modal) {
        modal.remove();
    }
}

// Enhanced Order Notification System
let loadingToasts = new Map();
let notificationSound = null;

function showLoadingToast(message) {
    const toastId = 'loading_' + Date.now();
    const toast = document.createElement('div');
    toast.id = toastId;
    toast.className = 'toast loading-toast';
    toast.innerHTML = `
        <div class="toast-content">
            <div class="loading-spinner"></div>
            <span>${message}</span>
        </div>
    `;
    
    document.body.appendChild(toast);
    loadingToasts.set(toastId, toast);
    
    // Auto-position
    setTimeout(() => {
        toast.classList.add('show');
    }, 100);
    
    return toastId;
}

function hideLoadingToast(toastId) {
    if (!toastId) return;
    
    const toast = loadingToasts.get(toastId);
    if (toast) {
        toast.classList.remove('show');
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
            loadingToasts.delete(toastId);
        }, 300);
    }
}

function showOrderSuccessNotification(action, orderDetails) {
    const { strike, optionType, price, lots, orderId, cost } = orderDetails;
    
    // Create detailed success notification
    const notification = document.createElement('div');
    notification.className = 'order-notification success';
    notification.innerHTML = `
        <div class="notification-header">
            <i class="fas fa-check-circle"></i>
            <h4>${action} Order Successful!</h4>
            <button class="close-btn" onclick="this.parentElement.parentElement.remove()">×</button>
        </div>
        <div class="notification-body">
            <div class="order-details">
                <div class="detail-row">
                    <span class="label">Strike:</span>
                    <span class="value">${strike} ${optionType}</span>
                </div>
                <div class="detail-row">
                    <span class="label">Price:</span>
                    <span class="value">₹${price}</span>
                </div>
                <div class="detail-row">
                    <span class="label">Lots:</span>
                    <span class="value">${lots}</span>
                </div>
                <div class="detail-row">
                    <span class="label">Total Cost:</span>
                    <span class="value cost">₹${formatNumber(cost)}</span>
                </div>
                ${orderId ? `
                <div class="detail-row">
                    <span class="label">Order ID:</span>
                    <span class="value order-id">${orderId}</span>
                </div>
                ` : ''}
            </div>
            <div class="notification-actions">
                <button onclick="loadPositions()" class="btn btn-small btn-primary">
                    <i class="fas fa-refresh"></i> View Positions
                </button>
                <button onclick="loadTradeHistory()" class="btn btn-small btn-secondary">
                    <i class="fas fa-history"></i> Trade History
                </button>
            </div>
        </div>
    `;
    
    // Add to notification container
    addToNotificationContainer(notification);
    
    // Also show a quick toast
    showToast(`✅ ${action} Order Placed: ${strike} ${optionType} @ ₹${price}`, 'success');
}

function showOrderErrorNotification(action, errorDetails) {
    const { strike, optionType, error } = errorDetails;
    
    const notification = document.createElement('div');
    notification.className = 'order-notification error';
    notification.innerHTML = `
        <div class="notification-header">
            <i class="fas fa-exclamation-circle"></i>
            <h4>${action} Order Failed!</h4>
            <button class="close-btn" onclick="this.parentElement.parentElement.remove()">×</button>
        </div>
        <div class="notification-body">
            <div class="order-details">
                <div class="detail-row">
                    <span class="label">Strike:</span>
                    <span class="value">${strike} ${optionType}</span>
                </div>
                <div class="detail-row error-row">
                    <span class="label">Error:</span>
                    <span class="value">${error}</span>
                </div>
            </div>
            <div class="notification-actions">
                <button onclick="checkSessionStatus()" class="btn btn-small btn-warning">
                    <i class="fas fa-wifi"></i> Check Connection
                </button>
                <button onclick="this.parentElement.parentElement.parentElement.remove()" class="btn btn-small btn-secondary">
                    <i class="fas fa-times"></i> Dismiss
                </button>
            </div>
        </div>
    `;
    
    addToNotificationContainer(notification);
    showToast(`❌ ${action} Failed: ${error}`, 'error');
}

function addToNotificationContainer(notification) {
    let container = document.getElementById('notificationContainer');
    if (!container) {
        container = document.createElement('div');
        container.id = 'notificationContainer';
        container.className = 'notification-container';
        document.body.appendChild(container);
    }
    
    container.appendChild(notification);
    
    // Show with animation
    setTimeout(() => {
        notification.classList.add('show');
    }, 100);
    
    // Auto-remove after 15 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.classList.remove('show');
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }
    }, 15000);
}

function playNotificationSound(type) {
    try {
        if (!notificationSound) {
            notificationSound = new Audio();
        }
        
        // Use different frequencies for different types
        const context = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = context.createOscillator();
        const gain = context.createGain();
        
        oscillator.connect(gain);
        gain.connect(context.destination);
        
        if (type === 'success') {
            // Pleasant success tone
            oscillator.frequency.setValueAtTime(800, context.currentTime);
            oscillator.frequency.setValueAtTime(1000, context.currentTime + 0.1);
        } else if (type === 'error') {
            // Alert error tone
            oscillator.frequency.setValueAtTime(400, context.currentTime);
            oscillator.frequency.setValueAtTime(300, context.currentTime + 0.1);
        }
        
        gain.gain.setValueAtTime(0.1, context.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.01, context.currentTime + 0.2);
        
        oscillator.start(context.currentTime);
        oscillator.stop(context.currentTime + 0.2);
        
    } catch (error) {
        console.log('Sound notification not supported');
    }
}

function getLotSize(symbol) {
    const lotSizes = {
        'NIFTY': 75,
        'BANKNIFTY': 35,
        'MIDCPNIFTY': 140,
        'SENSEX': 20,
        'SBIN': 3400,
        'RELIANCE': 500
    };
    return lotSizes[symbol] || 1;
}

// Stop session monitoring when page unloads
window.addEventListener('beforeunload', () => {
    if (sessionCheckInterval) {
        clearInterval(sessionCheckInterval);
    }
});

// Paper Trading Functions
function initializePaperTradingToggle() {
    const toggle = document.getElementById('paperTradingToggle');
    const label = document.getElementById('tradingModeLabel');
    const container = document.querySelector('.trading-mode-toggle');
    
    if (!toggle || !label) {
        console.error('Paper trading toggle elements not found');
        return;
    }
    
    console.log('📄 Initializing paper trading toggle...');
    
    // Track if toggle operation is in progress
    let toggleInProgress = false;
    
    // Get initial status from backend
    fetchPaperTradingStatus();
    
    // Setup toggle event listener
    toggle.addEventListener('change', handleToggleChange);
    
    function fetchPaperTradingStatus() {
        fetch('/api/paper-trading/status')
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                return response.json();
            })
            .then(data => {
                console.log('📄 Initial paper trading status:', data);
                const isEnabled = data.paper_trading_enabled || false;
                
                // Update toggle state without triggering change event
                toggle.removeEventListener('change', handleToggleChange);
                toggle.checked = isEnabled;
                toggle.addEventListener('change', handleToggleChange);
                
                // Update UI
                updateTradingModeUI(isEnabled);
            })
            .catch(error => {
                console.error('Error fetching paper trading status:', error);
                showToast('Failed to load trading mode status', 'error');
                
                // Default to live trading mode
                toggle.removeEventListener('change', handleToggleChange);
                toggle.checked = false;
                toggle.addEventListener('change', handleToggleChange);
                updateTradingModeUI(false);
            });
    }
    
    function handleToggleChange(e) {
        // Prevent multiple rapid clicks
        if (toggleInProgress) {
            console.log('🚫 Toggle operation already in progress, reverting...');
            e.preventDefault();
            toggle.checked = !toggle.checked; // Revert the toggle
            return;
        }
        
        const enabled = toggle.checked;
        console.log(`🔄 Toggle changed to: ${enabled ? 'Paper Trading' : 'Live Trading'}`);
        
        // Mark toggle operation as in progress
        toggleInProgress = true;
        
        // Add visual feedback
        toggle.disabled = true;
        container.classList.add('loading');
        
        // Show loading toast
        const loadingToast = showToast(`🔄 Switching to ${enabled ? 'Paper' : 'Live'} Trading...`, 'info');
        
        // Send toggle request to backend
        fetch('/api/paper-trading/toggle', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ enabled: enabled })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('📄 Toggle response:', data);
            
            if (data.success) {
                // Update UI to reflect the change
                updateTradingModeUI(enabled);
                
                // Control session monitoring based on trading mode
                if (enabled) {
                    // Paper trading enabled - stop session monitoring
                    if (typeof sessionCheckInterval !== 'undefined' && sessionCheckInterval) {
                        clearInterval(sessionCheckInterval);
                        sessionCheckInterval = null;
                        console.log('📄 Paper Trading enabled - stopped session monitoring');
                    }
                    // Close any existing session expired modal
                    const existingModal = document.getElementById('sessionExpiredModal');
                    if (existingModal) {
                        existingModal.style.display = 'none';
                    }
                } else {
                    // Live trading enabled - start session monitoring
                    if (typeof startSessionMonitoring === 'function') {
                        startSessionMonitoring();
                        console.log('💰 Live Trading enabled - started session monitoring');
                    }
                }
                
                // Show success message
                const modeText = enabled ? 'Paper Trading' : 'Live Trading';
                const modeIcon = enabled ? '📄' : '💰';
                showToast(`${modeIcon} Switched to ${modeText} mode successfully!`, 'success');
                
                // Refresh data after a short delay
                setTimeout(() => {
                    loadWalletInfo();
                    loadPositions();
                }, 500);
                
            } else {
                throw new Error(data.error || data.message || 'Unknown error');
            }
        })
        .catch(error => {
            console.error('Error toggling paper trading:', error);
            
            // Revert toggle state
            toggle.checked = !enabled;
            updateTradingModeUI(!enabled);
            
            // Show error message
            showToast(`❌ Failed to switch trading mode: ${error.message}`, 'error');
        })
        .finally(() => {
            // Re-enable toggle and reset progress flag
            toggle.disabled = false;
            toggleInProgress = false;
            container.classList.remove('loading');
            console.log('🔓 Toggle operation completed');
        });
    }
    
    console.log('📄 Paper trading toggle initialized successfully');
}

function updateTradingModeUI(paperTradingEnabled) {
    // Update global paper trading state
    window.paperTradingEnabled = paperTradingEnabled;
    
    const label = document.getElementById('tradingModeLabel');
    const toggle = document.getElementById('paperTradingToggle');
    const container = document.querySelector('.trading-mode-toggle');
    const zerodhaSection = document.getElementById('zerodhaConnectionSection');
    const description = document.querySelector('.toggle-description');
    
    console.log(`🎨 Updating UI for ${paperTradingEnabled ? 'Paper' : 'Live'} Trading mode`);
    
    if (!label || !container) {
        console.error('Trading mode UI elements not found');
        return;
    }
    
    // Add smooth transition class
    container.classList.add('transitioning');
    
    if (paperTradingEnabled) {
        // Paper Trading Mode
        label.textContent = 'Paper Trading';
        if (description) description.textContent = 'Virtual Money';
        
        container.classList.add('paper-mode');
        container.classList.remove('live-mode');
        
        // Hide Zerodha connection section with smooth transition
        if (zerodhaSection) {
            zerodhaSection.classList.add('hiding');
            zerodhaSection.classList.remove('showing');
            setTimeout(() => {
                zerodhaSection.style.display = 'none';
            }, 300);
        }
        
        // Update portfolio title and related elements
        const portfolioTitle = document.getElementById('portfolioTitle');
        const portfolioDataSource = document.getElementById('portfolioDataSource');
        const resetWalletBtn = document.getElementById('resetPaperWalletBtn');
        const balanceMode = document.getElementById('balanceMode');
        
        if (portfolioTitle) portfolioTitle.textContent = 'Paper Trading Portfolio';
        if (portfolioDataSource) portfolioDataSource.textContent = 'Virtual Portfolio Data';
        if (resetWalletBtn) {
            resetWalletBtn.style.display = 'inline-block';
            resetWalletBtn.classList.remove('hiding');
            setTimeout(() => {
                resetWalletBtn.classList.add('showing');
            }, 100);
        }
        if (balanceMode) balanceMode.textContent = 'PAPER TRADING';
        
        console.log('✅ UI updated to Paper Trading mode');
        
    } else {
        // Live Trading Mode
        label.textContent = 'Live Trading';
        if (description) description.textContent = 'Real Money';
        
        container.classList.add('live-mode');
        container.classList.remove('paper-mode');
        
        // Show Zerodha connection section with smooth transition
        if (zerodhaSection) {
            zerodhaSection.style.display = 'flex';
            zerodhaSection.classList.remove('hiding');
            setTimeout(() => {
                zerodhaSection.classList.add('showing');
            }, 50);
        }
        
        // Update portfolio title and related elements
        const portfolioTitle = document.getElementById('portfolioTitle');
        const portfolioDataSource = document.getElementById('portfolioDataSource');
        const resetWalletBtn = document.getElementById('resetPaperWalletBtn');
        const balanceMode = document.getElementById('balanceMode');
        
        if (portfolioTitle) portfolioTitle.textContent = 'Live Trading Portfolio';
        if (portfolioDataSource) portfolioDataSource.textContent = 'Zerodha Live Data';
        if (resetWalletBtn) {
            resetWalletBtn.classList.add('hiding');
            resetWalletBtn.classList.remove('showing');
            setTimeout(() => {
                resetWalletBtn.style.display = 'none';
            }, 300);
        }
        if (balanceMode) balanceMode.textContent = 'LIVE TRADING';
        
        console.log('✅ UI updated to Live Trading mode');
    }
    
    // Update trading mode indicators with animation
    const tradingModeIndicators = document.querySelectorAll('.trading-mode-indicator');
    tradingModeIndicators.forEach(indicator => {
        indicator.style.opacity = '0';
        setTimeout(() => {
            indicator.textContent = paperTradingEnabled ? 'Paper' : 'Live';
            indicator.className = `trading-mode-indicator ${paperTradingEnabled ? 'paper' : 'live'}`;
            indicator.style.opacity = '1';
        }, 150);
    });
    
    // Remove transition class after animation
    setTimeout(() => {
        container.classList.remove('transitioning');
    }, 500);
}

function resetPaperWallet() {
    if (!confirm('Are you sure you want to reset your paper trading wallet? This will clear all positions and reset balance to ₹1,00,000.')) {
        return;
    }
    
    const loadingToast = showToast('🔄 Resetting paper wallet...', 'info');
    
    fetch('/api/paper-trading/reset-wallet', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('✅ ' + data.message, 'success');
            // Refresh wallet and positions data
            setTimeout(() => {
                loadWalletInfo();
                loadPositions();
            }, 500);
        } else {
            showToast('❌ Failed to reset wallet: ' + data.error, 'error');
        }
    })
    .catch(error => {
        console.error('Error resetting paper wallet:', error);
        showToast('❌ Error resetting wallet', 'error');
    });
}

// Helper function to sync toggle state with backend
function syncTradingModeState() {
    fetch('/api/paper-trading/status')
        .then(response => response.json())
        .then(data => {
            const toggle = document.getElementById('paperTradingToggle');
            if (toggle && toggle.checked !== data.paper_trading_enabled) {
                console.log('🔄 Syncing toggle state with backend');
                toggle.checked = data.paper_trading_enabled;
                updateTradingModeUI(data.paper_trading_enabled);
            }
        })
        .catch(error => {
            console.error('Error syncing trading mode state:', error);
        });
}

// Call sync function periodically to ensure consistency
setInterval(syncTradingModeState, 30000); // Every 30 seconds

// Cooldown Protection Toggle Functions
function initializeCooldownToggle() {
    const toggle = document.getElementById('cooldownToggle');
    const label = document.getElementById('cooldownModeLabel');
    const container = document.querySelector('.trading-mode-toggle:nth-child(2)'); // Second toggle container
    
    if (!toggle || !label) {
        console.error('Cooldown toggle elements not found');
        return;
    }
    
    console.log('🔧 Initializing cooldown protection toggle...');
    
    // Track if toggle operation is in progress
    let toggleInProgress = false;
    
    // Get initial status from backend
    fetchCooldownStatus();
    
    // Setup toggle event listener
    toggle.addEventListener('change', handleCooldownToggleChange);
    
    function fetchCooldownStatus() {
        fetch('/api/cooldown/status')
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                console.log('🔧 Current cooldown status:', data);
                // Update UI first, then set toggle state
                updateCooldownUI(data.cooldown_enabled);
                toggle.checked = data.cooldown_enabled;
            })
            .catch(error => {
                console.error('Error fetching cooldown status:', error);
                showToast('⚠️ Failed to load cooldown status', 'warning');
                // Default to enabled
                updateCooldownUI(true);
                toggle.checked = true;
            });
    }
    
    function handleCooldownToggleChange() {
        if (toggleInProgress) {
            console.log('🔒 Cooldown toggle operation already in progress');
            return;
        }
        
        const enabled = toggle.checked;
        console.log(`🔧 Cooldown toggle changed to: ${enabled ? 'ENABLED' : 'DISABLED'}`);
        
        // Prevent multiple rapid toggles
        toggleInProgress = true;
        toggle.disabled = true;
        
        // Add loading state
        if (container) {
            container.classList.add('loading');
        }
        
        // Send request to backend
        toggleCooldownProtection(enabled);
    }
    
    function toggleCooldownProtection(enabled) {
        console.log(`🔧 Toggling cooldown protection to: ${enabled ? 'ENABLED' : 'DISABLED'}`);
        
        fetch('/api/toggle_cooldown', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                cooldown_enabled: enabled
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                console.log('🔧 Cooldown toggle successful:', data);
                
                // Update UI
                updateCooldownUI(data.cooldown_enabled);
                
                // Ensure toggle state matches
                toggle.checked = data.cooldown_enabled;
                
                // Show success message
                const statusText = data.cooldown_enabled ? 'ENABLED' : 'DISABLED';
                const statusIcon = data.cooldown_enabled ? '🛡️' : '⚡';
                showToast(`${statusIcon} Cooldown protection ${statusText}!`, 'success');
                
            } else {
                throw new Error(data.error || data.message || 'Unknown error');
            }
        })
        .catch(error => {
            console.error('Error toggling cooldown protection:', error);
            
            // Revert toggle state and UI
            toggle.checked = !enabled;
            updateCooldownUI(!enabled);
            
            // Show error message
            showToast(`❌ Failed to toggle cooldown protection: ${error.message}`, 'error');
        })
        .finally(() => {
            // Re-enable toggle and reset progress flag
            toggle.disabled = false;
            toggleInProgress = false;
            if (container) {
                container.classList.remove('loading');
            }
            console.log('🔓 Cooldown toggle operation completed');
        });
    }
    
    console.log('🔧 Cooldown protection toggle initialized successfully');
}

function updateCooldownUI(cooldownEnabled) {
    const label = document.getElementById('cooldownModeLabel');
    const toggle = document.getElementById('cooldownToggle');
    const container = document.querySelector('.trading-mode-toggle:nth-child(2)');
    const description = document.querySelector('.trading-mode-toggle:nth-child(2) .toggle-description');
    
    console.log(`🎨 Updating UI for cooldown: ${cooldownEnabled ? 'ENABLED' : 'DISABLED'}`);
    
    if (!label || !container) {
        console.error('Cooldown UI elements not found');
        return;
    }
    
    if (cooldownEnabled) {
        // Cooldown Enabled - Toggle should be ON (right side)
        label.textContent = 'Cooldown ON';
        if (description) description.textContent = 'Protection Active';
        
        container.classList.add('cooldown-enabled');
        container.classList.remove('cooldown-disabled');
        
        // Make sure toggle is checked
        if (toggle) toggle.checked = true;
        
        console.log('✅ UI updated to Cooldown ENABLED mode');
        
    } else {
        // Cooldown Disabled - Toggle should be OFF (left side)
        label.textContent = 'Cooldown OFF';
        if (description) description.textContent = 'Protection Disabled';
        
        container.classList.add('cooldown-disabled');
        container.classList.remove('cooldown-enabled');
        
        // Make sure toggle is unchecked
        if (toggle) toggle.checked = false;
        
        console.log('✅ UI updated to Cooldown DISABLED mode');
    }
}

// Helper function to sync cooldown toggle state with backend
function syncCooldownState() {
    fetch('/api/cooldown/status')
        .then(response => response.json())
        .then(data => {
            const toggle = document.getElementById('cooldownToggle');
            if (toggle && toggle.checked !== data.cooldown_enabled) {
                console.log('🔄 Syncing cooldown toggle state with backend');
                toggle.checked = data.cooldown_enabled;
                updateCooldownUI(data.cooldown_enabled);
            }
        })
        .catch(error => {
            console.error('Error syncing cooldown state:', error);
        });
}

// ===== PROFITABLE RE-ENTRY CONFIRMATION MODAL =====

let currentConfirmationData = null;

function showReentryConfirmationModal(confirmation, message) {
    console.log('💰 Showing re-entry confirmation modal:', confirmation);
    
    currentConfirmationData = confirmation;
    
    // Update modal content
    document.getElementById('confirmationMessage').textContent = message || 'Profitable stop loss hit! Re-enter position?';
    document.getElementById('confirmStrike').textContent = confirmation.strike;
    document.getElementById('confirmOptionType').textContent = confirmation.option_type;
    document.getElementById('confirmBuyPrice').textContent = `₹${confirmation.buy_price.toFixed(2)}`;
    document.getElementById('confirmSellPrice').textContent = `₹${confirmation.sell_price.toFixed(2)}`;
    document.getElementById('confirmProfit').textContent = `₹${confirmation.profit.toFixed(2)}`;
    document.getElementById('confirmReentryPrice').textContent = `₹${confirmation.reentry_price.toFixed(2)}`;
    document.getElementById('confirmQuantity').textContent = `${confirmation.quantity} × ${confirmation.lots} lots`;
    
    // Show modal
    const modal = document.getElementById('reentryConfirmationModal');
    if (modal) {
        modal.style.display = 'block';
        // Play notification sound
        playNotificationSound('profit');
        
        // Auto-close after 30 seconds if no response
        setTimeout(() => {
            if (modal.style.display === 'block') {
                console.log('⏰ Auto-rejecting confirmation after 30 seconds');
                handleReentryDecision('reject');
            }
        }, 30000);
    }
}

function setupReentryConfirmationListeners() {
    const acceptBtn = document.getElementById('acceptReentryBtn');
    const rejectBtn = document.getElementById('rejectReentryBtn');
    
    if (acceptBtn) {
        acceptBtn.addEventListener('click', () => handleReentryDecision('accept'));
    }
    
    if (rejectBtn) {
        rejectBtn.addEventListener('click', () => handleReentryDecision('reject'));
    }
    
    // Close modal when clicking outside
    const modal = document.getElementById('reentryConfirmationModal');
    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                handleReentryDecision('reject');
            }
        });
    }
}

async function handleReentryDecision(decision) {
    if (!currentConfirmationData) {
        console.error('No confirmation data available');
        return;
    }
    
    const errorDiv = document.getElementById('confirmationError');
    const acceptBtn = document.getElementById('acceptReentryBtn');
    const rejectBtn = document.getElementById('rejectReentryBtn');
    
    // Disable buttons during processing
    if (acceptBtn) acceptBtn.disabled = true;
    if (rejectBtn) rejectBtn.disabled = true;
    
    try {
        const response = await fetch('/api/reentry-confirmation/respond', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                confirmation_id: currentConfirmationData.id,
                decision: decision
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            console.log(`✅ Re-entry decision processed: ${decision}`, data);
            
            // Close modal
            const modal = document.getElementById('reentryConfirmationModal');
            if (modal) modal.style.display = 'none';
            
            // Show success message
            const icon = decision === 'accept' ? '✅' : '❌';
            const color = decision === 'accept' ? 'success' : 'info';
            showToast(`${icon} ${data.message}`, color);
            
            // Refresh positions
            loadPositions();
            loadTradeHistory();
            
        } else {
            console.error('Re-entry decision failed:', data.message);
            if (errorDiv) {
                errorDiv.textContent = data.message;
                errorDiv.style.display = 'block';
            }
        }
        
    } catch (error) {
        console.error('Error handling re-entry decision:', error);
        if (errorDiv) {
            errorDiv.textContent = 'Network error. Please try again.';
            errorDiv.style.display = 'block';
        }
    } finally {
        // Re-enable buttons
        if (acceptBtn) acceptBtn.disabled = false;
        if (rejectBtn) rejectBtn.disabled = false;
        
        // Clear confirmation data
        currentConfirmationData = null;
    }
}

// Initialize re-entry confirmation listeners when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    setupReentryConfirmationListeners();
});

// Add cooldown sync to periodic sync
setInterval(syncCooldownState, 30000); // Every 30 seconds
