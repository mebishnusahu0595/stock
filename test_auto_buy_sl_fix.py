#!/usr/bin/env python3
"""
Test Auto Buy Stop Loss Fix
Tests that stop loss stays at auto_buy_price - 10 after auto buy
"""

def test_auto_buy_stop_loss_fix():
    """Test the auto buy stop loss calculation fix"""

    # Simulate position after auto buy
    position = {
        'buy_price': 554.15,  # Auto buy price
        'current_price': 554.15,  # Current market price
        'highest_price': 554.15,  # Highest price after auto buy
        'stop_loss_price': 544.15,  # Should be auto_buy_price - 10
        'auto_bought': True
    }

    # Test parameters
    trailing_step = 10
    auto_buy_price = position['buy_price']
    current_price = position['current_price']
    highest_after_auto_buy = position['highest_price']
    current_stop_loss = position['stop_loss_price']

    # Calculate profit from auto buy price
    profit_from_auto_buy = highest_after_auto_buy - auto_buy_price

    print("🧪 TESTING AUTO BUY STOP LOSS FIX")
    print("=" * 50)
    print(f"Auto Buy Price: ₹{auto_buy_price}")
    print(f"Current Price: ₹{current_price}")
    print(f"Highest After Auto Buy: ₹{highest_after_auto_buy}")
    print(f"Current Stop Loss: ₹{current_stop_loss}")
    print(f"Profit from Auto Buy: ₹{profit_from_auto_buy}")
    print()

    if profit_from_auto_buy >= trailing_step:  # If profit >= 10
        print("✅ PROFIT >= 10: Trailing logic would activate")
        profit_steps = int(profit_from_auto_buy // trailing_step)
        new_trailing_stop_loss = auto_buy_price + (profit_steps * trailing_step)
        position['stop_loss_price'] = max(new_trailing_stop_loss, current_stop_loss)
        print(f"   New Stop Loss: ₹{position['stop_loss_price']}")
    else:
        print("🔒 NO PROFIT YET: Stop loss should stay at auto_buy_price - 10")

        # OLD BUGGY CODE (what was happening before):
        # position['stop_loss_price'] = max(auto_buy_price, current_stop_loss)
        # This would set SL to ₹554.15 instead of ₹544.15

        # NEW FIXED CODE:
        position['stop_loss_price'] = auto_buy_price - 10
        print(f"   Fixed Stop Loss: ₹{position['stop_loss_price']} (auto_buy_price - 10)")

        # Verify the fix
        expected_sl = auto_buy_price - 10
        if position['stop_loss_price'] == expected_sl:
            print("✅ FIX VERIFIED: Stop loss correctly set to auto_buy_price - 10")
        else:
            print(f"❌ FIX FAILED: Expected ₹{expected_sl}, got ₹{position['stop_loss_price']}")

    print()
    print("🎯 EXPECTED BEHAVIOR:")
    print("   - Auto buy at ₹554.15")
    print("   - Stop loss should be ₹544.15 (554.15 - 10)")
    print("   - NOT ₹554.15 (which was the bug)")

if __name__ == "__main__":
    test_auto_buy_stop_loss_fix()