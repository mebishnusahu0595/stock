#!/usr/bin/env python3
"""
Test Zerodha API configuration
"""

import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path.cwd()))

try:
    from app import KITE_CONFIG, initialize_kite
    
    print("🔧 ZERODHA API CONFIGURATION TEST")
    print("=" * 50)
    
    print(f"✅ API Key: {KITE_CONFIG['api_key']}")
    print(f"✅ API Secret: {KITE_CONFIG['api_secret'][:10]}...")
    print(f"🔑 Access Token: {'Not set - will be generated after login' if not KITE_CONFIG['access_token'] else 'Available'}")
    
    print("\n🧪 Testing Kite Connect initialization...")
    result = initialize_kite()
    
    if result:
        print("✅ Kite Connect initialized successfully!")
        print("🎯 Ready for Zerodha login flow")
    else:
        print("❌ Kite Connect initialization failed")
    
    print("\n🚀 NEXT STEPS:")
    print("1. Start the app: python app.py")
    print("2. Open http://localhost:5000")
    print("3. Login with admin/admin123")
    print("4. Click 'Connect Zerodha' and complete login")
    print("5. Access token will be generated automatically!")
    
except Exception as e:
    print(f"❌ Configuration test failed: {e}")
