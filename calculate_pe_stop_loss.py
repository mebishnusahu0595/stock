#!/usr/bin/env python3
"""
Stop Loss Calculator for Advanced Algorithm
User Query: "buy 716 pe kiya abhi current 739 chal rha toh stop loss kya hona chhaiye?"

Advanced Algorithm Logic:
1. Initial stop loss = buy_price - 10
2. When price goes up, trailing happens in steps of 10
3. Stop loss = original_buy_price + (complete_steps × 10)
4. Progressive minimum protection = highest_stop_loss - 20
"""

def calculate_advanced_stop_loss(buy_price, current_price):
    """Calculate stop loss using Advanced Algorithm logic"""
    
    print(f"🔍 ADVANCED ALGORITHM STOP LOSS CALCULATION")
    print(f"=" * 50)
    print(f"📊 Trade Details:")
    print(f"   Buy Price: ₹{buy_price}")
    print(f"   Current Price: ₹{current_price}")
    print(f"   Current Profit: ₹{current_price - buy_price:.2f}")
    print()
    
    # Step 1: Initial stop loss (buy_price - 10)
    initial_stop_loss = buy_price - 10
    print(f"1️⃣ Initial Stop Loss = ₹{buy_price} - 10 = ₹{initial_stop_loss}")
    
    # Step 2: Calculate profit and trailing steps
    profit = current_price - buy_price
    trailing_step = 10  # From config
    
    if profit >= 10:
        # Calculate complete steps
        profit_steps = int(profit // trailing_step)
        
        # Advanced Algorithm Formula: SL = buy_price + (steps × 10)
        new_stop_loss = buy_price + (profit_steps * trailing_step)
        
        print(f"2️⃣ Trailing Calculation:")
        print(f"   Profit: ₹{profit:.2f}")
        print(f"   Complete Steps: {profit_steps} (₹{profit:.2f} ÷ 10)")
        print(f"   Advanced SL = ₹{buy_price} + ({profit_steps} × 10) = ₹{new_stop_loss}")
        
        # Step 3: Progressive minimum (highest_stop_loss - 20)
        highest_stop_loss = new_stop_loss  # Assuming this is the highest so far
        progressive_minimum = highest_stop_loss - 20
        
        print(f"3️⃣ Progressive Protection:")
        print(f"   Highest Stop Loss: ₹{highest_stop_loss}")
        print(f"   Progressive Minimum: ₹{highest_stop_loss} - 20 = ₹{progressive_minimum}")
        
        # Final stop loss (max of calculated and progressive minimum)
        final_stop_loss = max(new_stop_loss, progressive_minimum)
        
        print(f"4️⃣ Final Stop Loss:")
        print(f"   Final SL = max(₹{new_stop_loss}, ₹{progressive_minimum}) = ₹{final_stop_loss}")
        
        if final_stop_loss > new_stop_loss:
            protection = final_stop_loss - new_stop_loss
            print(f"   🛡️ Protection Applied: +₹{protection:.2f}")
            
    else:
        final_stop_loss = initial_stop_loss
        print(f"2️⃣ No Trailing (Profit < ₹10)")
        print(f"   Current Stop Loss: ₹{final_stop_loss}")
    
    print()
    print(f"💰 RESULT:")
    print(f"   Current Stop Loss: ₹{final_stop_loss}")
    print(f"   Risk per Share: ₹{current_price - final_stop_loss:.2f}")
    
    return final_stop_loss

# User's trade scenario
buy_price = 716
current_price = 739

print("🏷️ USER TRADE SCENARIO:")
print("Buy 716 PE kiya, abhi current 739 chal rha")
print()

stop_loss = calculate_advanced_stop_loss(buy_price, current_price)

print()
print("🎯 SUMMARY:")
print(f"✅ Your current stop loss should be: ₹{stop_loss}")
print(f"📈 If price goes to ₹749, stop loss will trail to ₹{buy_price + (int((749-buy_price) // 10) * 10)}")
print(f"📉 If price drops to ₹{stop_loss}, position will auto sell")