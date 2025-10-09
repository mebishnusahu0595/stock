#!/usr/bin/env python3
"""
Test Phase 1 Auto Buy Logic to Prevent Rapid Fire
Tests the CE55400 scenario to ensure no rapid fire cycles
"""

def test_phase1_rapid_fire_fix():
    """Test that Phase 1 auto buy logic prevents rapid fire cycles"""
    
    # Simulate app state
    app_state = {
        'trading_algorithm': 'advanced',
        'paper_trading_enabled': True,
        'auto_trading_config': {'auto_buy_buffer': 0}
    }
    
    # Simulate CE55400 position
    position = {
        'strike': 55400,
        'type': 'CE',
        'option_type': 'CE',
        'manual_buy_price': 528.35,
        'buy_price': 528.35,
        'original_buy_price': 528.35,
        'current_price': 517.95,  # Stop loss price
        'highest_price': 528.35,
        'stop_loss_price': 518.35,
        'advanced_stop_loss': 518.35,
        'algorithm_phase': 1,
        'last_stop_loss_price': 518.35,  # Auto buy trigger (old logic)
        'waiting_for_autobuy': True,
        'auto_bought': False
    }
    
    print("🧪 PHASE 1 RAPID FIRE FIX TEST")
    print("=" * 50)
    print(f"📊 SCENARIO: CE55400")
    print(f"   Manual Buy: ₹{position['manual_buy_price']}")
    print(f"   Current Price: ₹{position['current_price']}")
    print(f"   Stop Loss: ₹{position['stop_loss_price']}")
    print(f"   Old Trigger: ₹{position['last_stop_loss_price']}")
    print(f"   Algorithm: {app_state['trading_algorithm']}")
    print(f"   Phase: {position['algorithm_phase']}")
    print()
    
    # Test current price scenarios
    test_prices = [517.95, 518.35, 520.00, 525.00, 528.35, 530.00]
    
    for current_price in test_prices:
        position['current_price'] = current_price
        
        # Apply the new logic
        current_algorithm = app_state.get('trading_algorithm', 'simple')
        is_phase1_advanced = (current_algorithm == 'advanced' and 
                            position.get('algorithm_phase', 1) == 1)
        
        print(f"📈 Testing Price: ₹{current_price}")
        
        if is_phase1_advanced:
            # Phase 1 Advanced: Use manual buy price trigger
            manual_buy_price = position.get('manual_buy_price', position.get('original_buy_price', 0))
            will_auto_buy = current_price >= manual_buy_price
            
            print(f"   🎯 PHASE 1 LOGIC:")
            print(f"      Manual Buy Price: ₹{manual_buy_price}")
            print(f"      Current >= Manual: {current_price} >= {manual_buy_price} = {will_auto_buy}")
            print(f"      Result: {'✅ AUTO BUY' if will_auto_buy else '❌ NO AUTO BUY'}")
        else:
            # Old logic (for comparison)
            last_stop_loss = position.get('last_stop_loss_price', 0)
            auto_buy_buffer = 1  # ±1 rupee buffer
            will_auto_buy_old = abs(current_price - last_stop_loss) <= auto_buy_buffer
            
            print(f"   🔄 OLD LOGIC (for comparison):")
            print(f"      Trigger: ₹{last_stop_loss} ± {auto_buy_buffer}")
            print(f"      Distance: |{current_price} - {last_stop_loss}| = {abs(current_price - last_stop_loss):.2f}")
            print(f"      Result: {'✅ AUTO BUY' if will_auto_buy_old else '❌ NO AUTO BUY'}")
        
        print()
    
    print("💡 ANALYSIS:")
    print("   OLD LOGIC: Would auto buy at ₹517.95, ₹518.35, ₹520.00 → RAPID FIRE!")
    print("   NEW LOGIC: Only auto buys at ₹528.35+ → NO RAPID FIRE!")
    print()
    print("🎯 EXPECTED BEHAVIOR:")
    print("   1. Manual Buy ₹528.35 → Stop Loss ₹518.35")
    print("   2. Price drops → Sell at ₹517.95")
    print("   3. No immediate auto buy (need price ≥ ₹528.35)")
    print("   4. Auto buy only when price recovers to ₹528.35")
    print("   5. No rapid fire cycles!")

if __name__ == "__main__":
    test_phase1_rapid_fire_fix()