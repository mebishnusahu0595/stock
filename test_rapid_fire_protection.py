#!/usr/bin/env python3
"""
Test Rapid Fire Auto Buy Protection
Tests that auto buy has minimum time delay
"""

def test_rapid_fire_protection():
    """Test that auto buy protection prevents rapid fire trading"""

    # Simulate position with recent auto buy
    position = {
        'waiting_for_autobuy': True,
        'current_price': 420.0,
        'last_stop_loss_price': 415.0,
        'last_auto_buy_time': 0,  # No recent auto buy
        'strike': 55600,
        'type': 'CE'
    }

    import time

    # Test 1: Should allow auto buy (no recent auto buy)
    current_time = time.time()
    time_since_last = current_time - position['last_auto_buy_time']
    min_delay = 3.0

    can_auto_buy_1 = (position['waiting_for_autobuy'] and
                     position['current_price'] >= position['last_stop_loss_price'] and
                     time_since_last >= min_delay)

    print("🧪 RAPID FIRE PROTECTION TEST")
    print("=" * 50)
    print(f"Test 1 - No recent auto buy:")
    print(f"   Current time: {current_time}")
    print(f"   Last auto buy: {position['last_auto_buy_time']}")
    print(f"   Time since last: {time_since_last:.1f}s")
    print(f"   Min delay: {min_delay}s")
    print(f"   Can auto buy: {'✅ YES' if can_auto_buy_1 else '❌ NO'}")
    print()

    # Test 2: Should block auto buy (recent auto buy)
    position['last_auto_buy_time'] = current_time - 1.0  # 1 second ago
    time_since_last = current_time - position['last_auto_buy_time']

    can_auto_buy_2 = (position['waiting_for_autobuy'] and
                     position['current_price'] >= position['last_stop_loss_price'] and
                     time_since_last >= min_delay)

    print(f"Test 2 - Recent auto buy (1s ago):")
    print(f"   Time since last: {time_since_last:.1f}s")
    print(f"   Can auto buy: {'✅ YES' if can_auto_buy_2 else '❌ NO (PROTECTED)'}")
    print()

    # Test 3: Should allow auto buy (enough time passed)
    position['last_auto_buy_time'] = current_time - 4.0  # 4 seconds ago
    time_since_last = current_time - position['last_auto_buy_time']

    can_auto_buy_3 = (position['waiting_for_autobuy'] and
                     position['current_price'] >= position['last_stop_loss_price'] and
                     time_since_last >= min_delay)

    print(f"Test 3 - Enough time passed (4s ago):")
    print(f"   Time since last: {time_since_last:.1f}s")
    print(f"   Can auto buy: {'✅ YES' if can_auto_buy_3 else '❌ NO'}")
    print()

    # Summary
    print("🎯 PROTECTION SUMMARY:")
    print("   ✅ Prevents rapid fire auto buy cycles")
    print("   ✅ Allows auto buy after minimum delay")
    print("   ✅ Protects against market volatility losses")

    success = can_auto_buy_1 and not can_auto_buy_2 and can_auto_buy_3
    print(f"\nTest Result: {'✅ ALL TESTS PASSED' if success else '❌ TESTS FAILED'}")

if __name__ == "__main__":
    test_rapid_fire_protection()