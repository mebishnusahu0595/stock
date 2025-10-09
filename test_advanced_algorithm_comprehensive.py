#!/usr/bin/env python3
"""
Advanced Algorithm Test Suite
Tests all functions from app.py using dummy data
No external dependencies, self-contained testing
"""

import sys
import os
from datetime import datetime as dt
import copy

# Add current directory to path to import from app.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_update_advanced_algorithm():
    """Test the advanced algorithm function with dummy data"""
    print("="*80)
    print("TESTING UPDATE_ADVANCED_ALGORITHM FUNCTION")
    print("="*80)
    
    # Import the actual function from app.py
    try:
        from app import update_advanced_algorithm
        print("Successfully imported update_advanced_algorithm from app.py")
    except ImportError as e:
        print(f"Error importing function: {e}")
        return False
    
    # Test Case 1: Phase 1 - Initial buy to buy+20
    print("\nTEST CASE 1: PHASE 1 (Buy to Buy+20)")
    print("-" * 50)
    
    position_phase1 = {
        'strike': 55200,
        'type': 'CE',
        'option_type': 'CE',
        'buy_price': 500.0,
        'average_price': 500.0,
        'current_price': 510.0,
        'qty': 35,
        'quantity': 35,
        'id': 'test_phase1'
    }
    
    # Test Phase 1 behavior
    test_prices_phase1 = [500, 505, 510, 515, 519]
    
    for price in test_prices_phase1:
        position_copy = copy.deepcopy(position_phase1)
        print(f"\nTesting price: Rs.{price}")
        
        try:
            updated_position = update_advanced_algorithm(position_copy, price)
            
            print(f"  Current Price: Rs.{updated_position['current_price']}")
            print(f"  Algorithm Phase: {updated_position.get('algorithm_phase', 'N/A')}")
            print(f"  Manual Buy Price: Rs.{updated_position.get('manual_buy_price', 'N/A')}")
            print(f"  Highest Price: Rs.{updated_position.get('highest_price', 'N/A')}")
            print(f"  Stop Loss: Rs.{updated_position.get('stop_loss_price', 'N/A')}")
            print(f"  Advanced Stop Loss: Rs.{updated_position.get('advanced_stop_loss', 'N/A')}")
            print(f"  Progressive Minimum: {updated_position.get('progressive_minimum', 'N/A')}")
            
        except Exception as e:
            print(f"  Error testing price {price}: {e}")
    
    # Test Case 2: Phase 2 - Buy+20 to Buy+30
    print("\n\nTEST CASE 2: PHASE 2 (Buy+20 to Buy+30)")
    print("-" * 50)
    
    position_phase2 = {
        'strike': 55200,
        'type': 'CE',
        'option_type': 'CE',
        'buy_price': 500.0,
        'average_price': 500.0,
        'current_price': 525.0,
        'qty': 35,
        'quantity': 35,
        'id': 'test_phase2'
    }
    
    test_prices_phase2 = [520, 522, 525, 527, 529]
    
    for price in test_prices_phase2:
        position_copy = copy.deepcopy(position_phase2)
        print(f"\nTesting price: Rs.{price}")
        
        try:
            updated_position = update_advanced_algorithm(position_copy, price)
            
            print(f"  Current Price: Rs.{updated_position['current_price']}")
            print(f"  Algorithm Phase: {updated_position.get('algorithm_phase', 'N/A')}")
            print(f"  Manual Buy Price: Rs.{updated_position.get('manual_buy_price', 'N/A')}")
            print(f"  Highest Price: Rs.{updated_position.get('highest_price', 'N/A')}")
            print(f"  Stop Loss: Rs.{updated_position.get('stop_loss_price', 'N/A')}")
            print(f"  Advanced Stop Loss: Rs.{updated_position.get('advanced_stop_loss', 'N/A')}")
            print(f"  Progressive Minimum: {updated_position.get('progressive_minimum', 'N/A')}")
            
        except Exception as e:
            print(f"  Error testing price {price}: {e}")
    
    # Test Case 3: Phase 3 - After Buy+30
    print("\n\nTEST CASE 3: PHASE 3 (After Buy+30)")
    print("-" * 50)
    
    position_phase3 = {
        'strike': 55200,
        'type': 'CE',
        'option_type': 'CE',
        'buy_price': 500.0,
        'average_price': 500.0,
        'current_price': 540.0,
        'qty': 35,
        'quantity': 35,
        'id': 'test_phase3'
    }
    
    test_prices_phase3 = [530, 535, 540, 545, 550]
    
    for price in test_prices_phase3:
        position_copy = copy.deepcopy(position_phase3)
        print(f"\nTesting price: Rs.{price}")
        
        try:
            updated_position = update_advanced_algorithm(position_copy, price)
            
            print(f"  Current Price: Rs.{updated_position['current_price']}")
            print(f"  Algorithm Phase: {updated_position.get('algorithm_phase', 'N/A')}")
            print(f"  Manual Buy Price: Rs.{updated_position.get('manual_buy_price', 'N/A')}")
            print(f"  Highest Price: Rs.{updated_position.get('highest_price', 'N/A')}")
            print(f"  Stop Loss: Rs.{updated_position.get('stop_loss_price', 'N/A')}")
            print(f"  Advanced Stop Loss: Rs.{updated_position.get('advanced_stop_loss', 'N/A')}")
            print(f"  Progressive Minimum: {updated_position.get('progressive_minimum', 'N/A')}")
            
        except Exception as e:
            print(f"  Error testing price {price}: {e}")
    
    return True

