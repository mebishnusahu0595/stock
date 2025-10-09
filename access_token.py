from kiteconnect import KiteConnect

# Step 1: Setup
api_key = "w20swyclj9h2oevg"
api_secret = "z6tlef7md3k928xcz0bfbjfq1pcv8jjm"
request_token = "4qOrJQeUtAsB1G4uX6YEirP68NngXHwf"  

# Step 2: Connect to Kite
kite = KiteConnect(api_key=api_key)

# Step 3: Generate Access Token
data = kite.generate_session(request_token, api_secret=api_secret)
access_token = data["access_token"]

# Step 4: Set the access token for future use
kite.set_access_token(access_token)

print("Access Token:", access_token)


#  'w20swyclj9h2oevg',  # Your Zerodha API key
#     'api_secret': 'z6tlef7md3k928xcz0bfbjfq1pcv8jjm'
