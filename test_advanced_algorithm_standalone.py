
import copy
from datetime import datetime as dt

# Embedded algorithm logic from app.py
def update_advanced_algorithm_standalone(position, new_price):
    """
    Standalone version of advanced algorithm from app.py
    3-Phase Logic Implementation
    """
    print(f"[DEBUG] ADVANCED ALGORITHM called for {position.get('strike', '?')} {position.get('type', '?')} | Price: {new_price}")
    
    old_price = float(position['current_price'])
    position['current_price'] = new_price
    position['last_update'] = dt.now()
    
    # Initialize required fields
    if 'original_buy_price' not in position:
        position['original_buy_price'] = position.get('buy_price', position.get('average_price', new_price))
    if 'manual_buy_price' not in position:
        position['manual_buy_price'] = position.get('buy_price', position.get('average_price', new_price))
    if 'highest_price' not in position:
        position['highest_price'] = position['original_buy_price']
    if 'advanced_stop_loss' not in position:
        position['advanced_stop_loss'] = position['original_buy_price'] - 10
    if 'algorithm_phase' not in position:
        position['algorithm_phase'] = 1
    if 'progressive_minimum' not in position:
        position['progressive_minimum'] = None
    if 'highest_stop_loss' not in position:
        position['highest_stop_loss'] = position['original_buy_price'] - 10
    
    original_buy_price = position['original_buy_price']
    manual_buy_price = position['manual_buy_price']
    current_phase = position['algorithm_phase']
    
    # Determine current phase based on price levels
    price_above_buy = new_price - manual_buy_price
    
    if price_above_buy < 20:
        position['algorithm_phase'] = 1
    elif price_above_buy < 30:
        position['algorithm_phase'] = 2
    else:
        position['algorithm_phase'] = 3
    
    print(f"PHASE {position['algorithm_phase']}: Manual Buy Rs.{manual_buy_price} | Current Rs.{new_price} | Above Buy: +Rs.{price_above_buy:.2f}")
    
    # PHASE 1: Initial Stop Loss Logic (Buy to Buy+20)
    if position['algorithm_phase'] == 1:
        if new_price > position['highest_price']:
            position['highest_price'] = new_price
        
        profit = position['highest_price'] - manual_buy_price
        trailing_step = 10
        
        if profit >= 10:
            profit_steps = int(profit // trailing_step)
            trailing_stop_loss = manual_buy_price + (profit_steps * trailing_step)
            minimum_sl = manual_buy_price - 10
            position['advanced_stop_loss'] = max(trailing_stop_loss, minimum_sl)
            
            print(f"PHASE 1 TRAILING: Buy Rs.{manual_buy_price} | High Rs.{position['highest_price']} | Profit Rs.{profit:.2f} | Steps {profit_steps}")
            print(f"   SL = Rs.{manual_buy_price} + ({profit_steps}×10) = Rs.{trailing_stop_loss} | Final SL Rs.{position['advanced_stop_loss']}")
        else:
            position['advanced_stop_loss'] = manual_buy_price - 10
            print(f"PHASE 1: Simple SL = Rs.{manual_buy_price} - 10 = Rs.{position['advanced_stop_loss']}")
        
        position['progressive_minimum'] = None
    
    # PHASE 2: Progressive Minimum Activation (Buy+20 to Buy+30)
    elif position['algorithm_phase'] == 2:
        if new_price > position['highest_price']:
            position['highest_price'] = new_price
        
        if position['progressive_minimum'] is None:
            position['progressive_minimum'] = manual_buy_price
            print(f"PROGRESSIVE MINIMUM ACTIVATED: Rs.{position['progressive_minimum']}")
        
        # Fixed Phase 2 trailing: step-wise from buy price
        profit = position['highest_price'] - manual_buy_price
        trailing_step = 10
        
        if profit >= 10:
            profit_steps = int(profit // trailing_step)
            step_stop_loss = manual_buy_price + (profit_steps * trailing_step)
            position['advanced_stop_loss'] = max(step_stop_loss, position['progressive_minimum'])
            
            print(f"PHASE 2: Buy Rs.{manual_buy_price} | High Rs.{position['highest_price']} | Profit Rs.{profit:.2f} | Steps {profit_steps}")
            print(f"   SL = Rs.{manual_buy_price} + ({profit_steps}×10) = Rs.{step_stop_loss} | Progressive Min Rs.{position['progressive_minimum']} → Final SL Rs.{position['advanced_stop_loss']}")
        else:
            position['advanced_stop_loss'] = position['progressive_minimum']
            print(f"PHASE 2: No profit yet, using Progressive Min Rs.{position['progressive_minimum']}")
    
    # PHASE 3: Step-wise Algorithm (After Buy+30)
    elif position['algorithm_phase'] == 3:
        if new_price > position['highest_price']:
            position['highest_price'] = new_price
        
        profit = position['highest_price'] - manual_buy_price
        trailing_step = 10
        
        if profit >= 30:
            profit_steps = int(profit // trailing_step)
            step_stop_loss = manual_buy_price + (profit_steps * trailing_step)
            
            if position['progressive_minimum'] is None:
                position['progressive_minimum'] = manual_buy_price
            
            position['advanced_stop_loss'] = max(step_stop_loss, position['progressive_minimum'])
            
            print(f"PHASE 3: Profit Rs.{profit:.2f} → Steps {profit_steps} → SL = Rs.{manual_buy_price} + ({profit_steps}×10) = Rs.{step_stop_loss}")
            print(f"   Progressive Min Rs.{position['progressive_minimum']} → Final SL Rs.{position['advanced_stop_loss']}")
    
    # Update traditional stop_loss_price for display
    position['stop_loss_price'] = position['advanced_stop_loss']
    
    return position

def execute_auto_buy_standalone(position):
    """
    Standalone version of auto buy logic from app.py
    """
    print(f"AUTO BUY EXECUTION for {position['strike']} {position['type']}")
    
    # Get current price for auto buy
    buy_price = position.get('current_price', position.get('last_stop_loss_price', 0))
    
    # Set quantity for paper trading
    position['qty'] = 35
    position['quantity'] = 35
    
    # Update buy price
    position['buy_price'] = buy_price
    position['average_price'] = buy_price
    
    # Calculate new stop loss (buy_price - 10)
    new_stop_loss_price = buy_price - 10
    position['stop_loss_price'] = new_stop_loss_price
    position['advanced_stop_loss'] = new_stop_loss_price
    
    # Update auto buy count
    position['auto_buy_count'] = position.get('auto_buy_count', 0) + 1
    
    # Clear waiting flags
    position['waiting_for_autobuy'] = False
    position['sold'] = False
    position['manual_sold'] = False
    
    print(f"AUTO BUY EXECUTED: {position['strike']} {position['type']} @ Rs.{buy_price} | Stop Loss: Rs.{position['stop_loss_price']} | Count: {position['auto_buy_count']}")
    
    return True

def test_complete_algorithm_cycle():
    """Test complete algorithm cycle with realistic data"""
    print("="*80)
    print("COMPLETE ALGORITHM CYCLE TEST")
    print("="*80)
    
    # Test Case: CE55200 complete cycle
    position = {
        'strike': 55200,
        'type': 'CE',
        'option_type': 'CE',
        'buy_price': 673.60,
        'average_price': 673.60,
        'current_price': 673.60,
        'qty': 35,
        'quantity': 35,
        'id': 'ce55200_test',
        'auto_buy_count': 0,
        'waiting_for_autobuy': False
    }
    
    # Simulate price movements
    price_sequence = [
        673.60,  # Initial buy
        675.00,  # Small move up
        680.00,  # Phase 1 profit
        685.00,  # More profit
        690.00,  # Approaching Phase 2
        695.00,  # Phase 2 territory  
        701.75,  # User's actual scenario
        705.00,  # Higher profit
        698.00,  # Pullback
        693.00,  # Near stop loss
        690.00,  # Below stop loss - should sell
        695.00,  # Recovery - should auto buy
    ]
    
    print(f"Starting Position: {position['strike']} {position['type']} @ Rs.{position['buy_price']}")
    print("-" * 60)
    
    for i, price in enumerate(price_sequence, 1):
        print(f"\nStep {i}: Price Rs.{price}")
        print("-" * 30)
        
        # Update algorithm
        updated_position = update_advanced_algorithm_standalone(position.copy(), price)
        
        print(f"Results:")
        print(f"  Phase: {updated_position.get('algorithm_phase')}")
        print(f"  Highest: Rs.{updated_position.get('highest_price')}")
        print(f"  Stop Loss: Rs.{updated_position.get('stop_loss_price')}")
        print(f"  Progressive Min: {updated_position.get('progressive_minimum')}")
        
        # Check for stop loss trigger
        stop_loss = updated_position.get('stop_loss_price', 0)
        if price < stop_loss and stop_loss > 0:
            print(f"  STOP LOSS TRIGGERED: Price Rs.{price} < SL Rs.{stop_loss}")
            
            # Simulate sell
            position['qty'] = 0
            position['waiting_for_autobuy'] = True
            position['last_stop_loss_price'] = stop_loss
            
            print(f"  POSITION SOLD at Rs.{price}")
            
        # Check for auto buy trigger
        elif updated_position.get('waiting_for_autobuy', False):
            should_auto_buy = False
            
            # Apply auto buy logic based on phase
            if updated_position.get('algorithm_phase') == 1:
                # Phase 1: Manual buy price trigger
                manual_buy_price = updated_position.get('manual_buy_price', updated_position.get('buy_price', 0))
                should_auto_buy = price >= manual_buy_price
                trigger_type = f"Manual Buy Rs.{manual_buy_price}"
            else:
                # Phase 2/3: Stop loss price trigger
                last_stop_loss = updated_position.get('last_stop_loss_price', 0)
                should_auto_buy = abs(price - last_stop_loss) <= 1
                trigger_type = f"Stop Loss Rs.{last_stop_loss} ± 1"
            
            if should_auto_buy:
                print(f"  AUTO BUY TRIGGERED: {trigger_type}")
                execute_auto_buy_standalone(updated_position)
                position.update(updated_position)
            else:
                print(f"  Waiting for auto buy: {trigger_type}")
        
        # Update position for next iteration
        if not updated_position.get('waiting_for_autobuy', False):
            position.update(updated_position)

def test_phase_transitions():
    """Test phase transitions with detailed calculations"""
    print("\n\n" + "="*80)
    print("PHASE TRANSITION TESTING")
    print("="*80)
    
    position = {
        'strike': 56000,
        'type': 'PE',
        'buy_price': 500.0,
        'current_price': 500.0,
        'qty': 50,
        'id': 'phase_test'
    }
    
    # Test prices that span all phases
    test_prices = [
        500.0,   # Phase 1 start
        505.0,   # Phase 1 small profit
        510.0,   # Phase 1 trailing
        515.0,   # Phase 1 more trailing
        519.0,   # Phase 1 near Phase 2
        520.0,   # Phase 2 start (500 + 20)
        522.0,   # Phase 2 middle
        525.0,   # Phase 2 middle
        529.0,   # Phase 2 near Phase 3
        530.0,   # Phase 3 start (500 + 30)
        535.0,   # Phase 3 middle
        540.0,   # Phase 3 higher
        545.0    # Phase 3 much higher
    ]
    
    print(f"Base Position: {position['strike']} {position['type']} @ Rs.{position['buy_price']}")
    print("-" * 60)
    
    for price in test_prices:
        test_position = copy.deepcopy(position)
        result = update_advanced_algorithm_standalone(test_position, price)
        
        # Calculate expected values
        profit = price - 500.0
        expected_phase = 1 if profit < 20 else (2 if profit < 30 else 3)
        profit_steps = int(profit // 10) if profit >= 10 else 0
        expected_sl = 500.0 + (profit_steps * 10) if profit >= 10 else 490.0
        
        print(f"\nPrice Rs.{price}:")
        print(f"  Profit: Rs.{profit:.1f}")
        print(f"  Expected Phase: {expected_phase} | Actual Phase: {result.get('algorithm_phase')}")
        print(f"  Expected SL: Rs.{expected_sl} | Actual SL: Rs.{result.get('stop_loss_price')}")
        print(f"  Progressive Min: {result.get('progressive_minimum')}")
        
        # Validation
        phase_ok = result.get('algorithm_phase') == expected_phase
        sl_ok = abs(result.get('stop_loss_price', 0) - expected_sl) < 0.01
        
        status = "PASS" if (phase_ok and sl_ok) else "FAIL"
        print(f"  Status: {status}")

def test_auto_buy_scenarios():
    """Test auto buy scenarios for all phases"""
    print("\n\n" + "="*80)
    print("AUTO BUY SCENARIO TESTING")
    print("="*80)
    
    scenarios = [
        {
            'name': 'Phase 1 Auto Buy Test',
            'position': {
                'strike': 55200,
                'type': 'CE',
                'manual_buy_price': 600.0,
                'algorithm_phase': 1,
                'last_stop_loss_price': 590.0,
                'waiting_for_autobuy': True
            },
            'test_prices': [585, 590, 595, 599, 600, 601, 605],
            'description': 'Phase 1 should auto buy when price >= manual_buy_price (600)'
        },
        {
            'name': 'Phase 2 Auto Buy Test',
            'position': {
                'strike': 55400,
                'type': 'PE',
                'manual_buy_price': 700.0,
                'algorithm_phase': 2,
                'last_stop_loss_price': 710.0,
                'waiting_for_autobuy': True
            },
            'test_prices': [705, 708, 709, 710, 711, 712, 715],
            'description': 'Phase 2 should auto buy when price within ±1 of last_stop_loss_price (710)'
        },
        {
            'name': 'Phase 3 Auto Buy Test',
            'position': {
                'strike': 56000,
                'type': 'CE',
                'manual_buy_price': 800.0,
                'algorithm_phase': 3,
                'last_stop_loss_price': 830.0,
                'waiting_for_autobuy': True
            },
            'test_prices': [825, 828, 829, 830, 831, 832, 835],
            'description': 'Phase 3 should auto buy when price within ±1 of last_stop_loss_price (830)'
        }
    ]
    
    for scenario in scenarios:
        print(f"\n{scenario['name']}")
        print("-" * 50)
        print(scenario['description'])
        print()
        
        position = scenario['position']
        
        for price in scenario['test_prices']:
            # Apply auto buy logic
            if position['algorithm_phase'] == 1:
                should_trigger = price >= position['manual_buy_price']
                trigger_logic = f"Price {price} >= Manual Buy {position['manual_buy_price']}"
            else:
                should_trigger = abs(price - position['last_stop_loss_price']) <= 1
                trigger_logic = f"|{price} - {position['last_stop_loss_price']}| <= 1"
            
            result = "AUTO BUY" if should_trigger else "NO AUTO BUY"
            print(f"  Rs.{price}: {trigger_logic} = {should_trigger} → {result}")

def test_real_world_calculations():
    """Test with real user data calculations"""
    print("\n\n" + "="*80)
    print("REAL WORLD CALCULATION TESTING")
    print("="*80)
    
    # User's actual CE55200 case
    print("\nCE55200 User Case Validation")
    print("-" * 40)
    
    real_data = {
        'manual_buy': 673.60,
        'current_price': 701.75,
        'displayed_sl': 692.00,  # Wrong value user reported
        'qty': 35
    }
    
    # Manual calculation
    profit = real_data['current_price'] - real_data['manual_buy']
    profit_steps = int(profit // 10)
    correct_sl = real_data['manual_buy'] + (profit_steps * 10)
    
    print(f"Manual Buy: Rs.{real_data['manual_buy']}")
    print(f"Current Price: Rs.{real_data['current_price']}")
    print(f"Profit: Rs.{profit:.2f}")
    print(f"Profit Steps: {profit_steps}")
    print(f"Correct Stop Loss: Rs.{correct_sl}")
    print(f"User's Displayed SL: Rs.{real_data['displayed_sl']} (WRONG)")
    print(f"Difference: Rs.{correct_sl - real_data['displayed_sl']:.2f}")
    
    # Test with algorithm
    test_position = {
        'strike': 55200,
        'type': 'CE',
        'buy_price': real_data['manual_buy'],
        'current_price': real_data['current_price'],
        'qty': real_data['qty'],
        'id': 'real_test'
    }
    
    result = update_advanced_algorithm_standalone(test_position, real_data['current_price'])
    
    print(f"\nAlgorithm Results:")
    print(f"Phase: {result.get('algorithm_phase')}")
    print(f"Stop Loss: Rs.{result.get('stop_loss_price')}")
    print(f"Highest Price: Rs.{result.get('highest_price')}")
    print(f"Progressive Min: {result.get('progressive_minimum')}")
    
    # Validation
    algorithm_correct = abs(result.get('stop_loss_price', 0) - correct_sl) < 0.01
    print(f"\nValidation: {'PASS' if algorithm_correct else 'FAIL'}")
    
    # Auto buy trigger test
    print(f"\nAuto Buy Trigger Analysis:")
    phase = result.get('algorithm_phase', 1)
    if phase == 1:
        print(f"Phase 1: Auto buy at manual buy price Rs.{real_data['manual_buy']}")
    else:
        print(f"Phase {phase}: Auto buy at stop loss price Rs.{correct_sl} ± 1")
        print(f"Trigger range: Rs.{correct_sl-1} to Rs.{correct_sl+1}")

def run_comprehensive_tests():
    """Run all comprehensive tests"""
    print("ADVANCED ALGORITHM STANDALONE TEST SUITE")
    print("="*80)
    print(f"Test Execution Time: {dt.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("No external dependencies - Pure Python implementation")
    print("="*80)
    
    test_functions = [
        test_complete_algorithm_cycle,
        test_phase_transitions,
        test_auto_buy_scenarios,
        test_real_world_calculations
    ]
    
    for i, test_func in enumerate(test_functions, 1):
        try:
            print(f"\n[TEST {i}/{len(test_functions)}] Running: {test_func.__name__}")
            test_func()
            print(f"[TEST {i}] STATUS: COMPLETED")
        except Exception as e:
            print(f"[TEST {i}] STATUS: ERROR - {e}")
            import traceback
            print(traceback.format_exc())
    
    print("\n" + "="*80)
    print("COMPREHENSIVE TEST SUITE COMPLETED")
    print("All algorithm functions tested with dummy data")
    print("="*80)

if __name__ == "__main__":
    run_comprehensive_tests()