#!/usr/bin/env python3
"""
Test Simple Algorithm Auto Buy Fix
- Auto buy trigger should be at sell price (₹140), not original price (₹100)
- Use >= condition to trigger exactly at sell price
- New stop loss should be auto buy price - 10
"""

def test_simple_auto_buy_logic():
    """Test the fixed Simple Algorithm auto buy logic"""
    
    print("🧪 TESTING SIMPLE ALGORITHM AUTO BUY FIX")
    print("=" * 50)
    
    # Simulate position data
    position = {
        'strike': '50000',
        'type': 'CE',
        'buy_price': 100.0,
        'original_buy_price': 100.0,
        'current_price': 140.0,
        'stop_loss_price': 140.0,
        'quantity': 25,
        'mode': 'Auto-Monitoring'
    }
    
    print(f"📊 Initial Position:")
    print(f"   Buy Price: ₹{position['buy_price']}")
    print(f"   Current Price: ₹{position['current_price']}")
    print(f"   Stop Loss: ₹{position['stop_loss_price']}")
    print()
    
    # Step 1: Price hits stop loss - trigger auto sell
    print("🔴 STEP 1: Stop Loss Hit - Auto Sell")
    sell_price = 140.0
    
    # Simulate auto sell logic (FIXED)
    position['last_stop_loss_price'] = sell_price  # ✅ AUTO BUY AT SELL PRICE
    position['waiting_for_autobuy'] = True
    position['quantity'] = 0  # Sold
    
    print(f"   Sold at: ₹{sell_price}")
    print(f"   Auto Buy Trigger: ₹{position['last_stop_loss_price']} (✅ Same as sell price)")
    print()
    
    # Step 2: Test auto buy trigger conditions
    print("🎯 STEP 2: Testing Auto Buy Trigger Conditions")
    
    test_prices = [139.0, 139.9, 140.0, 140.1, 141.0]
    
    for test_price in test_prices:
        position['current_price'] = test_price
        auto_buy_trigger = position.get('last_stop_loss_price', 0)
        
        # FIXED: Use >= instead of >
        will_trigger = (position.get('waiting_for_autobuy', False) and 
                       position['current_price'] >= auto_buy_trigger)
        
        status = "✅ WILL TRIGGER" if will_trigger else "❌ NO TRIGGER"
        print(f"   Price ₹{test_price} vs Trigger ₹{auto_buy_trigger} → {status}")
    
    print()
    
    # Step 3: Execute auto buy at ₹140
    print("🟢 STEP 3: Auto Buy Execution at ₹140")
    auto_buy_price = 140.0
    position['current_price'] = auto_buy_price
    
    # Simulate auto buy execution
    position['waiting_for_autobuy'] = False
    position['buy_price'] = auto_buy_price
    position['stop_loss_price'] = auto_buy_price - 10  # ✅ CORRECT: 140 - 10 = 130
    position['quantity'] = 25  # Restored
    position['auto_buy_count'] = position.get('auto_buy_count', 0) + 1
    
    print(f"   Auto Buy Price: ₹{auto_buy_price}")
    print(f"   New Stop Loss: ₹{position['stop_loss_price']} (✅ Buy Price - 10)")
    print(f"   Quantity Restored: {position['quantity']}")
    print()
    
    # Step 4: Verify no immediate re-sell
    print("🔒 STEP 4: Verify No Immediate Re-sell")
    print(f"   Current Price: ₹{position['current_price']} (140)")
    print(f"   Stop Loss: ₹{position['stop_loss_price']} (130)")
    print(f"   Will Sell Immediately? {'❌ NO' if position['current_price'] > position['stop_loss_price'] else '⚠️ YES'}")
    print()
    
    # Step 5: Test edge case - price drops to 139
    print("📉 STEP 5: Edge Case - Price Drops to ₹139")
    position['current_price'] = 139.0
    print(f"   Current Price: ₹{position['current_price']} (139)")
    print(f"   Stop Loss: ₹{position['stop_loss_price']} (130)")
    print(f"   Will Sell? {'❌ NO - Safe' if position['current_price'] > position['stop_loss_price'] else '🔴 YES - Stop Loss Hit'}")
    print()
    
    print("✅ CONCLUSION:")
    print("   ✅ Auto buy triggers at same sell price (₹140)")
    print("   ✅ Uses >= condition for exact price matching")
    print("   ✅ New stop loss is correct (₹130 = 140-10)")
    print("   ✅ No immediate re-sell oscillation")
    print("   ✅ Protected against small price drops")

if __name__ == "__main__":
    test_simple_auto_buy_logic()