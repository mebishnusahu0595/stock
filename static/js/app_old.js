// Professional Trading Platform JavaScript
let socket;
let isLoggedIn = false;
let zerodhaConnected = false;
let currentTab = 'overview';
let refreshInterval = 3;
let refreshTimer;

// Initialize app
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    // Initialize socket connection
    socket = io();
    
    setupEventListeners();
    setupTabNavigation();
    setupSocketListeners();
    checkLoginStatus();
    updateServerTime();
    setInterval(updateServerTime, 1000);
    checkZerodhaStatus();
}

// Socket listeners
function setupSocketListeners() {
    if (socket) {
        socket.on('connect', function() {
            console.log('Connected to server');
        });
        
        socket.on('disconnect', function() {
            console.log('Disconnected from server');
        });
        
        socket.on('market_data', function(data) {
            updateMarketData(data);
        });
    }
}

// Tab Navigation
function setupTabNavigation() {
    const navItems = document.querySelectorAll('.nav-item');
    const tabContents = document.querySelectorAll('.tab-content');
    
    navItems.forEach(item => {
        item.addEventListener('click', function() {
            const tabName = this.getAttribute('data-tab');
            
            // Remove active class from all nav items and tab contents
            navItems.forEach(nav => nav.classList.remove('active'));
            tabContents.forEach(tab => tab.classList.remove('active'));
            
            // Add active class to clicked nav item and corresponding tab
            this.classList.add('active');
            document.getElementById(tabName + 'Tab').classList.add('active');
            
            currentTab = tabName;
            loadTabContent(tabName);
        });
    });
}

function loadTabContent(tabName) {
    switch(tabName) {
        case 'overview':
            loadOverviewData();
            break;
        case 'portfolio':
            loadPortfolioData();
            break;
        case 'orders':
            loadOrdersData();
            break;
        case 'positions':
            loadPositionsData();
            break;
        case 'watchlist':
            loadWatchlistData();
            break;
        case 'analytics':
            loadAnalyticsData();
            break;
    }
}

// Event Listeners
function setupEventListeners() {
    // Login form
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', handleLogin);
    }
    
    // Logout button
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', handleLogout);
    }
    
    // Zerodha connection
    const connectZerodhaBtn = document.getElementById('connectZerodhaBtn');
    if (connectZerodhaBtn) {
        connectZerodhaBtn.addEventListener('click', showZerodhaModal);
    }
    
    // Zerodha modal
    setupZerodhaModalListeners();
    
    // Trading buttons
    setupTradingEventListeners();
    
    // Order type changes
    const quickOrderType = document.getElementById('quickOrderType');
    if (quickOrderType) {
        quickOrderType.addEventListener('change', toggleQuickPriceField);
    }
    
    const tradeOrderType = document.getElementById('tradeOrderType');
    if (tradeOrderType) {
        tradeOrderType.addEventListener('change', toggleAdvancedPriceFields);
    }
    
    // Toast close buttons
    const closeErrorToast = document.getElementById('closeErrorToast');
    const closeSuccessToast = document.getElementById('closeSuccessToast');
    if (closeErrorToast) {
        closeErrorToast.addEventListener('click', () => hideToast('error'));
    }
    if (closeSuccessToast) {
        closeSuccessToast.addEventListener('click', () => hideToast('success'));
    }
}

function setupZerodhaModalListeners() {
    const zerodhaLoginBtn = document.getElementById('zerodhaLoginBtn');
    const closeZerodhaModal = document.getElementById('closeZerodhaModal');
    const refreshZerodhaStatus = document.getElementById('refreshZerodhaStatus');
    const checkConnectionBtn = document.getElementById('checkConnectionBtn');
    
    if (zerodhaLoginBtn) {
        zerodhaLoginBtn.addEventListener('click', openZerodhaLogin);
    }
    
    if (closeZerodhaModal) {
        closeZerodhaModal.addEventListener('click', hideZerodhaModal);
    }
    
    if (refreshZerodhaStatus) {
        refreshZerodhaStatus.addEventListener('click', checkZerodhaStatus);
    }
    
    if (checkConnectionBtn) {
        checkConnectionBtn.addEventListener('click', checkZerodhaStatus);
    }
}

