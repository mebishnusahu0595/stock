#!/usr/bin/env python3
"""
Quick Status Check Script
Checks current algorithm setting and position status
"""

import requests
import json

def check_app_status():
    """Check if app is running and get basic status"""
    try:
        response = requests.get('http://127.0.0.1:5000/api/status', timeout=5)
        if response.status_code == 200:
            data = response.json()
            print("✅ App Status: RUNNING")
            print(f"   Algorithm: {data.get('algorithm', 'UNKNOWN')}")
            print(f"   Auto Trading: {data.get('auto_trading', 'UNKNOWN')}")
            return True
        else:
            print("❌ App Status: ERROR")
            return False
    except Exception as e:
        print(f"❌ App Status: NOT RUNNING ({str(e)})")
        return False

def check_positions():
    """Check current positions"""
    try:
        response = requests.get('http://127.0.0.1:5000/api/positions', timeout=5)
        if response.status_code == 200:
            positions = response.json()
            if positions:
                print(f"✅ Positions Found: {len(positions)}")
                for pos in positions:
                    print(f"   {pos.get('tradingsymbol', 'UNKNOWN')}: Buy ₹{pos.get('average_price', 0)} | SL ₹{pos.get('stop_loss', 0)}")
            else:
                print("ℹ️  No positions found")
        else:
            print("❌ Positions API Error")
    except Exception as e:
        print(f"❌ Positions Check Failed: {str(e)}")

def main():
    print("🔍 QUICK STATUS CHECK")
    print("=" * 50)

    if check_app_status():
        check_positions()

    print("\n💡 If algorithm shows 'simple' → Change to 'advanced'")
    print("💡 If no positions → Create a test position manually")

if __name__ == "__main__":
    main()