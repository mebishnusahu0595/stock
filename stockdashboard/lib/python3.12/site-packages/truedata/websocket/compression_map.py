
msg_map = { "A" : [ ( "msg_code" ,   "str_var" ,  0 , 1 ) , ( "success" ,   "bool_var" ,  1 , 1 ) , ( "message" , "str_var" , 2  , 31) , ( "segments" ,   "list_var" ,  33 , 60 ) ,
                    ( "maxsymbols" ,  "int_var"  ,  93 , 4 ) , ( "subscription" , "str_var" , 97  , 20) , ("validity" , "str_var" , 117 , 10)  ], 

            "H" : [ ( "msg_code" ,   "str_var" ,  0 , 1 ) , ( "success" ,   "bool_var" ,  1 , 1 ) , ( "timestamp" ,   "epoch_var" ,  2 , 8 ) ,
                    ( "message" ,   "HeartBeat" ,  0 , 0 ) ],
            
            "M" : [ ( "msg_code" ,   "str_var" ,  0 , 1 ) , ( "success" ,   "bool_var" ,  1 , 1 ) , ( "data" ,   "str_var" ,  2 , 60 ) ,
                    ( "message" ,   "marketstatus" ,  2 , 8 ) ],
            
            "T" : [ ( "msg_code",   "str_var",  0, 1 ), ( "symbol_id",   "int_var", 1 , 4 ) , ( "timestamp",   "epoch_var",  5, 4 ),( "ltp",   "float_var",  9, 4 ),
                    ( "volume",   "int_var",  13, 4 ), ( "atp",   "float_var", 17 , 4 ), ( "total_volume",   "long_var",  21, 8 ),( "open",   "float_var",  29, 4 ),
                    ( "high",   "float_var", 33, 4 ), ( "low",   "float_var", 37 , 4 ), ( "prev_close",   "float_var",  41, 4 ),( "oi",   "long_var",  45, 8 ),
                    ( "prev_oi",   "long_var",  53, 8 ), ( "turnover",   "double_var", 61  , 8 ), ( "ohl",   "str_var",  69 , 1 ),( "seq_no",   "int_var",  70, 4 ),
                    ( "bid",   "float_var", 74, 4 ), ( "bid_qty",   "int_var", 78 , 4 ), ( "ask",   "float_var",  82, 4 ),( "ask_qty",   "int_var",  86, 4 ) ],

            "W" : [ ( "msg_code",   "str_var",  0, 1 ), ( "symbol_id",   "int_var", 1 , 4 ) , ( "timestamp",   "epoch_var",  5, 4 ),( "ltp",   "float_var",  9, 4 ),
                    ( "volume",   "int_var",  13, 4 ), ( "atp",   "float_var", 17 , 4 ), ( "total_volume",   "long_var",  21, 8 ),( "open",   "float_var",  29, 4 ),
                    ( "high",   "float_var", 33, 4 ), ( "low",   "float_var", 37 , 4 ), ( "prev_close",   "float_var",  41, 4 ),( "oi",   "long_var",  45, 8 ),
                    ( "prev_oi",   "long_var",  53, 8 ), ( "turnover",   "double_var", 61  , 8 ), ( "ohl",   "str_var",  69 , 1 ),( "seq_no",   "int_var",  70, 4 ) ],
            
            "B" : [ ( "msg_code",   "str_var",  0, 1 ), ( "symbol_id",   "int_var", 1 , 4 ) , ( "timestamp",   "epoch_var",  5, 4 ),( "bid",   "float_var",  9, 4 ),
                    ( "bid_qty",   "int_var",  13, 4 ), ( "ask",   "float_var", 17 , 4 ), ( "ask_qty",   "int_var",  21, 4 )],
            
            "D" : [ ( "msg_code",   "str_var",  0, 1 ), ( "symbol_id",   "int_var", 1 , 4 ) , ( "timestamp",   "epoch_var",  5, 4 ), ( "seq_no",   "int_var",  9, 4 ) ,
                    ( "bid_1",   "float_var",  13, 4 ), ( "bid_qty_1",   "int_var", 17 , 4 ), ( "no_bid_1",   "int_var",  21, 4 ),( "ask_1",   "float_var",  25, 4 ),
                    ( "ask_qty_1",   "int_var", 29, 4 ), ( "no_ask_1",   "int_var", 33 , 4 ), ( "bid_2",   "float_var",  37, 4 ),( "bid_qty_2",   "int_var",  45, 4 ),
                    ( "no_bid_2",   "int_var",  41, 4 ), ( "ask_2",   "float_var", 45  , 4 ), ( "ask_qty_2",   "int_var",  49 , 4 ),( "no_ask_2",   "int_var",  53, 4 ),
                    ( "bid_3",   "float_var",  57, 4 ), ( "bid_qty_3",   "int_var", 61 , 4 ), ( "no_bid_3",   "int_var",  65, 4 ),( "ask_3",   "float_var",  69, 4 ),
                    ( "ask_qty_3",   "int_var", 73, 4 ), ( "no_ask_3",   "int_var", 77 , 4 ), ( "bid_4",   "float_var",  81, 4 ),( "bid_qty_4",   "int_var",  85, 4 ),
                    ( "no_bid_4",   "int_var",  89, 4 ), ( "ask_4",   "float_var", 93  , 4 ), ( "ask_qty_4",   "int_var",  97 , 4 ),( "no_ask_4",   "int_var",  101, 4 ),
                    ( "bid_5",   "float_var",  105, 4 ),( "bid_qty_5",   "int_var",  109, 4 ), ( "no_bid_5",   "int_var",  113, 4 ), ( "ask_5",   "float_var", 117  , 4 ),
                    ( "ask_qty_5",   "int_var",  121 , 4 ),( "no_ask_5",   "int_var",  125, 4 ),( "total_bid",   "int_var",  129 , 4 ),( "total_ask",   "int_var",  133, 4 ) ],

           "G"  : [ ( "msg_code",   "str_var",  0, 1 ), ( "symbol_id",   "int_var", 1 , 4 ) , ( "timestamp",   "epoch_var",  5, 4 ),( "iv",   "double_var",  9, 8  ),
                    ( "delta",   "double_var",  17, 8 ), ( "gamma",   "double_var", 25 , 8 ), ( "theta",   "double_var",  33, 8 ) , ( "vega",   "double_var",  41, 8 ),
                    ( "rho",   "double_var",  49, 8 ) ],

           "O"  : [ ( "msg_code",   "str_var",  0, 1 ), ( "symbol_id",   "int_var", 1 , 4 ) , ( "timestamp",   "epoch_var",  5, 4 ),( "open",   "float_var",  9, 4  ),
                    ( "high",   "float_var",  13, 4 ), ( "low",   "float_var", 17 , 4 ), ( "close",   "float_var",  21, 4 ) , ( "volume",   "int_var",  25, 4 ),
                    ( "oi",   "double_var",  29, 8 )   ],
           "F"  : [ ( "msg_code",   "str_var",  0, 1 ), ( "symbol_id",   "int_var", 1 , 4 ) , ( "timestamp",   "epoch_var",  5, 4 ),( "open",   "float_var",  9, 4  ),
                    ( "high",   "float_var",  13, 4 ), ( "low",   "float_var", 17 , 4 ), ( "close",   "float_var",  21, 4 ) , ( "volume",   "int_var",  25, 4 ),
                    ( "oi",   "double_var",  29, 8 )   ],

           "S"  : [ ( "msg_code",   "str_var",  0, 1 ), ( "success",   "bool_var", 1 , 1 ) , ( "symbolsadded",   "int_var",  2, 4 ),( "total_symbols", "int_var",  6, 4 ),
                    ( "symbollist",   "add_symbol",  10, 114 ) , ( "message" ,   "symbols added" ,  0 , 0 ) ],

           "L"  : [ ( "msg_code",   "str_var",  0, 1 ), ( "success",   "bool_var", 1 , 1 ) , ( "symbolsadded",   "int_var",  2, 4 ),( "total_symbols", "int_var",  6, 4 ),
                    ( "symbollist",   "add_symbol",  10, 114 ) ,( "message" ,   "touchline" ,  0 , 0 ) ],
            
           "add_symbol" : [ ( "symbol",   "str_var",  0, 30 ), ( "symbol_id",   "int_var", 30 , 4 ) , ( "timestamp",   "epoch_var",  34, 4 ),( "ltp",   "float_var",  38, 4 ),
                    ( "volume",   "int_var",  42, 4 ), ( "atp",   "float_var", 46 , 4 ), ( "total_volume",   "long_var",  50, 8 ),( "open",   "float_var",  58, 4 ),
                    ( "high",   "float_var", 62, 4 ), ( "low",   "float_var", 66 , 4 ), ( "prev_close",   "float_var",  70, 4 ),( "oi",   "long_var",  74, 8 ),
                    ( "prev_oi",   "long_var",  82, 8 ), ( "turnover",   "double_var", 90  , 8 ),( "bid",   "float_var", 98, 4 ), ( "bid_qty",   "int_var", 102 , 4 ),
                    ( "ask",   "float_var",  106, 4 ),( "ask_qty",   "int_var",  110, 4 )],

            "R"  : [ ( "msg_code",   "str_var",  0, 1 ), ( "success",   "bool_var", 1 , 1 ) , ( "symbolsremoved",   "int_var",  2, 4 ),( "totalsymbolsubscribed", "int_var",  6, 4 ) ,
                    ( "symbollist",   "remove_symbol",  10, 34 ) ,( "message" ,   "symbols removed" ,  0 , 0 ) ],
            
            "remove_symbol" : [ ( "symbol",   "str_var",  0, 30 ), ( "symbol_id",   "int_var", 30 , 4 ) ],
                
            }