function setupTradingEventListeners() {
    // Quick trading buttons
    const quickBuyBtn = document.getElementById('quickBuyBtn');
    const quickSellBtn = document.getElementById('quickSellBtn');
    
    if (quickBuyBtn) {
        quickBuyBtn.addEventListener('click', () => handleQuickTrade('BUY'));
    }
    
    if (quickSellBtn) {
        quickSellBtn.addEventListener('click', () => handleQuickTrade('SELL'));
    }
    
    // Advanced trading buttons
    const advancedBuyBtn = document.getElementById('advancedBuyBtn');
    const advancedSellBtn = document.getElementById('advancedSellBtn');
    
    if (advancedBuyBtn) {
        advancedBuyBtn.addEventListener('click', () => handleAdvancedTrade('BUY'));
    }
    
    if (advancedSellBtn) {
        advancedSellBtn.addEventListener('click', () => handleAdvancedTrade('SELL'));
    }
}

// Authentication
function checkLoginStatus() {
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
    if (dashboard) dashboard.style.display = 'grid';
    
    // Load initial data
    loadOverviewData();
}

async function handleLogin(e) {
    e.preventDefault();
    
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    
    showLoading(true);
    
    try {
        const response = await fetch('/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ username, password })
        });
        
        const data = await response.json();
        
        if (data.success) {
            sessionStorage.setItem('loginToken', data.token || 'authenticated');
            isLoggedIn = true;
            showDashboard();
            showToast('Login successful!', 'success');
        } else {
            showError('loginError', data.message || 'Login failed');
        }
    } catch (error) {
        console.error('Login error:', error);
        showError('loginError', 'Connection error. Please try again.');
    } finally {
        showLoading(false);
    }
}

function handleLogout() {
    sessionStorage.removeItem('loginToken');
    isLoggedIn = false;
    zerodhaConnected = false;
    showLoginModal();
    showToast('Logged out successfully', 'success');
}

// Zerodha Integration
async function checkZerodhaStatus() {
    try {
        const response = await fetch('/api/zerodha-status');
        const data = await response.json();
        
        updateZerodhaUI(data);
        zerodhaConnected = data.connected || false;
        
        if (zerodhaConnected) {
            updateConnectionIndicator('connected');
            loadAccountData();
        } else {
            updateConnectionIndicator('disconnected');
        }
    } catch (error) {
        console.error('Error checking Zerodha status:', error);
        updateConnectionIndicator('disconnected');
    }
}

function updateZerodhaUI(data) {
    const apiKeyStatus = document.getElementById('apiKeyStatus');
    const accessTokenStatus = document.getElementById('accessTokenStatus');
    const connectionStatus = document.getElementById('connectionStatus');
    
    if (apiKeyStatus) {
        apiKeyStatus.textContent = data.api_key_configured ? 
            '🟢 API Key: Configured' : '🔴 API Key: Not Configured';
    }
    
    if (accessTokenStatus) {
        accessTokenStatus.textContent = data.access_token_available ? 
            '🟢 Access Token: Available' : '🔴 Access Token: Not Available';
    }
    
    if (connectionStatus) {
        const statusText = connectionStatus.querySelector('.status-text');
        if (statusText) {
            statusText.textContent = data.connected ? 
                '🟢 Connected' : '🔴 Disconnected';
        }
    }
}

function updateConnectionIndicator(status) {
    const indicator = document.getElementById('connectionIndicator');
    if (indicator) {
        indicator.className = `indicator ${status}`;
        indicator.innerHTML = status === 'connected' ? 
            '<i class="fas fa-circle"></i> Connected' : 
            '<i class="fas fa-circle"></i> Disconnected';
    }
}

function showZerodhaModal() {
    const modal = document.getElementById('zerodhaModal');
    if (modal) {
        modal.style.display = 'flex';
        checkZerodhaStatus();
    }
}