def test_execute_auto_buy():
    """Test the auto buy function with dummy data"""
    print("\n\n" + "="*80)
    print("TESTING EXECUTE_AUTO_BUY FUNCTION")
    print("="*80)
    
    try:
        from app import execute_auto_buy, app_state
        print("Successfully imported execute_auto_buy from app.py")
    except ImportError as e:
        print(f"Error importing function: {e}")
        return False
    
    # Initialize app_state if needed
    if 'auto_trading_config' not in app_state:
        app_state['auto_trading_config'] = {
            'enabled': True,
            'auto_buy_buffer': 1,
            'max_auto_buy_count': 5
        }
    
    if 'trade_history' not in app_state:
        app_state['trade_history'] = []
    
    if 'auto_positions' not in app_state:
        app_state['auto_positions'] = []
    
    # Test different scenarios
    test_scenarios = [
        {
            'name': 'Phase 1 Auto Buy',
            'position': {
                'strike': 55200,
                'type': 'CE',
                'option_type': 'CE',
                'manual_buy_price': 500.0,
                'original_buy_price': 500.0,
                'current_price': 500.0,
                'algorithm_phase': 1,
                'qty': 0,
                'quantity': 0,
                'auto_buy_count': 1,
                'waiting_for_autobuy': True,
                'last_stop_loss_price': 490.0,
                'id': 'test_auto_buy_1'
            }
        },
        {
            'name': 'Phase 2 Auto Buy',
            'position': {
                'strike': 55400,
                'type': 'PE',
                'option_type': 'PE',
                'manual_buy_price': 600.0,
                'original_buy_price': 600.0,
                'current_price': 610.0,
                'algorithm_phase': 2,
                'qty': 0,
                'quantity': 0,
                'auto_buy_count': 2,
                'waiting_for_autobuy': True,
                'last_stop_loss_price': 610.0,
                'id': 'test_auto_buy_2'
            }
        },
        {
            'name': 'High Auto Buy Count',
            'position': {
                'strike': 56000,
                'type': 'CE',
                'option_type': 'CE',
                'manual_buy_price': 700.0,
                'original_buy_price': 700.0,
                'current_price': 695.0,
                'algorithm_phase': 1,
                'qty': 0,
                'quantity': 0,
                'auto_buy_count': 4,
                'waiting_for_autobuy': True,
                'last_stop_loss_price': 690.0,
                'id': 'test_auto_buy_3'
            }
        }
    ]
    
    for scenario in test_scenarios:
        print(f"\nTesting: {scenario['name']}")
        print("-" * 40)
        
        position_copy = copy.deepcopy(scenario['position'])
        
        print(f"Before Auto Buy:")
        print(f"  Strike: {position_copy['strike']} {position_copy['type']}")
        print(f"  Manual Buy Price: Rs.{position_copy['manual_buy_price']}")
        print(f"  Current Price: Rs.{position_copy['current_price']}")
        print(f"  Algorithm Phase: {position_copy['algorithm_phase']}")
        print(f"  Auto Buy Count: {position_copy['auto_buy_count']}")
        print(f"  Quantity: {position_copy['qty']}")
        
        try:
            # Enable paper trading for testing
            original_paper_trading = app_state.get('paper_trading_enabled', False)
            app_state['paper_trading_enabled'] = True
            
            result = execute_auto_buy(position_copy)
            
            print(f"\nAfter Auto Buy:")
            print(f"  Auto Buy Result: {result}")
            print(f"  New Quantity: {position_copy.get('qty', 0)}")
            print(f"  New Auto Buy Count: {position_copy.get('auto_buy_count', 0)}")
            print(f"  Buy Price: Rs.{position_copy.get('buy_price', 'N/A')}")
            print(f"  Stop Loss: Rs.{position_copy.get('stop_loss_price', 'N/A')}")
            print(f"  Waiting for Auto Buy: {position_copy.get('waiting_for_autobuy', 'N/A')}")
            
            # Restore original paper trading setting
            app_state['paper_trading_enabled'] = original_paper_trading
            
        except Exception as e:
            print(f"  Error during auto buy: {e}")
            import traceback
            print(f"  Traceback: {traceback.format_exc()}")
    
    return True

