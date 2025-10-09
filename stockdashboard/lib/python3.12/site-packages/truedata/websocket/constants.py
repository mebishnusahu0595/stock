tick_fields = [ "timestamp","symbol_id","symbol","ltp","ltq","atp","ttq","day_open","day_high","day_low","prev_day_close",
                     "oi","prev_day_oi","turnover","special_tag","tick_seq","best_bid_price","best_bid_qty","best_ask_price",
                     "best_ask_qty","change","change_perc","oi_change","oi_change_perc" ]

bar_fields = ["symbol" ,"symbol_id",  "timestamp", "bar_open", "bar_high", "bar_low", "bar_close", "bar_volume", "oi", "ttq" ]

extended_bar_fields = ["symbol" ,"symbol_id",  "timestamp", "bar_open", "bar_high", "bar_low", "bar_close", "bar_volume", "oi", "ttq" , "change","change_perc","oi_change","oi_change_perc" ]

bid_ask_fields =    [ "timestamp", "symbol_id", "symbol", "bid", "ask", "total_bid", "total_ask" ]

greek_fields = [ "timestamp", "symbol_id", "symbol", "iv", "delta", "theta", "gamma", "vega", "rho" ] 

full_feed_fields = [ "timestamp", "symbol_id", "symbol", "ltp", "ltq", "atp", "ttq", "day_open", "day_high", 
                    "day_low" , "prev_day_close", "oi", "prev_day_oi", "turnover", "tick_seq", "best_bid_price",
                    "best_bid_qty", "best_ask_price", "best_ask_qty" ]

min_fields = [ "symbol", "symbol_id", "day_open", "day_high", "day_low", "prev_day_close", "prev_day_oi", "oi",
        "ttq", "timestamp", "open", "high", "low", "close", "volume", "change","change_perc","oi_change","oi_change_perc" ]

chain_columns = ['symbols' , 'strike' , 'type' , 'ltp' , 'ltt' , 'ltq' , 'volume' , 'price_change' , 'price_change_perc', 'oi' , 
                'prev_oi' , 'oi_change' , 'oi_change_perc' , 'bid' , 'bid_qty' , 'ask' , 'ask_qty']

chain_live_update_column = ['ltp' , 'ltt'  , 'ltq' , 'volume' ,'price_change' , 'price_change_perc' , 'oi' , 'prev_oi',
                'oi_change' , 'oi_change_perc','bid' , 'bid_qty' , 'ask' , 'ask_qty' ]

chain_min_update_column = chain_live_update_column[:-4]

chain_fields_from_live_dict = [ "ltp", "timestamp", "ltq", "ttq", "change", "change_perc", "oi", "prev_day_oi",
                                "oi_change", "oi_change_perc", "best_bid_price", "best_bid_qty","best_ask_price", "best_ask_qty" ]

chain_fields_from_min_dict = [ "close", "timestamp", "volume", "ttq", "change", "change_perc", "oi", "prev_day_oi",
                                "oi_change", "oi_change_perc",  ]

chain_greek_fields =  ["iv", "delta", "theta", "gamma", "vega", "rho" ]