function hideZerodhaModal() {
    const modal = document.getElementById('zerodhaModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

function openZerodhaLogin() {
    window.open('/zerodha-login', 'zerodha_login', 'width=600,height=700');
}

// Time Display
function updateServerTime() {
    const now = new Date();
    const timeString = now.toLocaleTimeString('en-IN', {
        timeZone: 'Asia/Kolkata',
        hour12: false
    });
    
    const serverTimeElement = document.getElementById('serverTime');
    if (serverTimeElement) {
        serverTimeElement.textContent = timeString + ' IST';
    }
}

// Trading Functions
async function handleQuickTrade(action) {
    if (!zerodhaConnected) {
        showToast('Please connect to Zerodha first', 'error');
        return;
    }
    
    const symbol = document.getElementById('quickSymbol').value;
    const quantity = document.getElementById('quickQuantity').value;
    const orderType = document.getElementById('quickOrderType').value;
    const price = document.getElementById('quickPrice').value;
    
    if (!symbol || !quantity) {
        showToast('Please enter symbol and quantity', 'error');
        return;
    }
    
    const orderData = {
        symbol: symbol.toUpperCase(),
        quantity: parseInt(quantity),
        action: action,
        order_type: orderType,
        exchange: 'NSE'
    };
    
    if (orderType === 'LIMIT' && price) {
        orderData.price = parseFloat(price);
    }
    
    await placeOrder(orderData);
}

async function handleAdvancedTrade(action) {
    if (!zerodhaConnected) {
        showToast('Please connect to Zerodha first', 'error');
        return;
    }
    
    const symbol = document.getElementById('tradeSymbol').value;
    const exchange = document.getElementById('tradeExchange').value;
    const quantity = document.getElementById('tradeQuantity').value;
    const orderType = document.getElementById('tradeOrderType').value;
    const price = document.getElementById('tradePrice').value;
    const triggerPrice = document.getElementById('tradeTriggerPrice').value;
    const product = document.getElementById('tradeProduct').value;
    const validity = document.getElementById('tradeValidity').value;
    
    if (!symbol || !quantity) {
        showToast('Please enter symbol and quantity', 'error');
        return;
    }
    
    const orderData = {
        symbol: symbol.toUpperCase(),
        exchange: exchange,
        quantity: parseInt(quantity),
        action: action,
        order_type: orderType,
        product: product,
        validity: validity
    };
    
    if (price) orderData.price = parseFloat(price);
    if (triggerPrice) orderData.trigger_price = parseFloat(triggerPrice);
    
    await placeOrder(orderData);
}

async function placeOrder(orderData) {
    showLoading(true);
    
    try {
        const response = await fetch('/api/place-order', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(orderData)
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast(`${orderData.action} order placed successfully!`, 'success');
            loadOrdersData();
        } else {
            showToast(data.message || 'Order placement failed', 'error');
        }
    } catch (error) {
        console.error('Order placement error:', error);
        showToast('Connection error. Please try again.', 'error');
    } finally {
        showLoading(false);
    }
}

function toggleQuickPriceField() {
    const orderType = document.getElementById('quickOrderType').value;
    const priceField = document.getElementById('quickPrice');
    
    if (priceField) {
        priceField.style.display = orderType === 'LIMIT' ? 'block' : 'none';
    }
}

function toggleAdvancedPriceFields() {
    const orderType = document.getElementById('tradeOrderType').value;
    const priceRow = document.getElementById('priceRow');
    
    if (priceRow) {
        priceRow.style.display = orderType !== 'MARKET' ? 'block' : 'none';
    }
}

// Data Loading Functions
async function loadOverviewData() {
    await Promise.all([
        loadMarketIndices(),
        loadAccountData(),
        loadRecentOrders()
    ]);
}

async function loadMarketIndices() {
    try {
        const response = await fetch('/api/market-indices');
        const data = await response.json();
        
        if (data.success) {
            updateElement('niftyValue', data.nifty?.value || '--');
            updateElement('niftyChange', data.nifty?.change || '--');
            updateElement('sensexValue', data.sensex?.value || '--');
            updateElement('sensexChange', data.sensex?.change || '--');
            updateElement('bankniftyValue', data.banknifty?.value || '--');
            updateElement('bankniftyChange', data.banknifty?.change || '--');
        }
    } catch (error) {
        console.error('Error loading market indices:', error);
        // Use placeholder data
        updateElement('niftyValue', '--');
        updateElement('niftyChange', '--');
        updateElement('sensexValue', '--');
        updateElement('sensexChange', '--');
        updateElement('bankniftyValue', '--');
        updateElement('bankniftyChange', '--');
    }
}

async function loadAccountData() {
    if (!zerodhaConnected) return;
    
    try {
        const response = await fetch('/api/account-summary');
        const data = await response.json();
        
        if (data.success) {
            updateElement('availableBalance', formatCurrency(data.available_balance || 0));
            updateElement('usedMargin', formatCurrency(data.used_margin || 0));
            updateElement('todayPnlOverview', formatCurrency(data.today_pnl || 0));
            updateElement('totalPnl', formatCurrency(data.total_pnl || 0));
            updateElement('accountBalance', formatCurrency(data.available_balance || 0));
            updateElement('todayPnl', formatCurrency(data.today_pnl || 0));
        }
    } catch (error) {
        console.error('Error loading account data:', error);
    }
}

async function loadRecentOrders() {
    try {
        const response = await fetch('/api/recent-orders');
        const data = await response.json();
        
        const ordersList = document.getElementById('recentOrdersList');
        if (ordersList) {
            if (data.success && data.orders && data.orders.length > 0) {
                ordersList.innerHTML = data.orders.map(order => `
                    <div class="order-item">
                        <span class="symbol">${order.symbol}</span>
                        <span class="action ${order.action.toLowerCase()}">${order.action}</span>
                        <span class="quantity">${order.quantity}</span>
                        <span class="status">${order.status}</span>
                    </div>
                `).join('');
            } else {
                ordersList.innerHTML = '<div class="no-data">No recent orders</div>';
            }
        }
    } catch (error) {
        console.error('Error loading recent orders:', error);
        const ordersList = document.getElementById('recentOrdersList');
        if (ordersList) {
            ordersList.innerHTML = '<div class="no-data">No recent orders</div>';
        }
    }
}

async function loadPortfolioData() {
    try {
        const response = await fetch('/api/portfolio');
        const data = await response.json();
        
        const portfolioTable = document.getElementById('portfolioTable');
        if (portfolioTable) {
            if (data.success && data.holdings && data.holdings.length > 0) {
                portfolioTable.innerHTML = data.holdings.map(holding => `
                    <div class="table-row">
                        <div class="table-cell">${holding.symbol}</div>
                        <div class="table-cell">${holding.quantity}</div>
                        <div class="table-cell">${formatCurrency(holding.average_price)}</div>
                        <div class="table-cell">${formatCurrency(holding.current_price)}</div>
                        <div class="table-cell ${holding.pnl >= 0 ? 'profit' : 'loss'}">${formatCurrency(holding.pnl)}</div>
                    </div>
                `).join('');
            } else {
                portfolioTable.innerHTML = '<div class="no-data">No holdings found</div>';
            }
        }
    } catch (error) {
        console.error('Error loading portfolio data:', error);
        const portfolioTable = document.getElementById('portfolioTable');
        if (portfolioTable) {
            portfolioTable.innerHTML = '<div class="no-data">No holdings found</div>';
        }
    }
}

async function loadOrdersData() {
    try {
        const response = await fetch('/api/orders');
        const data = await response.json();
        
        const ordersTable = document.getElementById('allOrdersTable');
        if (ordersTable) {
            if (data.success && data.orders && data.orders.length > 0) {
                ordersTable.innerHTML = data.orders.map(order => `
                    <div class="table-row">
                        <div class="table-cell">${order.symbol}</div>
                        <div class="table-cell ${order.action.toLowerCase()}">${order.action}</div>
                        <div class="table-cell">${order.quantity}</div>
                        <div class="table-cell">${order.order_type}</div>
                        <div class="table-cell">${formatCurrency(order.price || 0)}</div>
                        <div class="table-cell">${order.status}</div>
                        <div class="table-cell">${new Date(order.timestamp).toLocaleString()}</div>
                    </div>
                `).join('');
            } else {
                ordersTable.innerHTML = '<div class="no-data">No orders found</div>';
            }
        }
    } catch (error) {
        console.error('Error loading orders data:', error);
        const ordersTable = document.getElementById('allOrdersTable');
        if (ordersTable) {
            ordersTable.innerHTML = '<div class="no-data">No orders found</div>';
        }
    }
}

async function loadPositionsData() {
    try {
        const response = await fetch('/api/positions');
        const data = await response.json();
        
        const positionsTable = document.getElementById('positionsTable');
        if (positionsTable) {
            if (data.success && data.positions && data.positions.length > 0) {
                positionsTable.innerHTML = data.positions.map(position => `
                    <div class="table-row">
                        <div class="table-cell">${position.symbol}</div>
                        <div class="table-cell">${position.quantity}</div>
                        <div class="table-cell">${formatCurrency(position.average_price)}</div>
                        <div class="table-cell">${formatCurrency(position.current_price)}</div>
                        <div class="table-cell ${position.pnl >= 0 ? 'profit' : 'loss'}">${formatCurrency(position.pnl)}</div>
                        <div class="table-cell">${position.product}</div>
                    </div>
                `).join('');
            } else {
                positionsTable.innerHTML = '<div class="no-data">No open positions</div>';
            }
        }
    } catch (error) {
        console.error('Error loading positions data:', error);
        const positionsTable = document.getElementById('positionsTable');
        if (positionsTable) {
            positionsTable.innerHTML = '<div class="no-data">No open positions</div>';
        }
    }
}

async function loadWatchlistData() {
    const watchlistTable = document.getElementById('watchlistTable');
    if (watchlistTable) {
        watchlistTable.innerHTML = '<div class="no-data">Watchlist is empty</div>';
    }
}

async function loadAnalyticsData() {
    updateElement('totalTrades', '--');
    updateElement('winRate', '--');
    updateElement('avgReturn', '--');
    updateElement('maxDrawdown', '--');
}

// Market data updates
function updateMarketData(data) {
    if (data.indices) {
        updateElement('niftyValue', data.indices.nifty?.value || '--');
        updateElement('niftyChange', data.indices.nifty?.change || '--');
        updateElement('sensexValue', data.indices.sensex?.value || '--');
        updateElement('sensexChange', data.indices.sensex?.change || '--');
        updateElement('bankniftyValue', data.indices.banknifty?.value || '--');
        updateElement('bankniftyChange', data.indices.banknifty?.change || '--');
    }
}

// Utility Functions
function updateElement(id, value) {
    const element = document.getElementById(id);
    if (element) {
        element.textContent = value;
    }
}

function formatCurrency(amount) {
    return new Intl.NumberFormat('en-IN', {
        style: 'currency',
        currency: 'INR',
        minimumFractionDigits: 2
    }).format(amount);
}

function showToast(message, type = 'info') {
    const toastId = type === 'error' ? 'errorToast' : 'successToast';
    const messageId = type === 'error' ? 'errorMessage' : 'successMessage';
    
    const toast = document.getElementById(toastId);
    const messageElement = document.getElementById(messageId);
    
    if (toast && messageElement) {
        messageElement.textContent = message;
        toast.style.display = 'block';
        toast.classList.add('show');
        
        setTimeout(() => {
            hideToast(type);
        }, 5000);
    }
}

function hideToast(type) {
    const toastId = type === 'error' ? 'errorToast' : 'successToast';
    const toast = document.getElementById(toastId);
    
    if (toast) {
        toast.classList.remove('show');
        setTimeout(() => {
            toast.style.display = 'none';
        }, 300);
    }
}

function showError(elementId, message) {
    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = message;
    }
}

function showLoading(show) {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.style.display = show ? 'flex' : 'none';
    }
}

