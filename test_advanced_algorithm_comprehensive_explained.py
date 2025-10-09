#!/usr/bin/env python3
"""
🧪 ADVANCED ALGORITHM TEST FILE - COMPREHENSIVE TESTING WITH REAL MARKET DATA
================================================================

This test file extracts the update_advanced_Algorithm function from app.py
and provides detailed line-by-line explanations along with manual test data
that simulates real market conditions for thorough testing.

Created: September 21, 2025
Purpose: Test the 3-Phase Advanced Trading Algorithm with realistic scenarios
"""

import datetime as dt
import pandas as pd
import numpy as np
import json

# =============================================================================
# 📊 MOCK DATA AND HELPER FUNCTIONS (Extracted from app.py)
# =============================================================================

def execute_auto_sell(position, reason='Stop Loss'):
    """
    Mock function for auto sell execution during testing
    
    Explanation:
    - Simulates the sell execution without actual trading
    - Updates position status for auto-buy monitoring
    - Calculates P&L and updates position state
    """
    print(f"🔴 MOCK AUTO SELL: {position['strike']} {position['type']} @ ₹{position['current_price']} | Reason: {reason}")
    
    # Calculate P&L
    buy_price = position.get('buy_price', position.get('original_buy_price', 0))
    sell_price = position['current_price']
    quantity = position.get('qty', position.get('quantity', 105))  # Default NIFTY lot size
    pnl = (sell_price - buy_price) * quantity
    
    print(f"   P&L: (₹{sell_price} - ₹{buy_price}) × {quantity} = ₹{pnl:.2f}")
    
    # Mark position as sold and waiting for auto buy
    position['sell_triggered'] = True
    position['waiting_for_autobuy'] = True
    position['realized_pnl'] = pnl
    position['quantity'] = 0  # Show as sold
    
    return True

def execute_auto_buy(position):
    """
    Mock function for auto buy execution during testing
    
    Explanation:
    - Simulates the buy execution without actual trading
    - Resets position for continued monitoring
    - Handles phase-specific buy price logic
    """
    # Determine buy price based on phase
    if position.get('algorithm_phase', 1) == 1:
        # Phase 1: Buy at manual buy price (original price)
        buy_price = position.get('manual_buy_price', position.get('original_buy_price'))
        print(f"🟢 MOCK AUTO BUY (Phase 1): {position['strike']} {position['type']} @ ₹{buy_price} (manual price)")
    else:
        # Phase 2&3: Buy at current market price
        buy_price = position['current_price']
        print(f"🟢 MOCK AUTO BUY (Phase {position.get('algorithm_phase', 1)}): {position['strike']} {position['type']} @ ₹{buy_price} (market price)")
    
    # Update position state
    position['buy_price'] = buy_price
    position['original_buy_price'] = buy_price
    position['sell_triggered'] = False
    position['waiting_for_autobuy'] = False
    position['quantity'] = 105  # Restore quantity
    position['auto_buy_count'] = position.get('auto_buy_count', 0) + 1
    
    return True

# =============================================================================
# 🎯 MAIN ADVANCED ALGORITHM FUNCTION (Extracted from app.py with explanations)
# =============================================================================

