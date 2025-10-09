from kiteconnect import KiteConnect
import pandas as pd

kite = KiteConnect(api_key="w20swyclj9h2oevg")
kite.set_access_token("z6tlef7md3k928xcz0bfbjfq1pcv8jjm")

# Download instrument list (once a day)
instruments = kite.instruments("NFO")  # for options
df = pd.DataFrame(instruments)

# Save locally
df.to_csv("zerodha_instruments.csv", index=False)
