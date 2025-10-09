#!/usr/bin/env python3
"""
Debug PE56000 Trailing Issue
Tests why stop loss didn't move from 537 to 547 when price went from 547.20 to 560.30
"""

def debug_pe56000_trailing():
    """Debug the specific PE56000 trailing issue"""
    
    # Simulate the exact PE56000 position
    position = {
        'strike': 56000,
        'type': 'PE',
        'manual_buy_price': 547.20,
        'buy_price': 547.20,
        'original_buy_price': 547.20,
        'current_price': 560.30,
        'highest_price': 560.30,
        'stop_loss_price': 537.20,  # Current (wrong)
        'advanced_stop_loss': 537.20,
        'algorithm_phase': 1,  # Phase 1
        'progressive_minimum': None,
        'auto_bought': False  # Manual buy
    }
    
    print("🔍 PE56000 TRAILING DEBUG")
    print("=" * 50)
    print(f"📊 POSITION DATA:")
    print(f"   Manual Buy Price: ₹{position['manual_buy_price']}")
    print(f"   Current Price: ₹{position['current_price']}")
    print(f"   Highest Price: ₹{position['highest_price']}")
    print(f"   Current Stop Loss: ₹{position['stop_loss_price']}")
    print()
    
    # Apply Phase 1 trailing logic manually
    manual_buy_price = position['manual_buy_price']
    highest_price = position['highest_price']
    profit = highest_price - manual_buy_price
    trailing_step = 10
    
    print(f"📈 TRAILING CALCULATION:")
    print(f"   Profit: ₹{highest_price} - ₹{manual_buy_price} = ₹{profit:.2f}")
    print(f"   Trailing Step: ₹{trailing_step}")
    print()
    
    if profit >= 10:  # If profit >= 10, start trailing
        profit_steps = int(profit // trailing_step)  # Number of complete 10-rupee steps
        trailing_stop_loss = manual_buy_price + (profit_steps * trailing_step)
        
        # Minimum protection: never go below manual_buy_price - 10
        minimum_sl = manual_buy_price - 10
        new_advanced_stop_loss = max(trailing_stop_loss, minimum_sl)
        
        print(f"✅ TRAILING ACTIVATED:")
        print(f"   Profit Steps: {profit_steps} (₹{profit:.2f} ÷ ₹{trailing_step})")
        print(f"   Trailing SL: ₹{manual_buy_price} + ({profit_steps}×{trailing_step}) = ₹{trailing_stop_loss}")
        print(f"   Minimum SL: ₹{minimum_sl} (buy price - 10)")
        print(f"   Final SL: max(₹{trailing_stop_loss}, ₹{minimum_sl}) = ₹{new_advanced_stop_loss}")
        print()
        
        # Expected vs Actual
        expected_sl = new_advanced_stop_loss
        current_sl = position['stop_loss_price']
        
        print(f"🎯 COMPARISON:")
        print(f"   Expected SL: ₹{expected_sl}")
        print(f"   Current SL: ₹{current_sl}")
        print(f"   Difference: ₹{expected_sl - current_sl:.2f}")
        print(f"   Status: {'✅ CORRECT' if abs(expected_sl - current_sl) < 0.01 else '❌ WRONG'}")
        
        if abs(expected_sl - current_sl) > 0.01:
            print()
            print("🚨 ISSUE DETECTED:")
            print("   Stop loss should have moved up but didn't!")
            print("   Possible causes:")
            print("   1. Advanced algorithm not being called")
            print("   2. Position not marked as manual buy correctly")
            print("   3. Highest price not being updated")
            print("   4. Stop loss not syncing from advanced_stop_loss")
    else:
        print(f"❌ NO TRAILING:")
        print(f"   Profit ₹{profit:.2f} < ₹{trailing_step} required")
        print(f"   Stop Loss remains: ₹{manual_buy_price - 10}")

    print()
    print("💡 WHAT SHOULD HAPPEN:")
    print(f"   Buy ₹547.20 → High ₹560.30 → Profit ₹13.10")
    print(f"   Steps: 1 (₹13.10 ÷ ₹10 = 1.31 → 1)")
    print(f"   New SL: ₹547.20 + (1×₹10) = ₹557.20")
    print(f"   But minimum is ₹537.20, so SL = max(₹557.20, ₹537.20) = ₹557.20")

if __name__ == "__main__":
    debug_pe56000_trailing()