def update_advanced_algorithm(position, new_price):
    """
    🚨 NEW Advanced algorithm: 3-Phase Logic with detailed explanations
    
    PHASE OVERVIEW:
    🚨 PHASE 1 (Buy to Buy+20): SL = Buy-10, Auto buy at SAME buy price
    🚨 PHASE 2 (Buy+20 to Buy+30): Progressive Min activated, SL = High-10
    🚨 PHASE 3 (After Buy+30): Step-wise algorithm like Simple
    
    EXAMPLE WALKTHROUGH:
    Phase 1: Buy ₹100 → SL ₹90, Auto buy at ₹100 (not sell price)
    Phase 2: Price ₹120 → SL ₹110, Progressive Min ₹100, Auto buy ₹110 → SL ₹100
    Phase 3: Price ₹130 → Step algorithm: SL = 100 + (3×10) = ₹130
    
    Args:
        position (dict): Position dictionary with all required fields
        new_price (float): Current market price to update position with
    
    Returns:
        bool: True if any action was taken (sell/buy), False otherwise
    """
    
    # =========================================================================
    # 📝 STEP 1: DEBUG LOGGING AND PRICE UPDATE
    # =========================================================================
    print(f"[DEBUG] NEW ADVANCED ALGORITHM CALLED for {position.get('strike', '?')} {position.get('type', '?')} | Price: {new_price}")
    # Explanation: Log the algorithm call with position details for debugging
    
    old_price = float(position['current_price'])
    # Explanation: Store the previous price for comparison and analysis
    
    position['current_price'] = new_price
    # Explanation: Update the position with the new market price
    
    position['last_update'] = dt.datetime.now()
    # Explanation: Record the timestamp of this price update for tracking
    
    # =========================================================================
    # 📝 STEP 2: INITIALIZE REQUIRED FIELDS FOR ADVANCED ALGORITHM
    # =========================================================================
    
    # Initialize original_buy_price (the very first buy price - never changes)
    if 'original_buy_price' not in position:
        position['original_buy_price'] = position.get('buy_price', position.get('average_price', new_price))
        # Explanation: Set the original buy price as anchor point for all calculations
    
    # Initialize manual_buy_price (manual buy price - only changes in Phase 1 auto-buy)
    if 'manual_buy_price' not in position:
        position['manual_buy_price'] = position.get('buy_price', position.get('average_price', new_price))
        # Explanation: This is the manual buy price that serves as the anchor for Phase 1 logic
    
    # Initialize highest_price (tracks the highest price achieved)
    if 'highest_price' not in position:
        position['highest_price'] = position['original_buy_price']
        # Explanation: Track highest price for trailing stop loss calculations
    
    # Initialize advanced_stop_loss (the calculated stop loss based on algorithm)
    if 'advanced_stop_loss' not in position:
        position['advanced_stop_loss'] = position['original_buy_price'] - 10
        # Explanation: Set initial stop loss 10 points below buy price
    
    # Initialize algorithm_phase (current phase: 1, 2, or 3)
    if 'algorithm_phase' not in position:
        position['algorithm_phase'] = 1
        # Explanation: Start in Phase 1 (initial phase from buy to buy+20)
    
    # Initialize progressive_minimum (activated in Phase 2, protects gains)
    if 'progressive_minimum' not in position:
        position['progressive_minimum'] = None
        # Explanation: Progressive minimum is not active initially, only in Phase 2+
    
    # Initialize highest_stop_loss (tracks the highest stop loss ever achieved)
    if 'highest_stop_loss' not in position:
        position['highest_stop_loss'] = position['original_buy_price'] - 10
        # Explanation: Track the highest stop loss for progressive minimum calculation
    
    # =========================================================================
    # 📝 STEP 3: EXTRACT KEY VARIABLES FOR CALCULATIONS
    # =========================================================================
    
    original_buy_price = position['original_buy_price']
    # Explanation: The very first buy price, used for overall P&L calculation
    
    manual_buy_price = position['manual_buy_price']
    # Explanation: The manual buy price (anchor), only changes in Phase 1 auto-buy
    
    current_phase = position['algorithm_phase']
    # Explanation: Current algorithm phase for debugging and logic flow
    
    # =========================================================================
    # 📝 STEP 4: DETERMINE CURRENT PHASE BASED ON PRICE LEVELS
    # =========================================================================
    
    price_above_buy = new_price - manual_buy_price
    # Explanation: Calculate how much current price is above the manual buy price
    
    if price_above_buy < 20:
        position['algorithm_phase'] = 1  # Phase 1: Below Buy+20
        # Explanation: If price is less than 20 points above buy, stay in Phase 1
    elif price_above_buy < 30:
        position['algorithm_phase'] = 2  # Phase 2: Buy+20 to Buy+30
        # Explanation: If price is 20-30 points above buy, move to Phase 2
    else:
        position['algorithm_phase'] = 3  # Phase 3: Above Buy+30
        # Explanation: If price is more than 30 points above buy, move to Phase 3
    
    print(f"🔄 PHASE {position['algorithm_phase']}: Manual Buy ₹{manual_buy_price} | Current ₹{new_price} | Above Buy: +₹{price_above_buy:.2f}")
    # Explanation: Log the current phase and price relationship for debugging
    
    # =========================================================================
    # 📝 STEP 5: PHASE 1 LOGIC (Buy to Buy+20)
    # =========================================================================
    if position['algorithm_phase'] == 1:
        print("📍 ENTERING PHASE 1 LOGIC")
        
        # Update highest price for trailing calculations
        if new_price > position['highest_price']:
            position['highest_price'] = new_price
            # Explanation: Track the highest price reached for trailing stop loss
        
        # Clear progressive minimum in Phase 1 (not active yet)
        position['progressive_minimum'] = None
        # Explanation: Progressive minimum is only active in Phase 2 and 3
        
        # Calculate profit from manual buy price
        profit = position['highest_price'] - manual_buy_price
        # Explanation: Profit is calculated from the highest price achieved
        
        trailing_step = 10  # Fixed ₹10 steps
        # Explanation: Stop loss moves in 10 rupee increments
        
        if profit >= 10:
            # If profit is at least 10, apply trailing stop loss
            profit_steps = int(profit // trailing_step)
            # Explanation: Calculate how many 10-rupee steps of profit we have
            
            trailing_stop_loss = manual_buy_price + (profit_steps * trailing_step)
            # Explanation: Trailing stop = buy price + (profit steps × 10)
            
            minimum_sl = manual_buy_price - 10
            # Explanation: Minimum stop loss is always buy price minus 10
            
            position['advanced_stop_loss'] = max(trailing_stop_loss, minimum_sl)
            # Explanation: Use the higher of trailing stop or minimum stop loss
            
            print(f"📍 PHASE 1 TRAILING: Buy ₹{manual_buy_price} | High ₹{position['highest_price']} | Profit ₹{profit:.2f} | Steps {profit_steps}")
            print(f"   SL = ₹{manual_buy_price} + ({profit_steps}×10) = ₹{trailing_stop_loss} | Final SL ₹{position['advanced_stop_loss']}")
        else:
            # If profit is less than 10, use simple stop loss
            position['advanced_stop_loss'] = manual_buy_price - 10
            # Explanation: Simple stop loss 10 points below buy price
            
            print(f"📍 PHASE 1: Simple SL = ₹{manual_buy_price} - 10 = ₹{position['advanced_stop_loss']}")
    
    # =========================================================================
    # 📝 STEP 6: PHASE 2 LOGIC (Buy+20 to Buy+30 - Progressive Minimum Activation)
    # =========================================================================
    elif position['algorithm_phase'] == 2:
        print("📍 ENTERING PHASE 2 LOGIC")
        
        # Update highest price
        if new_price > position['highest_price']:
            position['highest_price'] = new_price
            # Explanation: Continue tracking highest price for trailing calculations
        
        # Activate progressive minimum if not set (first time in Phase 2)
        if position['progressive_minimum'] is None:
            position['progressive_minimum'] = manual_buy_price
            # Explanation: Set progressive minimum to manual buy price to protect gains
            print(f"🚨 PROGRESSIVE MINIMUM ACTIVATED: ₹{position['progressive_minimum']}")
        
        # Calculate profit and apply step-wise trailing
        profit = position['highest_price'] - manual_buy_price
        # Explanation: Calculate profit from highest price achieved
        
        trailing_step = 10
        # Explanation: Continue using 10-rupee steps
        
        if profit >= 10:
            profit_steps = int(profit // trailing_step)
            # Explanation: Calculate profit steps for trailing stop loss
            
            step_stop_loss = manual_buy_price + (profit_steps * trailing_step)
            # Explanation: Calculate step-wise stop loss
        else:
            step_stop_loss = manual_buy_price - 10  # fallback, but clamped by PM below
            # Explanation: Fallback stop loss, but will be overridden by progressive minimum
        
        # Final SL = max(step SL, progressive min) - Progressive minimum protects gains
        position['advanced_stop_loss'] = max(step_stop_loss, position['progressive_minimum'])
        # Explanation: Stop loss cannot fall below progressive minimum (gain protection)
        
        print(f"📍 PHASE 2: Buy ₹{manual_buy_price} | High ₹{position['highest_price']} | Profit ₹{profit:.2f} | Steps {profit_steps if profit >= 10 else 0}")
        print(f"   SL = ₹{step_stop_loss} | Progressive Min ₹{position['progressive_minimum']} → Final SL ₹{position['advanced_stop_loss']}")
    
    # =========================================================================
    # 📝 STEP 7: PHASE 3 LOGIC (After Buy+30 - Full Step-wise Algorithm)
    # =========================================================================
    elif position['algorithm_phase'] == 3:
        print("📍 ENTERING PHASE 3 LOGIC")
        
        # Update highest price
        if new_price > position['highest_price']:
            position['highest_price'] = new_price
            # Explanation: Continue tracking highest price for advanced trailing
        
        # Calculate profit and apply full step-wise algorithm
        profit = position['highest_price'] - manual_buy_price
        # Explanation: Calculate total profit from manual buy price
        
        trailing_step = 10
        # Explanation: Maintain 10-rupee step increments
        
        if profit >= 30:
            profit_steps = int(profit // trailing_step)
            # Explanation: Calculate profit steps (should be at least 3 in Phase 3)
            
            step_stop_loss = manual_buy_price + (profit_steps * trailing_step)
            # Explanation: Full step-wise algorithm: buy + (steps × 10)
        else:
            # Shouldn't happen in Phase 3, but safe fallback
            step_stop_loss = manual_buy_price + 20  # min SL in Phase 3
            # Explanation: Safety fallback - minimum stop loss in Phase 3
        
        # Ensure progressive minimum is set (should already be set from Phase 2)
        if position['progressive_minimum'] is None:
            position['progressive_minimum'] = manual_buy_price
            # Explanation: Safety check - ensure progressive minimum exists
        
        # Final SL = max(step SL, progressive min) - Full protection
        position['advanced_stop_loss'] = max(step_stop_loss, position['progressive_minimum'])
        # Explanation: Stop loss uses the higher of step calculation or progressive minimum
        
        print(f"📍 PHASE 3: Profit ₹{profit:.2f} → Steps {profit_steps if profit >= 30 else 0} → SL = ₹{step_stop_loss}")
        print(f"   Progressive Min ₹{position['progressive_minimum']} → Final SL ₹{position['advanced_stop_loss']}")
    
    # =========================================================================
    # 📝 STEP 8: UPDATE HIGHEST STOP LOSS & PROGRESSIVE MINIMUM (Phase 2 & 3)
    # =========================================================================
    if position['algorithm_phase'] in [2, 3]:
        # Check if current stop loss is higher than ever achieved
        if position['advanced_stop_loss'] > position.get('highest_stop_loss', 0):
            position['highest_stop_loss'] = position['advanced_stop_loss']
            # Explanation: Track the highest stop loss ever achieved
            
            new_pm = position['highest_stop_loss'] - 20
            # Explanation: Progressive minimum = highest stop loss - 20
            
            # Update progressive minimum only if higher (make it sticky floor)
            if position['progressive_minimum'] is None or new_pm > position['progressive_minimum']:
                position['progressive_minimum'] = new_pm
                # Explanation: Progressive minimum only moves up, never down (sticky floor)
                print(f"📈 PROGRESSIVE MIN UPDATED → ₹{position['progressive_minimum']} (Highest SL ₹{position['highest_stop_loss']} - 20)")
    
    # =========================================================================
    # 📝 STEP 9: UPDATE TRADITIONAL STOP LOSS FOR DISPLAY
    # =========================================================================
    position['stop_loss_price'] = position['advanced_stop_loss']
    # Explanation: Update the traditional stop loss field for UI compatibility
    
    # =========================================================================
    # 📝 STEP 10: COMPREHENSIVE DEBUG MONITORING
    # =========================================================================
    print(f"🔍 MONITORING: Phase {position['algorithm_phase']} | Current: ₹{new_price} | Advanced SL: ₹{position['advanced_stop_loss']} | Progressive Min: ₹{position.get('progressive_minimum', 'N/A')} | Highest SL: ₹{position.get('highest_stop_loss', 'N/A')}")
    # Explanation: Comprehensive debug output showing all key metrics
    
    # =========================================================================
    # 📝 STEP 11: CHECK FOR STOP LOSS TRIGGER (AUTO SELL)
    # =========================================================================
    if (position['current_price'] <= position['advanced_stop_loss'] and 
        position['advanced_stop_loss'] > 0 and 
        not position.get('waiting_for_autobuy', False) and
        not position.get('sell_triggered', False)):
        
        # Calculate profit for logging
        profit = position['current_price'] - original_buy_price
        # Explanation: Calculate P&L from original buy price
        
        reason = 'Advanced Trailing Stop Loss' if profit > 0 else 'Advanced Stop Loss'
        # Explanation: Determine if it's a profit-taking or loss-cutting sell
        
        print(f"🚨 ADVANCED STOP LOSS TRIGGERED @ ₹{new_price} (Stop Loss: ₹{position['advanced_stop_loss']}, Profit: ₹{profit:.2f})")
        
        # Execute the auto sell
        sell_executed = execute_auto_sell(position, reason=reason)
        # Explanation: Execute the automatic sell order
        
        if sell_executed:
            position['sell_triggered'] = True
            position['waiting_for_autobuy'] = True
            # Explanation: Mark position as sold and waiting for auto buy trigger
            
            # Preserve manual_buy_price for Phase 1 auto buy
            if 'manual_buy_price' not in position:
                position['manual_buy_price'] = position.get('original_buy_price', position.get('buy_price', new_price))
                print(f"🔧 PRESERVED: manual_buy_price = ₹{position['manual_buy_price']}")
                # Explanation: Ensure manual buy price is preserved for auto buy logic
            
            # Set auto buy trigger based on phase
            if position['algorithm_phase'] == 1:
                # Phase 1: Auto buy at SAME manual buy price
                position['last_stop_loss_price'] = position['manual_buy_price']
                print(f"🎯 PHASE 1 AUTO BUY: Will buy at manual buy price ₹{position['manual_buy_price']}")
                # Explanation: In Phase 1, auto buy at the original manual buy price
            else:
                # Phase 2 & 3: Auto buy at SELL PRICE
                position['last_stop_loss_price'] = position['current_price']
                print(f"🎯 PHASE {position['algorithm_phase']} AUTO BUY: Will buy at sell price ₹{position['current_price']}")
                # Explanation: In Phase 2&3, auto buy at the price where we sold
            
            position['mode'] = f'Waiting for Auto Buy (Advanced Phase {position["algorithm_phase"]})'
            # Explanation: Update position mode for UI display
            
            return True
        return False
    
    # =========================================================================
    # 📝 STEP 12: CHECK FOR AUTO BUY TRIGGER
    # =========================================================================
    auto_buy_trigger = position.get('last_stop_loss_price', 0)
    # Explanation: Get the price level that will trigger auto buy
    
    if (position.get('waiting_for_autobuy', False) and 
        position['current_price'] >= auto_buy_trigger):
        
        print(f"🎯 ADVANCED AUTO BUY TRIGGER (Phase {position['algorithm_phase']}) | Current: ₹{position['current_price']} | Trigger: ₹{auto_buy_trigger}")
        
        # Execute auto buy
        buy_executed = execute_auto_buy(position)
        # Explanation: Execute the automatic buy order
        
        if buy_executed:
            actual_buy_price = position['buy_price']  # Get the actual price we bought at
            # Explanation: Get the actual execution price
            
            position['original_buy_price'] = actual_buy_price
            position['sell_triggered'] = False
            position['waiting_for_autobuy'] = False
            # Explanation: Reset position state for new monitoring cycle
            
            # Phase-specific reset logic
            if position['algorithm_phase'] == 1:
                position['highest_price'] = actual_buy_price
                position['manual_buy_price'] = actual_buy_price  # 🔄 SYNC in Phase 1
                position['progressive_minimum'] = None
                print(f"🔁 PHASE 1 RESET: manual_buy_price updated to ₹{actual_buy_price}, progressive_min cleared")
                # Explanation: In Phase 1, sync manual buy price with new buy price
            else:
                position['highest_price'] = actual_buy_price
                # manual_buy_price remains unchanged (anchor)
                print(f"🔁 PHASE {position['algorithm_phase']} RESET: manual_buy_price remains ₹{position['manual_buy_price']}, progressive_min = ₹{position['progressive_minimum']}")
                # Explanation: In Phase 2&3, keep original manual buy price as anchor
            
            print(f"🎯 ADVANCED AUTO BUY COMPLETE (Phase {position['algorithm_phase']}): Buy ₹{actual_buy_price} | Manual Buy ₹{position['manual_buy_price']} | New SL ₹{position['advanced_stop_loss']}")
            return True
        return False
    
    return False

# =============================================================================
# 🎯 MANUAL TEST DATA - REAL MARKET SCENARIOS
# =============================================================================

# Test Scenario 1: Normal profit scenario with Phase transitions
TEST_SCENARIO_1 = {
    'name': 'Normal Profit with Phase Transitions',
    'description': 'Tests normal market movement through all three phases',
    'initial_position': {
        'id': 'test_001',
        'symbol': 'NIFTY',
        'strike': 55000,
        'type': 'PE',
        'buy_price': 535.85,
        'current_price': 535.85,
        'qty': 105,  # NIFTY lot size
        'auto_bought': False,
        'waiting_for_autobuy': False,
        'sell_triggered': False,
        'mode': 'Manual Entry',
        'entry_time': dt.datetime.now()
    },
    'price_sequence': [
        535.85,  # Initial buy price
        540.00,  # Small gain (+4.15)
        545.85,  # +10 points (start trailing)
        550.00,  # +14.15 points
        555.85,  # +20 points (enter Phase 2)
        560.00,  # +24.15 points (Phase 2 continues)
        565.85,  # +30 points (enter Phase 3)
        570.00,  # +34.15 points (Phase 3)
        575.85,  # +40 points
        565.85,  # Drop to +30 (test trailing)
        560.00,  # Drop to +24.15
        555.85,  # Drop to +20 (back to Phase 2)
        545.85   # Drop to +10 (back to Phase 1)
    ]
}

# Test Scenario 2: Stop loss scenario with auto buy
TEST_SCENARIO_2 = {
    'name': 'Stop Loss and Auto Buy Cycle',
    'description': 'Tests stop loss trigger and auto buy mechanism',
    'initial_position': {
        'id': 'test_002',
        'symbol': 'BANKNIFTY',
        'strike': 51000,
        'type': 'CE',
        'buy_price': 240.50,
        'current_price': 240.50,
        'qty': 35,  # BANKNIFTY lot size
        'auto_bought': False,
        'waiting_for_autobuy': False,
        'sell_triggered': False,
        'mode': 'Manual Entry',
        'entry_time': dt.datetime.now()
    },
    'price_sequence': [
        240.50,  # Initial buy
        245.00,  # Small gain
        250.50,  # +10 points
        255.00,  # +14.50 points
        260.50,  # +20 points (Phase 2)
        250.50,  # Drop back to +10
        235.00,  # Drop to -5.50
        225.00,  # Drop to -15.50 (trigger stop loss)
        235.00,  # Recovery (auto buy trigger in Phase 1)
        245.00,  # Further recovery
        255.00   # Test new cycle
    ]
}

# Test Scenario 3: High volatility scenario
TEST_SCENARIO_3 = {
    'name': 'High Volatility Market',
    'description': 'Tests algorithm behavior in volatile market conditions',
    'initial_position': {
        'id': 'test_003',
        'symbol': 'NIFTY',
        'strike': 25000,
        'type': 'CE',
        'buy_price': 159.00,
        'current_price': 159.00,
        'qty': 105,
        'auto_bought': False,
        'waiting_for_autobuy': False,
        'sell_triggered': False,
        'mode': 'Manual Entry',
        'entry_time': dt.datetime.now()
    },
    'price_sequence': [
        159.00,  # Initial buy
        169.00,  # +10 points (Phase 1 trailing starts)
        179.00,  # +20 points (enter Phase 2)
        189.00,  # +30 points (enter Phase 3)
        199.00,  # +40 points
        185.00,  # Drop -14 from high
        175.00,  # Drop -24 from high
        165.00,  # Drop -34 from high
        155.00,  # Drop -44 from high
        149.00,  # Drop to -10 from buy (stop loss)
        159.00,  # Recovery to original buy (auto buy trigger)
        169.00,  # New cycle +10
        175.00   # New cycle +16
    ]
}

# =============================================================================
# 🧪 TEST EXECUTION FUNCTIONS
# =============================================================================

def run_single_test_scenario(scenario):
    """
    Run a single test scenario and display detailed results
    
    Args:
        scenario (dict): Test scenario with position and price sequence
    """
    print("\n" + "="*80)
    print(f"🧪 RUNNING TEST: {scenario['name']}")
    print(f"📝 DESCRIPTION: {scenario['description']}")
    print("="*80)
    
    # Initialize test position
    position = scenario['initial_position'].copy()
    
    print(f"📍 INITIAL POSITION:")
    print(f"   Symbol: {position['symbol']} {position['strike']} {position['type']}")
    print(f"   Buy Price: ₹{position['buy_price']}")
    print(f"   Quantity: {position['qty']}")
    print(f"   Total Investment: ₹{position['buy_price'] * position['qty']:,.2f}")
    
    # Track test results
    actions_taken = []
    phase_transitions = []
    
    # Process each price in the sequence
    for step, price in enumerate(scenario['price_sequence']):
        print(f"\n--- STEP {step + 1}: Market Price = ₹{price} ---")
        
        # Record phase before update
        old_phase = position.get('algorithm_phase', 1)
        
        # Update algorithm with new price
        action_taken = update_advanced_algorithm(position, price)
        
        # Record phase after update
        new_phase = position.get('algorithm_phase', 1)
        
        # Check for phase transition
        if old_phase != new_phase:
            transition = f"Phase {old_phase} → Phase {new_phase} @ ₹{price}"
            phase_transitions.append(transition)
            print(f"🔄 PHASE TRANSITION: {transition}")
        
        # Record any actions taken
        if action_taken:
            if position.get('sell_triggered', False):
                actions_taken.append(f"SELL @ ₹{price} (Step {step + 1})")
            elif position.get('waiting_for_autobuy', False) and not position.get('sell_triggered', False):
                actions_taken.append(f"AUTO BUY @ ₹{price} (Step {step + 1})")
        
        # Display current position status
        print(f"💹 POSITION STATUS:")
        print(f"   Current Price: ₹{position['current_price']}")
        print(f"   Phase: {position.get('algorithm_phase', 1)}")
        print(f"   Stop Loss: ₹{position.get('advanced_stop_loss', 'N/A')}")
        print(f"   Progressive Min: ₹{position.get('progressive_minimum', 'N/A')}")
        print(f"   Highest Price: ₹{position.get('highest_price', 'N/A')}")
        print(f"   Mode: {position.get('mode', 'Running')}")
        
        # Calculate unrealized P&L
        if position.get('quantity', position.get('qty', 0)) > 0:
            buy_price = position.get('buy_price', position.get('original_buy_price', 0))
            unrealized_pnl = (position['current_price'] - buy_price) * position.get('quantity', position.get('qty', 0))
            print(f"   Unrealized P&L: ₹{unrealized_pnl:,.2f}")
    
    # Test summary
    print(f"\n🏁 TEST SUMMARY: {scenario['name']}")
    print(f"📊 Phase Transitions: {len(phase_transitions)}")
    for transition in phase_transitions:
        print(f"   • {transition}")
    
    print(f"🎯 Actions Taken: {len(actions_taken)}")
    for action in actions_taken:
        print(f"   • {action}")
    
    # Final position summary
    final_qty = position.get('quantity', position.get('qty', 0))
    if final_qty > 0:
        buy_price = position.get('buy_price', position.get('original_buy_price', 0))
        final_pnl = (position['current_price'] - buy_price) * final_qty
        print(f"💰 Final P&L: ₹{final_pnl:,.2f}")
    else:
        print(f"💰 Position Closed - Realized P&L: ₹{position.get('realized_pnl', 0):,.2f}")
    
    return position

def run_comprehensive_tests():
    """
    Run all test scenarios and provide comprehensive analysis
    """
    print("🚀 STARTING COMPREHENSIVE ADVANCED ALGORITHM TESTS")
    print("="*100)
    
    test_scenarios = [TEST_SCENARIO_1, TEST_SCENARIO_2, TEST_SCENARIO_3]
    results = []
    
    for scenario in test_scenarios:
        result = run_single_test_scenario(scenario)
        results.append({
            'scenario': scenario['name'],
            'final_position': result
        })
    
    # Overall test summary
    print("\n" + "="*100)
    print("📊 COMPREHENSIVE TEST RESULTS SUMMARY")
    print("="*100)
    
    for i, result in enumerate(results):
        print(f"\n{i+1}. {result['scenario']}:")
        position = result['final_position']
        
        # Calculate final status
        final_qty = position.get('quantity', position.get('qty', 0))
        if final_qty > 0:
            buy_price = position.get('buy_price', position.get('original_buy_price', 0))
            final_pnl = (position['current_price'] - buy_price) * final_qty
            status = f"OPEN - P&L: ₹{final_pnl:,.2f}"
        else:
            status = f"CLOSED - Realized P&L: ₹{position.get('realized_pnl', 0):,.2f}"
        
        print(f"   Status: {status}")
        print(f"   Final Phase: {position.get('algorithm_phase', 1)}")
        print(f"   Auto Buy Count: {position.get('auto_buy_count', 0)}")
        print(f"   Mode: {position.get('mode', 'Unknown')}")

def test_specific_price_scenario():
    """
    Test a specific price scenario mentioned by user
    This simulates the exact scenario the user might face in real trading
    """
    print("\n" + "="*80)
    print("🎯 TESTING SPECIFIC USER SCENARIO")
    print("="*80)
    
    # Real-world scenario: NIFTY 55000 PE bought at 535.85
    position = {
        'id': 'user_scenario_001',
        'symbol': 'NIFTY',
        'strike': 55000,
        'type': 'PE',
        'buy_price': 535.85,
        'current_price': 535.85,
        'qty': 105,  # 1 lot NIFTY
        'auto_bought': False,
        'waiting_for_autobuy': False,
        'sell_triggered': False,
        'mode': 'Manual Entry',
        'entry_time': dt.datetime.now()
    }
    
    print(f"📍 USER POSITION: {position['symbol']} {position['strike']} {position['type']}")
    print(f"💰 Buy Price: ₹{position['buy_price']} | Quantity: {position['qty']} lots")
    print(f"💵 Total Investment: ₹{position['buy_price'] * position['qty']:,.2f}")
    
    # Realistic price movements that might occur in real market
    price_scenarios = [
        535.85,  # Current buy price
        540.00,  # +4.15 small movement
        545.85,  # +10 exactly (trailing starts)
        550.00,  # +14.15 (still Phase 1)
        555.85,  # +20 exactly (enter Phase 2)
        560.00,  # +24.15 (Phase 2 - progressive min active)
        565.85,  # +30 exactly (enter Phase 3)
        570.00,  # +34.15 (Phase 3 full algorithm)
        562.70,  # Drop to +26.85 (test trailing in Phase 3)
        555.85,  # Drop back to +20 (back to Phase 2)
        545.85,  # Drop to +10 (back to Phase 1)
        540.00,  # Drop to +4.15
        530.00,  # Drop to -5.85
        525.85,  # Drop to -10 exactly (should trigger stop loss)
        535.85,  # Recovery to original price (auto buy trigger)
        545.85,  # New cycle +10
        555.85   # New cycle +20 (Phase 2 again)
    ]
    
    print(f"\n🔄 PROCESSING {len(price_scenarios)} PRICE MOVEMENTS...")
    
    for i, price in enumerate(price_scenarios):
        print(f"\n--- PRICE UPDATE {i+1}: ₹{price} ---")
        
        # Calculate price change from original buy
        price_change = price - 535.85
        print(f"📈 Price Change: {price_change:+.2f} points from original buy")
        
        # Update algorithm
        action_taken = update_advanced_algorithm(position, price)
        
        # Show detailed position status
        print(f"📊 DETAILED STATUS:")
        print(f"   Phase: {position.get('algorithm_phase', 1)}")
        print(f"   Current: ₹{position['current_price']}")
        print(f"   Stop Loss: ₹{position.get('advanced_stop_loss', 'N/A')}")
        print(f"   Highest: ₹{position.get('highest_price', 'N/A')}")
        print(f"   Progressive Min: ₹{position.get('progressive_minimum', 'N/A')}")
        
        # Show P&L calculation
        if position.get('quantity', position.get('qty', 0)) > 0:
            current_buy = position.get('buy_price', position.get('original_buy_price', 0))
            qty = position.get('quantity', position.get('qty', 0))
            unrealized_pnl = (position['current_price'] - current_buy) * qty
            pnl_percentage = (unrealized_pnl / (current_buy * qty)) * 100
            print(f"   Unrealized P&L: ₹{unrealized_pnl:,.2f} ({pnl_percentage:+.2f}%)")
        else:
            print(f"   Position SOLD - Realized P&L: ₹{position.get('realized_pnl', 0):,.2f}")
            if position.get('waiting_for_autobuy', False):
                auto_buy_price = position.get('last_stop_loss_price', 0)
                print(f"   🎯 Auto Buy will trigger at: ₹{auto_buy_price}")
        
        # Alert on important events
        if action_taken:
            if position.get('sell_triggered', False) and position.get('waiting_for_autobuy', False):
                print(f"🚨 STOP LOSS TRIGGERED! Position sold at ₹{price}")
            elif not position.get('waiting_for_autobuy', False) and position.get('auto_buy_count', 0) > 0:
                print(f"🎯 AUTO BUY EXECUTED! New position at ₹{price}")

# =============================================================================
# 🚀 MAIN EXECUTION - RUN TESTS
# =============================================================================

if __name__ == "__main__":
    print("🧪 ADVANCED ALGORITHM COMPREHENSIVE TEST SUITE")
    print("=" * 60)
    print("This test file demonstrates the 3-Phase Advanced Algorithm")
    print("with detailed explanations and real market scenarios.")
    print("=" * 60)
    
    # Run all comprehensive tests
    run_comprehensive_tests()
    
    # Run specific user scenario
    test_specific_price_scenario()
    
    print("\n🏁 ALL TESTS COMPLETED!")
    print("=" * 60)
    print("📝 SUMMARY:")
    print("• Phase 1 (Buy to Buy+20): Simple trailing with manual buy auto-buy")
    print("• Phase 2 (Buy+20 to Buy+30): Progressive minimum protection activated")
    print("• Phase 3 (Buy+30+): Full step-wise algorithm with maximum protection")
    print("• Auto-buy logic: Phase 1 at manual price, Phase 2&3 at sell price")
    print("• Progressive minimum provides downside protection in Phase 2&3")
    print("=" * 60)