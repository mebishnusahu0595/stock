#!/usr/bin/env python3
"""
Compare Simple vs Advanced Algorithm Side-by-Side
Show the exact differences in behavior and protection mechanisms
"""

def compare_algorithms():
    """Side-by-side comparison of Simple vs Advanced algorithms"""
    
    print("🆚 SIMPLE vs ADVANCED ALGORITHM COMPARISON")
    print("=" * 60)
    
    # Initialize identical positions for both algorithms
    simple_position = {
        'name': 'SIMPLE',
        'buy_price': 100.0,
        'current_price': 100.0,
        'stop_loss_price': 90.0,  # Simple uses this
        'quantity': 25,
        'auto_buy_count': 0
    }
    
    advanced_position = {
        'name': 'ADVANCED', 
        'buy_price': 100.0,
        'current_price': 100.0,
        'advanced_stop_loss': 90.0,  # Advanced uses this
        'progressive_minimum': 90.0,
        'highest_stop_loss': 90.0,
        'quantity': 25,
        'auto_buy_count': 0
    }
    
    print(f"🚀 STARTING CONDITIONS (Both Identical):")
    print(f"   Buy Price: ₹100 | Stop Loss: ₹90 | Quantity: 25")
    print()
    
    # Test sequence of price movements
    price_sequence = [110, 120, 130, 140, 150, 140, 145, 130, 135]
    
    print(f"📈 PRICE MOVEMENT SEQUENCE: {' → '.join([f'₹{p}' for p in price_sequence])}")
    print("=" * 60)
    
    for i, new_price in enumerate(price_sequence, 1):
        print(f"\n🔄 STEP {i}: Price moves to ₹{new_price}")
        print("-" * 40)
        
        # Update current price for both
        simple_position['current_price'] = new_price
        advanced_position['current_price'] = new_price
        
        # SIMPLE ALGORITHM LOGIC
        if new_price > simple_position['buy_price']:
            profit = new_price - simple_position['buy_price']
            steps = int(profit // 10)
            new_stop_loss = simple_position['buy_price'] + (steps * 10)
            
            if new_stop_loss > simple_position['stop_loss_price']:
                simple_position['stop_loss_price'] = new_stop_loss
        
        # ADVANCED ALGORITHM LOGIC
        if new_price > advanced_position['buy_price']:
            profit = new_price - advanced_position['buy_price']
            steps = int(profit // 10)
            calculated_stop_loss = advanced_position['buy_price'] + (steps * 10)
            
            # Apply progressive protection
            protected_stop_loss = max(calculated_stop_loss, advanced_position['progressive_minimum'])
            
            if protected_stop_loss > advanced_position['advanced_stop_loss']:
                advanced_position['advanced_stop_loss'] = protected_stop_loss
                advanced_position['highest_stop_loss'] = max(
                    advanced_position['highest_stop_loss'], 
                    protected_stop_loss
                )
                
                # ✅ FIX: Update progressive minimum AFTER highest stop loss is updated
                advanced_position['progressive_minimum'] = max(
                    advanced_position['progressive_minimum'],
                    advanced_position['highest_stop_loss'] - 20
                )
        
        # Display results
        simple_sl = simple_position['stop_loss_price']
        advanced_sl = advanced_position['advanced_stop_loss']
        
        print(f"📊 SIMPLE   : Stop Loss ₹{simple_sl}")
        print(f"🚀 ADVANCED : Stop Loss ₹{advanced_sl} | Progressive Min ₹{advanced_position['progressive_minimum']}")
        
        # Check for auto sell trigger
        simple_sell = new_price <= simple_sl
        advanced_sell = new_price <= advanced_sl
        
        if simple_sell or advanced_sell:
            print(f"\n🔴 SELL TRIGGERS:")
            if simple_sell:
                print(f"   SIMPLE: ✅ SELL at ₹{new_price} (Stop Loss ₹{simple_sl})")
                simple_position['auto_buy_trigger'] = new_price  # Fixed: same price
                simple_position['waiting_for_autobuy'] = True
                simple_position['quantity'] = 0
                
            if advanced_sell:
                print(f"   ADVANCED: ✅ SELL at ₹{new_price} (Stop Loss ₹{advanced_sl})")
                advanced_position['auto_buy_trigger'] = new_price  # Fixed: same price
                advanced_position['waiting_for_autobuy'] = True
                advanced_position['quantity'] = 0
        
        # Check for auto buy trigger
        simple_buy = (simple_position.get('waiting_for_autobuy', False) and 
                     new_price >= simple_position.get('auto_buy_trigger', 0))
        advanced_buy = (advanced_position.get('waiting_for_autobuy', False) and 
                       new_price >= advanced_position.get('auto_buy_trigger', 0))
        
        if simple_buy or advanced_buy:
            print(f"\n🟢 AUTO BUY TRIGGERS:")
            if simple_buy:
                print(f"   SIMPLE: ✅ BUY at ₹{new_price}")
                simple_position['buy_price'] = new_price
                simple_position['stop_loss_price'] = new_price - 10
                simple_position['waiting_for_autobuy'] = False
                simple_position['quantity'] = 25
                simple_position['auto_buy_count'] += 1
                
            if advanced_buy:
                print(f"   ADVANCED: ✅ BUY at ₹{new_price}")
                advanced_position['buy_price'] = new_price
                advanced_position['advanced_stop_loss'] = new_price - 10
                advanced_position['waiting_for_autobuy'] = False
                advanced_position['quantity'] = 25
                advanced_position['auto_buy_count'] += 1
                # Keep progressive minimum and highest stop loss!
    
    print(f"\n\n📋 FINAL COMPARISON SUMMARY")
    print("=" * 60)
    
    print(f"📊 SIMPLE ALGORITHM:")
    print(f"   Final Stop Loss: ₹{simple_position['stop_loss_price']}")
    print(f"   Auto Buy Count: {simple_position['auto_buy_count']}")
    print(f"   Position Status: {'Active' if simple_position['quantity'] > 0 else 'Waiting for Auto Buy'}")
    print()
    
    print(f"🚀 ADVANCED ALGORITHM:")
    print(f"   Final Stop Loss: ₹{advanced_position['advanced_stop_loss']}")
    print(f"   Progressive Minimum: ₹{advanced_position['progressive_minimum']}")
    print(f"   Highest Stop Loss Ever: ₹{advanced_position['highest_stop_loss']}")
    print(f"   Auto Buy Count: {advanced_position['auto_buy_count']}")
    print(f"   Position Status: {'Active' if advanced_position['quantity'] > 0 else 'Waiting for Auto Buy'}")
    print()
    
    # Key differences
    print(f"🔍 KEY DIFFERENCES:")
    print(f"=" * 30)
    
    protection_diff = advanced_position['progressive_minimum'] - simple_position.get('progressive_minimum', simple_position['stop_loss_price'])
    
    print(f"✅ Progressive Protection:")
    print(f"   Simple: No protection mechanism")
    print(f"   Advanced: ₹{advanced_position['progressive_minimum']} minimum (₹{protection_diff} better)")
    print()
    
    print(f"🎯 Auto Buy Mechanism:")
    print(f"   Both: ✅ Auto buy at same sell price (FIXED)")
    print(f"   Both: ✅ Use >= condition for exact price matching")
    print()
    
    print(f"🛡️ Risk Management:")
    print(f"   Simple: Basic trailing stop loss")
    print(f"   Advanced: Progressive protection + trailing stop loss")
    print()
    
    print(f"📈 Best Use Cases:")
    print(f"   Simple: Stable markets, conservative trading")
    print(f"   Advanced: Volatile markets, aggressive protection")
    
    # Real money impact
    print(f"\n💰 REAL MONEY IMPACT (25 shares):")
    simple_protection = simple_position['stop_loss_price'] * 25
    advanced_protection = advanced_position['progressive_minimum'] * 25
    savings = advanced_protection - simple_protection
    
    print(f"   Simple Protection: ₹{simple_protection:,.0f}")
    print(f"   Advanced Protection: ₹{advanced_protection:,.0f}")
    print(f"   🚀 Extra Protection: ₹{savings:,.0f}")

if __name__ == "__main__":
    compare_algorithms()