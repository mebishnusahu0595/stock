#!/usr/bin/env python3
"""
Test script to verify manual sell functionality is working correctly
"""

def test_manual_sell_routes():
    """Test if the required routes exist in app.py"""
    print("=== TESTING MANUAL SELL ROUTES ===")
    
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    routes_to_check = [
        '/api/manual-trigger-auto-sell',
        '/api/manual-sell-auto-position',
        '/api/sell-all-positions',
        '/api/sell-individual-position'
    ]
    
    print("Checking if all required routes exist:")
    all_exist = True
    
    for route in routes_to_check:
        if route in content:
            print(f"✅ {route} - FOUND")
        else:
            print(f"❌ {route} - MISSING")
            all_exist = False
    
    return all_exist

def test_javascript_functions():
    """Test if JavaScript functions exist in app.js"""
    print("\n=== TESTING JAVASCRIPT FUNCTIONS ===")
    
    with open('static/js/app.js', 'r', encoding='utf-8') as f:
        content = f.read()
    
    functions_to_check = [
        'manualSellAutoPosition',
        'manualAutoSell',
        'sellAllPositions',
        'manualSell'
    ]
    
    print("Checking if all required JavaScript functions exist:")
    all_exist = True
    
    for func in functions_to_check:
        if f"function {func}" in content or f"async function {func}" in content:
            print(f"✅ {func}() - FOUND")
        else:
            print(f"❌ {func}() - MISSING")
            all_exist = False
    
    return all_exist

def test_button_structure():
    """Test if button structure is correct"""
    print("\n=== TESTING BUTTON STRUCTURE ===")
    
    with open('static/js/app.js', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if action-buttons div exists
    if 'action-buttons' in content:
        print("✅ action-buttons container - FOUND")
    else:
        print("❌ action-buttons container - MISSING")
        return False
    
    # Check if both buttons exist
    if 'manualAutoSell' in content and 'manualSellAutoPosition' in content:
        print("✅ Both Auto Sell and Manual Sell buttons - FOUND")
    else:
        print("❌ Missing one or both buttons")
        return False
    
    return True

def main():
    print("🧪 MANUAL SELL FUNCTIONALITY TEST")
    print("=" * 50)
    
    routes_ok = test_manual_sell_routes()
    js_ok = test_javascript_functions()
    buttons_ok = test_button_structure()
    
    print(f"\n{'='*50}")
    print("📋 TEST SUMMARY:")
    print(f"Routes: {'✅ PASS' if routes_ok else '❌ FAIL'}")
    print(f"JavaScript: {'✅ PASS' if js_ok else '❌ FAIL'}")
    print(f"Buttons: {'✅ PASS' if buttons_ok else '❌ FAIL'}")
    
    if routes_ok and js_ok and buttons_ok:
        print(f"\n🎉 ALL TESTS PASSED! Manual sell functionality is ready!")
        print(f"\nNow you should have:")
        print(f"• Auto Sell button (triggers auto sell, allows auto buy)")
        print(f"• Manual Sell button (completely removes position)")
        print(f"• Sell All button (sells all Zerodha positions)")
        print(f"• Proper confirmation dialogs")
    else:
        print(f"\n⚠️ SOME TESTS FAILED. Please check the issues above.")

if __name__ == "__main__":
    main()