// Auto-refresh data every 30 seconds
setInterval(() => {
    if (isLoggedIn && currentTab === 'overview') {
        loadOverviewData();
    }
}, 30000);
    
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
        showToast('Connection lost', 'error');
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
        updatePositions(data);
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
    
    // Trade history controls
    const clearHistoryBtn = document.getElementById('clearHistoryBtn');
    if (clearHistoryBtn) {
        clearHistoryBtn.addEventListener('click', clearTradeHistory);
    }
    
    const historyFilter = document.getElementById('historyFilter');
    if (historyFilter) {
        historyFilter.addEventListener('change', handleHistoryFilter);
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
        await fetch('/logout', { method: 'POST' });
        sessionStorage.removeItem('loginToken');
        isLoggedIn = false;
        showLoginModal();
        showToast('Logged out successfully', 'info');
    } catch (error) {
        console.error('Logout error:', error);
    }
}

function loadInitialData() {
    loadMarketStatus();
    loadWalletInfo();
    loadTradeHistory();
    loadPositions();
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
            const response = await fetch('/api/start-option-chain', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    symbol: 'NIFTY',
                    expiry: expiries[0]
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
                    expirySelect.innerHTML = `<option value="${expiries[0]}" selected>${expiries[0]}</option>`;
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
        
        expirySelect.innerHTML = '<option value="">Select Expiry</option>';
        
        expiries.forEach(expiry => {
            const option = document.createElement('option');
            option.value = expiry;
            option.textContent = expiry;
            expirySelect.appendChild(option);
        });
        
        if (expiries.length > 0) {
            expirySelect.value = expiries[0];
            currentExpiry = expiries[0];
        }
    } catch (error) {
        console.error('Error loading expiry list:', error);
        showToast('Failed to load expiry list', 'error');
    }
}

