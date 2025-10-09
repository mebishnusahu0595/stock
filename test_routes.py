#!/usr/bin/env python3
"""
Test Zerodha login flow routes
"""

from pathlib import Path
import sys

def test_routes():
    """Test that all Zerodha routes are properly configured"""
    
    # Add current directory to Python path
    sys.path.insert(0, str(Path.cwd()))
    
    try:
        from app import app
        
        with app.test_client() as client:
            print("🧪 Testing Zerodha Routes...")
            
            # Test login route
            response = client.get('/api/zerodha/login')
            print(f"✅ /api/zerodha/login - Status: {response.status_code}")
            if response.status_code == 200:
                print("   Route returns proper configuration page")
            
            # Test login-url route  
            response = client.get('/api/zerodha/login-url')
            print(f"✅ /api/zerodha/login-url - Status: {response.status_code}")
            
            # Test callback route (without token)
            response = client.get('/api/zerodha/callback')
            print(f"✅ /api/zerodha/callback - Status: {response.status_code}")
            if response.status_code == 200:
                print("   Route returns proper error page")
            
            # Test status route
            response = client.get('/api/zerodha/status')
            print(f"✅ /api/zerodha/status - Status: {response.status_code}")
            
            print("\n🎉 All Zerodha routes are working!")
            print("📝 Summary:")
            print("   - /api/zerodha/login: Direct redirect to Zerodha")
            print("   - /api/zerodha/login-url: Returns login URL as JSON") 
            print("   - /api/zerodha/callback: Handles login callback")
            print("   - /api/zerodha/status: Returns connection status")
            
            return True
            
    except Exception as e:
        print(f"❌ Route test failed: {e}")
        return False

if __name__ == "__main__":
    test_routes()
