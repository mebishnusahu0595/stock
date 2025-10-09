#!/usr/bin/env python3
"""
Simple test runner to execute the multiple sell fix test
"""

try:
    print("Starting test runner...")
    
    # Import the test module
    import test_multiple_sell_fix
    
    print("Test module imported successfully")
    
    # Run the main function if it exists
    if hasattr(test_multiple_sell_fix, 'main'):
        print("Running main test function...")
        test_multiple_sell_fix.main()
    else:
        print("No main function found, checking for test functions...")
        # Try to run test functions directly
        if hasattr(test_multiple_sell_fix, 'test_multiple_sell_prevention'):
            test_multiple_sell_fix.test_multiple_sell_prevention()
        if hasattr(test_multiple_sell_fix, 'test_manual_sell_blocks_auto_buy'):
            test_multiple_sell_fix.test_manual_sell_blocks_auto_buy()
        if hasattr(test_multiple_sell_fix, 'test_position_removal_after_manual_sell'):
            test_multiple_sell_fix.test_position_removal_after_manual_sell()
        if hasattr(test_multiple_sell_fix, 'test_race_condition_prevention'):
            test_multiple_sell_fix.test_race_condition_prevention()
            
except Exception as e:
    print(f"Error running test: {e}")
    import traceback
    traceback.print_exc()