function handleExpiryChange() {
    const expirySelect = document.getElementById('expirySelect');
    currentExpiry = expirySelect.value;
}

function handleRefreshIntervalChange() {
    const refreshSlider = document.getElementById('refreshInterval');
    const refreshValue = document.getElementById('refreshValue');
    
    refreshInterval = parseInt(refreshSlider.value);
    refreshValue.textContent = refreshInterval + 's';
    
    // Restart refresh timer with new interval
    if (refreshTimer) {
        clearInterval(refreshTimer);
    }
    startRealtimeUpdates();
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
            if (id === 'walletPositions') {
                element.textContent = `${data.total_positions} Active`;
            } else {
                element.textContent = `₹${formatNumber(value)}`;
            }
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
    
    container.innerHTML = '';
    
    options.slice(0, 5).forEach((option, index) => {
        console.log(`Creating option item ${index} for ${containerId}:`, option);
        const optionItem = createOptionItem(option, optionType);
        container.appendChild(optionItem);
    });
    
    console.log(`Updated ${containerId} with ${container.children.length} option items`);
}

function createOptionItem(option, optionType) {
    const div = document.createElement('div');
    div.className = 'option-item';
    
    const strike = option.strike;
    const price = option.ltp || 0;
    const bid = option.bid || 0;
    const ask = option.ask || 0;
    const lotSize = lotSizes[currentSymbol] || 75;
    
    div.innerHTML = `
        <div class="option-header">
            <span class="option-strike">${strike}</span>
            <span class="option-price">₹${price.toFixed(2)}</span>
        </div>
        <div class="option-controls">
            <input type="number" class="lots-input" value="1" min="1" max="10" id="lots_${strike}_${optionType}">
            <button class="btn btn-primary btn-buy" onclick="buyOptionWithLots(${strike}, '${optionType}', ${price}, 'lots_${strike}_${optionType}')">🟢 Buy</button>
            <button class="btn btn-danger btn-sell" onclick="sellOption(${strike}, '${optionType}', ${price})">🔴 Sell</button>
        </div>
        <div class="qty-info">${lotSize} qty</div>
        ${bid > 0 || ask > 0 ? `<div class="option-details">Bid: ₹${bid.toFixed(1)} | Ask: ₹${ask.toFixed(1)}</div>` : ''}
    `;
    
    return div;
}

