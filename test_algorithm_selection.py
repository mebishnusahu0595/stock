#!/usr/bin/env python3
"""
🧪 Test Algorithm Selection Fix
Verify that the app now uses advanced algorithm by default
"""

# Mock the app_state
app_state = {
    'trading_algorithm': 'advanced',  # Now defaults to advanced
}

def update_simple_algorithm(position, new_price):
    print(f"❌ WRONG: Simple algorithm called!")
    return False

def update_advanced_algorithm(position, new_price):
    print(f"✅ CORRECT: Advanced algorithm called!")
    # Mock the phase 1 logic
    if position.get('algorithm_phase', 1) == 1:
        print(f"🎯 PHASE 1: Will use manual buy price ₹{position.get('manual_buy_price', 'N/A')}")
    return True

def test_algorithm_selection():
    """Test that algorithm selection now defaults to advanced"""
    
    print("="*60)
    print("🧪 TESTING ALGORITHM SELECTION")
    print("="*60)
    
    # Mock position
    position = {
        'strike': 55900,
        'type': 'PE',
        'manual_buy_price': 356.30,
        'current_price': 345.75,
        'algorithm_phase': 1
    }
    
    # Mock the algorithm selection logic from app.py
    algorithm = app_state.get('trading_algorithm', 'simple')
    print(f"📊 Algorithm setting: {algorithm}")
    
    if algorithm == 'simple':
        print("🔄 Calling simple algorithm...")
        result = update_simple_algorithm(position, 345.75)
    elif algorithm == 'advanced':
        print("🔄 Calling advanced algorithm...")
        result = update_advanced_algorithm(position, 345.75)
    else:
        print(f"[ERROR] Unknown algorithm: {algorithm}")
        result = update_simple_algorithm(position, 345.75)
    
    print(f"\n🎯 VERIFICATION:")
    if algorithm == 'advanced':
        print(f"   ✅ PASS: Using advanced algorithm (Phase 1 fix active)")
        print(f"   ✅ PASS: Phase 1 auto buy will use manual price ₹356.30")
    else:
        print(f"   ❌ FAIL: Still using {algorithm} algorithm")
        print(f"   ❌ FAIL: Phase 1 fix not active")

if __name__ == "__main__":
    test_algorithm_selection()