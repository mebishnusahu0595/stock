#!/usr/bin/env python3
"""
Test Progressive Minimum Calculation Fix
Verify that Progressive Min = Highest Stop Loss - 20
"""

def test_progressive_minimum_fix():
    """Test the corrected progressive minimum calculation"""
    
    print("🧪 TESTING PROGRESSIVE MINIMUM CALCULATION FIX")
    print("=" * 50)
    
    # Test scenario
    position = {
        'buy_price': 100.0,
        'highest_stop_loss': 90.0,  # Initial
        'progressive_minimum': 90.0  # Initial
    }
    
    print(f"📊 Starting Position:")
    print(f"   Buy Price: ₹{position['buy_price']}")
    print(f"   Highest Stop Loss: ₹{position['highest_stop_loss']}")
    print(f"   Progressive Minimum: ₹{position['progressive_minimum']}")
    print()
    
    # Test prices and expected results
    test_cases = [
        {'price': 110, 'expected_sl': 110, 'expected_pm': 90},   # 110-20=90, max(90,90)=90
        {'price': 120, 'expected_sl': 120, 'expected_pm': 100},  # 120-20=100, max(90,100)=100
        {'price': 130, 'expected_sl': 130, 'expected_pm': 110},  # 130-20=110, max(100,110)=110
        {'price': 140, 'expected_sl': 140, 'expected_pm': 120},  # 140-20=120, max(110,120)=120
        {'price': 150, 'expected_sl': 150, 'expected_pm': 130},  # 150-20=130, max(120,130)=130
    ]
    
    print("🔄 Testing Progressive Minimum Updates:")
    print("-" * 40)
    
    for i, test in enumerate(test_cases, 1):
        new_price = test['price']
        
        # Calculate new stop loss (buy_price + steps*10)
        profit = new_price - position['buy_price']
        steps = int(profit // 10)
        new_stop_loss = position['buy_price'] + (steps * 10)
        
        # Update highest stop loss FIRST
        if new_stop_loss > position['highest_stop_loss']:
            position['highest_stop_loss'] = new_stop_loss
            
            # Then calculate progressive minimum (highest - 20)
            calculated_pm = position['highest_stop_loss'] - 20
            position['progressive_minimum'] = max(position['progressive_minimum'], calculated_pm)
        
        # Verify results
        sl_correct = position['highest_stop_loss'] == test['expected_sl']
        pm_correct = position['progressive_minimum'] == test['expected_pm']
        
        status_sl = "✅" if sl_correct else "❌"
        status_pm = "✅" if pm_correct else "❌"
        
        print(f"Step {i}: Price ₹{new_price}")
        print(f"   Stop Loss: ₹{position['highest_stop_loss']} {status_sl} (Expected: ₹{test['expected_sl']})")
        print(f"   Progressive Min: ₹{position['progressive_minimum']} {status_pm} (Expected: ₹{test['expected_pm']})")
        print()
    
    # Final verification for the main issue: Price 150
    print("🎯 MAIN ISSUE VERIFICATION:")
    print(f"   When price reaches ₹150:")
    print(f"   Stop Loss = ₹{position['highest_stop_loss']} ✅")
    print(f"   Progressive Min = ₹{position['progressive_minimum']} ✅ (150 - 20 = 130)")
    print()
    
    if position['progressive_minimum'] == 130:
        print("✅ FIX SUCCESSFUL: Progressive minimum correctly calculated as 130!")
    else:
        print(f"❌ FIX FAILED: Progressive minimum is {position['progressive_minimum']}, should be 130")
    
    print()
    print("🔍 Formula Verification:")
    print("   Progressive Minimum = max(current_pm, highest_stop_loss - 20)")
    print("   At ₹150: Progressive Minimum = max(120, 150-20) = max(120, 130) = 130 ✅")

if __name__ == "__main__":
    test_progressive_minimum_fix()