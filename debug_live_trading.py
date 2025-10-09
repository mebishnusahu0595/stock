#!/usr/bin/env python3
"""
Debug script to check Live Trading issues
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app_state, KITE_CONFIG, LOT_SIZES, initialize_kite, td_to_zerodha_symbol
from kiteconnect import KiteConnect
import pandas as pd

def debug_live_trading():
    """Debug live trading setup and functionality"""
    print("🔍 LIVE TRADING DEBUG REPORT")
    print("=" * 50)
    
    # 1. Check Paper Trading Status
    print("\n1. TRADING MODE:")
    print(f"   📄 Paper Trading Enabled: {app_state['paper_trading_enabled']}")
    print(f"   🏦 Live Trading Mode: {'Active' if not app_state['paper_trading_enabled'] else 'Inactive'}")
    
    # 2. Check Zerodha Configuration
    print("\n2. ZERODHA CONFIGURATION:")
    print(f"   🔑 API Key: {'✅ Set' if KITE_CONFIG['api_key'] and KITE_CONFIG['api_key'] != 'your_zerodha_api_key_here' else '❌ Missing'}")
    print(f"   🔐 API Secret: {'✅ Set' if KITE_CONFIG['api_secret'] and KITE_CONFIG['api_secret'] != 'your_zerodha_api_secret_here' else '❌ Missing'}")
    print(f"   🎟️ Access Token: {'✅ Set' if KITE_CONFIG['access_token'] else '❌ Missing'}")
    print(f"   🔗 Request Token: {'✅ Set' if KITE_CONFIG['request_token'] else '❌ Missing'}")
    
    # 3. Check Kite Connection
    print("\n3. KITE CONNECTION:")
    print(f"   🔌 Kite Object: {'✅ Created' if app_state['kite'] else '❌ Not Created'}")
    print(f"   🟢 Connection Status: {'✅ Connected' if app_state['zerodha_connected'] else '❌ Disconnected'}")
    
    # 4. Test Kite Connection
    print("\n4. CONNECTION TEST:")
    try:
        if app_state['kite'] and app_state['zerodha_connected']:
            profile = app_state['kite'].profile()
            print(f"   👤 User: {profile.get('user_name', 'Unknown')}")
            print(f"   💰 Broker: {profile.get('broker', 'Unknown')}")
            print("   ✅ Connection Working")
        else:
            print("   ❌ Cannot test - No active connection")
    except Exception as e:
        print(f"   ❌ Connection Test Failed: {e}")
    
    # 5. Check Auto Trading Settings
    print("\n5. AUTO TRADING STATUS:")
    print(f"   🤖 Auto Trading Enabled: {app_state['auto_trading_enabled']}")
    print(f"   🏃 Auto Trading Running: {app_state['auto_trading_running']}")
    print(f"   📊 Auto Positions Count: {len(app_state['auto_positions'])}")
    print(f"   📋 Paper Positions Count: {len(app_state['paper_positions'])}")
    
    # 6. Check Symbol Conversion
    print("\n6. SYMBOL CONVERSION TEST:")
    test_symbols = [
        "NIFTY25081124550CE",  # Example TrueData symbol
        "BANKNIFTY25081152000PE"
    ]
    
    for td_symbol in test_symbols:
        try:
            zerodha_symbol = td_to_zerodha_symbol(td_symbol)
            print(f"   📝 {td_symbol} → {zerodha_symbol}")
        except Exception as e:
            print(f"   ❌ {td_symbol} → Conversion Failed: {e}")
    
    # 7. Check Position Monitoring
    print("\n7. POSITION MONITORING:")
    if app_state['paper_trading_enabled']:
        monitoring_positions = app_state['paper_positions']
        mode = "Paper"
    else:
        monitoring_positions = app_state['auto_positions']
        mode = "Live"
    
    print(f"   👁️ Monitoring Mode: {mode}")
    print(f"   📈 Positions Being Monitored: {len(monitoring_positions)}")
    
    if monitoring_positions:
        print("\n   Current Positions:")
        for i, pos in enumerate(monitoring_positions[:3]):  # Show first 3
            strike = pos.get('strike', 'Unknown')
            option_type = pos.get('option_type', pos.get('type', 'Unknown'))
            current_price = pos.get('current_price', 0)
            stop_loss = pos.get('stop_loss_price', 0)
            print(f"     {i+1}. {strike} {option_type} | Price: ₹{current_price} | Stop Loss: ₹{stop_loss}")
    
    # 8. Summary
    print("\n8. SUMMARY:")
    issues = []
    
    if app_state['paper_trading_enabled']:
        issues.append("ℹ️ Currently in Paper Trading mode")
    
    if not app_state['zerodha_connected']:
        issues.append("❌ Zerodha connection issue")
    
    if not app_state.get('kite'):
        issues.append("❌ Kite object not created")
    
    if len(monitoring_positions) == 0:
        issues.append("ℹ️ No positions to monitor")
    
    if not issues:
        print("   ✅ All systems working correctly!")
    else:
        for issue in issues:
            print(f"   {issue}")
    
    print("\n" + "=" * 50)
    print("🔍 DEBUG REPORT COMPLETE")

if __name__ == "__main__":
    debug_live_trading()