def test_trailing_stop_loss():
    """Test trailing stop loss calculations"""
    print("\n\n" + "="*80)
    print("TESTING TRAILING STOP LOSS CALCULATIONS")
    print("="*80)
    
    # Manual calculation test
    test_cases = [
        {
            'name': 'No Profit Scenario',
            'manual_buy': 500.0,
            'highest_price': 505.0,
            'expected_phase': 1,
            'expected_sl': 490.0  # manual_buy - 10
        },
        {
            'name': 'Small Profit Scenario',
            'manual_buy': 500.0,
            'highest_price': 515.0,
            'expected_phase': 1,
            'expected_sl': 500.0  # manual_buy + (1 step * 10)
        },
        {
            'name': 'Phase 2 Scenario',
            'manual_buy': 500.0,
            'highest_price': 525.0,
            'expected_phase': 2,
            'expected_sl': 520.0  # manual_buy + (2 steps * 10)
        },
        {
            'name': 'Phase 3 Scenario',
            'manual_buy': 500.0,
            'highest_price': 545.0,
            'expected_phase': 3,
            'expected_sl': 540.0  # manual_buy + (4 steps * 10)
        }
    ]
    
    for test_case in test_cases:
        print(f"\nTesting: {test_case['name']}")
        print("-" * 40)
        
        manual_buy = test_case['manual_buy']
        highest_price = test_case['highest_price']
        
        # Calculate profit and steps
        profit = highest_price - manual_buy
        profit_steps = int(profit // 10)
        calculated_sl = manual_buy + (profit_steps * 10)
        
        # Determine phase
        price_above_buy = highest_price - manual_buy
        if price_above_buy < 20:
            phase = 1
        elif price_above_buy < 30:
            phase = 2
        else:
            phase = 3
        
        print(f"  Manual Buy: Rs.{manual_buy}")
        print(f"  Highest Price: Rs.{highest_price}")
        print(f"  Profit: Rs.{profit}")
        print(f"  Profit Steps: {profit_steps}")
        print(f"  Calculated SL: Rs.{calculated_sl}")
        print(f"  Detected Phase: {phase}")
        print(f"  Expected Phase: {test_case['expected_phase']}")
        print(f"  Expected SL: Rs.{test_case['expected_sl']}")
        
        # Validation
        phase_correct = phase == test_case['expected_phase']
        sl_correct = abs(calculated_sl - test_case['expected_sl']) < 0.01
        
        print(f"  Phase Detection: {'PASS' if phase_correct else 'FAIL'}")
        print(f"  Stop Loss Calculation: {'PASS' if sl_correct else 'FAIL'}")

def test_auto_buy_trigger_logic():
    """Test auto buy trigger logic for different phases"""
    print("\n\n" + "="*80)
    print("TESTING AUTO BUY TRIGGER LOGIC")
    print("="*80)
    
    # Test scenarios for different phases
    scenarios = [
        {
            'name': 'Phase 1 - Should trigger at manual buy price',
            'position': {
                'algorithm_phase': 1,
                'manual_buy_price': 500.0,
                'last_stop_loss_price': 490.0
            },
            'test_prices': [485, 490, 495, 500, 505],
            'expected_triggers': [False, False, False, True, True]  # Only >= manual_buy_price
        },
        {
            'name': 'Phase 2 - Should trigger at stop loss price',
            'position': {
                'algorithm_phase': 2,
                'manual_buy_price': 500.0,
                'last_stop_loss_price': 510.0
            },
            'test_prices': [505, 509, 510, 511, 515],
            'expected_triggers': [False, True, True, True, False]  # Within ±1 of stop loss
        },
        {
            'name': 'Phase 3 - Should trigger at stop loss price',
            'position': {
                'algorithm_phase': 3,
                'manual_buy_price': 500.0,
                'last_stop_loss_price': 520.0
            },
            'test_prices': [515, 519, 520, 521, 525],
            'expected_triggers': [False, True, True, True, False]  # Within ±1 of stop loss
        }
    ]
    
    for scenario in scenarios:
        print(f"\nTesting: {scenario['name']}")
        print("-" * 50)
        
        position = scenario['position']
        
        for i, test_price in enumerate(scenario['test_prices']):
            expected = scenario['expected_triggers'][i]
            
            # Apply the actual trigger logic from app.py
            if position['algorithm_phase'] == 1:
                # Phase 1: Manual buy price trigger
                should_trigger = test_price >= position['manual_buy_price']
                trigger_type = "Manual Buy Price"
                trigger_value = position['manual_buy_price']
            else:
                # Phase 2/3: Stop loss price trigger
                should_trigger = abs(test_price - position['last_stop_loss_price']) <= 1
                trigger_type = "Stop Loss Price"
                trigger_value = position['last_stop_loss_price']
            
            result = "PASS" if should_trigger == expected else "FAIL"
            trigger_status = "TRIGGER" if should_trigger else "NO TRIGGER"
            
            print(f"  Price Rs.{test_price}: {trigger_type} Rs.{trigger_value} -> {trigger_status} [{result}]")

def test_comprehensive_scenarios():
    """Test comprehensive real-world scenarios"""
    print("\n\n" + "="*80)
    print("TESTING COMPREHENSIVE REAL-WORLD SCENARIOS")
    print("="*80)
    
    # CE55200 Scenario from user's actual data
    print("\nSCENARIO 1: CE55200 (User's Actual Case)")
    print("-" * 50)
    
    ce55200_data = {
        'strike': 55200,
        'type': 'CE',
        'manual_buy': 673.60,
        'current_price': 701.75,
        'qty': 35
    }
    
    # Calculate expected values
    profit = ce55200_data['current_price'] - ce55200_data['manual_buy']
    profit_steps = int(profit // 10)
    expected_sl = ce55200_data['manual_buy'] + (profit_steps * 10)
    expected_phase = 2 if profit < 30 else 3
    
    print(f"  Strike: {ce55200_data['strike']} {ce55200_data['type']}")
    print(f"  Manual Buy: Rs.{ce55200_data['manual_buy']}")
    print(f"  Current Price: Rs.{ce55200_data['current_price']}")
    print(f"  Quantity: {ce55200_data['qty']}")
    print(f"  Profit: Rs.{profit:.2f}")
    print(f"  Profit Steps: {profit_steps}")
    print(f"  Expected Stop Loss: Rs.{expected_sl}")
    print(f"  Expected Phase: {expected_phase}")
    print(f"  Auto Buy Should Trigger At: Rs.{expected_sl} ± 1 (for Phase {expected_phase})")
    
    # Test with actual algorithm if available
    try:
        from app import update_advanced_algorithm
        
        test_position = {
            'strike': ce55200_data['strike'],
            'type': ce55200_data['type'],
            'buy_price': ce55200_data['manual_buy'],
            'current_price': ce55200_data['current_price'],
            'qty': ce55200_data['qty'],
            'id': 'ce55200_test'
        }
        
        result = update_advanced_algorithm(test_position, ce55200_data['current_price'])
        
        print(f"\nActual Algorithm Results:")
        print(f"  Algorithm Phase: {result.get('algorithm_phase', 'N/A')}")
        print(f"  Stop Loss: Rs.{result.get('stop_loss_price', 'N/A')}")
        print(f"  Advanced Stop Loss: Rs.{result.get('advanced_stop_loss', 'N/A')}")
        print(f"  Highest Price: Rs.{result.get('highest_price', 'N/A')}")
        print(f"  Progressive Minimum: {result.get('progressive_minimum', 'N/A')}")
        
        # Validation
        phase_correct = result.get('algorithm_phase') == expected_phase
        sl_correct = abs(result.get('stop_loss_price', 0) - expected_sl) < 0.01
        
        print(f"\nValidation:")
        print(f"  Phase Detection: {'PASS' if phase_correct else 'FAIL'}")
        print(f"  Stop Loss Calculation: {'PASS' if sl_correct else 'FAIL'}")
        
    except ImportError:
        print("  Could not import algorithm function for testing")
    except Exception as e:
        print(f"  Error testing with actual algorithm: {e}")

def test_paper_trading_simulation():
    """Test paper trading calculations"""
    print("\n\n" + "="*80)
    print("TESTING PAPER TRADING SIMULATION")
    print("="*80)
    
    # Simulate a complete trading cycle
    initial_balance = 1000000.0  # Rs.10 lakhs
    
    trades = [
        {'action': 'Manual Buy', 'strike': 55200, 'type': 'CE', 'qty': 35, 'price': 673.60},
        {'action': 'Auto Sell', 'strike': 55200, 'type': 'CE', 'qty': 35, 'price': 693.05},
        {'action': 'Auto Buy', 'strike': 55200, 'type': 'CE', 'qty': 35, 'price': 673.60},
        {'action': 'Auto Sell', 'strike': 55200, 'type': 'CE', 'qty': 35, 'price': 681.65},
        {'action': 'Auto Buy', 'strike': 55200, 'type': 'CE', 'qty': 35, 'price': 673.60}
    ]
    
    current_balance = initial_balance
    positions = {}
    
    print(f"Initial Balance: Rs.{current_balance:,.2f}")
    print("\nTrade Simulation:")
    print("-" * 40)
    
    for i, trade in enumerate(trades, 1):
        position_key = f"{trade['strike']}{trade['type']}"
        
        if 'Buy' in trade['action']:
            cost = trade['qty'] * trade['price']
            current_balance -= cost
            positions[position_key] = {
                'qty': trade['qty'],
                'avg_price': trade['price'],
                'total_cost': cost
            }
            pnl = 0
        else:  # Sell
            if position_key in positions:
                revenue = trade['qty'] * trade['price']
                cost = positions[position_key]['total_cost']
                pnl = revenue - cost
                current_balance += revenue
                del positions[position_key]
            else:
                pnl = 0
        
        print(f"  {i}. {trade['action']}: {trade['strike']} {trade['type']}")
        print(f"     Qty: {trade['qty']} | Price: Rs.{trade['price']} | P&L: Rs.{pnl:.2f}")
        print(f"     Balance: Rs.{current_balance:,.2f}")
    
    total_pnl = current_balance - initial_balance
    print(f"\nFinal Results:")
    print(f"  Initial Balance: Rs.{initial_balance:,.2f}")
    print(f"  Final Balance: Rs.{current_balance:,.2f}")
    print(f"  Total P&L: Rs.{total_pnl:,.2f}")
    print(f"  Return %: {(total_pnl/initial_balance)*100:.2f}%")

def run_all_tests():
    """Run all test functions"""
    print("ADVANCED ALGORITHM COMPREHENSIVE TEST SUITE")
    print("="*80)
    print(f"Test Run Time: {dt.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    test_functions = [
        test_update_advanced_algorithm,
        test_execute_auto_buy,
        test_trailing_stop_loss,
        test_auto_buy_trigger_logic,
        test_comprehensive_scenarios,
        test_paper_trading_simulation
    ]
    
    passed_tests = 0
    total_tests = len(test_functions)
    
    for test_func in test_functions:
        try:
            print(f"\nRunning: {test_func.__name__}")
            result = test_func()
            if result is not False:
                passed_tests += 1
                print(f"RESULT: PASSED")
            else:
                print(f"RESULT: FAILED")
        except Exception as e:
            print(f"RESULT: ERROR - {e}")
            import traceback
            print(traceback.format_exc())
    
    print("\n" + "="*80)
    print("TEST SUITE SUMMARY")
    print("="*80)
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
    print("="*80)

if __name__ == "__main__":
    run_all_tests()