async function buyOptionWithLots(strike, optionType, price, lotsInputId) {
    const lotsInput = document.getElementById(lotsInputId);
    const lots = lotsInput ? parseInt(lotsInput.value) : 1;
    
    await buyOption(strike, optionType, price, lots);
}

function updateAtmOptions(atmOptions, atmStrike) {
    const container = document.getElementById('atmOptions');
    if (!container) return;
    
    if (!atmOptions || atmOptions.length === 0) {
        container.innerHTML = '<div class="info-message">No ATM options</div>';
        return;
    }
    
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
    // Check if trading is ready
    if (!tradingReady || !zerodhaConnected) {
        showToast('❌ Trading not ready. Please complete Zerodha setup first.', 'error');
        return;
    }
    
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
        
        if (data.success) {
            showToast(`🚀 ${data.message}`, 'success');
            if (data.order_id) {
                console.log('Order ID:', data.order_id);
            }
        } else {
            showToast(`❌ ${data.message}`, 'error');
        }
    } catch (error) {
        console.error('Error buying option:', error);
        showToast('❌ Failed to place buy order', 'error');
    }
}

async function sellOption(strike, optionType, price) {
    // Check if trading is ready
    if (!tradingReady || !zerodhaConnected) {
        showToast('❌ Trading not ready. Please complete Zerodha setup first.', 'error');
        return;
    }
    
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
        
        if (data.success) {
            showToast(data.message, 'success');
        } else {
            showToast(data.message, 'error');
        }
    } catch (error) {
        console.error('Error selling option:', error);
        showToast('Failed to sell option', 'error');
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

function updatePositions(positions) {
    const container = document.getElementById('positionsTable');
    if (!container) return;
    
    if (!positions || positions.length === 0) {
        container.innerHTML = '<div class="info-message">No open positions</div>';
        return;
    }
    
    let html = `
        <div class="position-row position-header">
            <div>Strike</div>
            <div>Type</div>
            <div>Qty</div>
            <div>First Buy ₹</div>
            <div>Buy ₹</div>
            <div>Current ₹</div>
            <div>Stop ₹</div>
            <div>P&L ₹</div>
            <div>P&L%</div>
            <div>Mode</div>
            <div>Sell</div>
        </div>
    `;
    
    positions.forEach(position => {
        const pnlClass = position.pnl > 0 ? 'profit' : position.pnl < 0 ? 'loss' : '';
        
        html += `
            <div class="position-row ${pnlClass}">
                <div>${position.strike}</div>
                <div>${position.type}</div>
                <div>${position.qty}</div>
                <div>₹${position.first_buy_price?.toFixed(2) || position.buy_price.toFixed(2)}</div>
                <div>₹${position.buy_price.toFixed(2)}</div>
                <div>₹${position.current_price.toFixed(2)}</div>
                <div>₹${position.stop_loss_price.toFixed(2)}</div>
                <div class="${pnlClass}">₹${position.pnl.toFixed(2)}</div>
                <div class="${pnlClass}">${position.pnl_percent.toFixed(2)}%</div>
                <div>${position.mode}</div>
                <div>
                    ${position.mode === 'Running' ? 
                        `<button class="btn btn-danger" onclick="sellPosition(${position.strike}, '${position.type}', ${position.current_price})">Sell</button>` :
                        '<span>-</span>'
                    }
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

async function sellPosition(strike, optionType, price) {
    await sellOption(strike, optionType, price);
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

async function resetStopLoss() {
    showToast('Stop loss reset functionality coming soon', 'info');
}

function handlePositionFilter() {
    // Position filtering logic would go here
    loadPositions();
}

async function loadTradeHistory() {
    try {
        const response = await fetch('/api/trade-history');
        const data = await response.json();
        updateTradeHistory(data);
    } catch (error) {
        console.error('Error loading trade history:', error);
    }
}

function updateTradeHistory(history) {
    if (!history || history.length === 0) {
        document.getElementById('tradeHistoryList').innerHTML = '<div class="info-message">No trades yet</div>';
        updateHistorySummary([]);
        return;
    }
    
    updateHistorySummary(history);
    
    const container = document.getElementById('tradeHistoryList');
    if (!container) return;
    
    container.innerHTML = '';
    
    // Show last 10 trades in reverse order (most recent first)
    const recentTrades = history.slice(-10).reverse();
    
    recentTrades.forEach(trade => {
        const div = document.createElement('div');
        div.className = 'history-item';
        
        if (trade.action === 'Buy') {
            div.classList.add('buy');
        } else if (trade.pnl > 0) {
            div.classList.add('profit');
        } else if (trade.pnl < 0) {
            div.classList.add('loss');
        }
        
        const pnlText = trade.action === 'Buy' ? '' : ` | P&L: ₹${trade.pnl.toFixed(2)}`;
        
        div.innerHTML = `
            <div class="history-header">
                ${getTradeIcon(trade)} ${trade.action} - ${trade.type} ${trade.strike}
            </div>
            <div class="history-details">
                Qty: ${trade.qty} | Price: ₹${trade.price.toFixed(2)}${pnlText}<br>
                Time: ${trade.time}
            </div>
        `;
        
        container.appendChild(div);
    });
}

function getTradeIcon(trade) {
    if (trade.action === 'Buy') return '🟢';
    if (trade.action === 'Stop Loss Sell') return '🛑';
    if (trade.action === 'Auto Buy') return '🤖';
    if (trade.pnl > 0) return '💰';
    if (trade.pnl < 0) return '🔴';
    return '⚪';
}

function updateHistorySummary(history) {
    const totalTrades = history.length;
    const buyTrades = history.filter(t => t.action === 'Buy').length;
    const sellTrades = totalTrades - buyTrades;
    const totalPnl = history.filter(t => t.action !== 'Buy').reduce((sum, t) => sum + (t.pnl || 0), 0);
    
    document.getElementById('totalTrades').textContent = totalTrades;
    document.getElementById('buyTrades').textContent = buyTrades;
    document.getElementById('sellTrades').textContent = sellTrades;
    document.getElementById('historyTotalPnl').textContent = `₹${formatNumber(totalPnl)}`;
}

async function clearTradeHistory() {
    if (!confirm('Are you sure you want to clear trade history?')) {
        return;
    }
    
    try {
        const response = await fetch('/api/clear-history', {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('Trade history cleared', 'success');
            loadTradeHistory();
        } else {
            showToast('Failed to clear history', 'error');
        }
    } catch (error) {
        console.error('Error clearing history:', error);
        showToast('Failed to clear history', 'error');
    }
}

function handleHistoryFilter() {
    // History filtering logic would go here
    loadTradeHistory();
}

function updateCurrentTime() {
    const now = new Date();
    const timeString = now.toLocaleTimeString();
    const timeElement = document.getElementById('currentTime');
    if (timeElement) {
        timeElement.textContent = timeString;
    }
}

function showLoading(show) {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.style.display = show ? 'flex' : 'none';
    }
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    if (!container) return;
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    
    container.appendChild(toast);
    
    // Remove toast after 3 seconds
    setTimeout(() => {
        if (toast.parentNode) {
            toast.parentNode.removeChild(toast);
        }
    }, 3000);
}

function formatNumber(num) {
    if (num >= 10000000) {
        return (num / 10000000).toFixed(2) + 'Cr';
    } else if (num >= 100000) {
        return (num / 100000).toFixed(2) + 'L';
    } else if (num >= 1000) {
        return (num / 1000).toFixed(2) + 'K';
    } else {
        return num.toFixed(2);
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
            zerodhaModalRefreshTimer = setInterval(updateZerodhaModal, 3000);
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

// Utility functions for debugging
window.debugApp = {
    socket,
    currentSymbol,
    currentExpiry,
    refreshInterval,
    isLoggedIn,
    lotSizes
};
