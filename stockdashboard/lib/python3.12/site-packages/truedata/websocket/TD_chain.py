from io import StringIO
from copy import deepcopy
from datetime import datetime as dt
from datetime import time as t
from .constants import chain_live_update_column , chain_min_update_column , chain_columns , chain_fields_from_live_dict  , chain_fields_from_min_dict , chain_greek_fields 
import pandas as pd
import re
import numpy as np
import time



class OptionChain:

    chain_url ='https://api.truedata.in/getOptionChain?'

    def __init__(self, TD_OBJ , symbol ,expiry , chain_length ,atm , strike_step , bid_ask , subs , greek_status):
        self.TD_OBJ = TD_OBJ
        self.symbol = symbol
        self.expiry = expiry
        self.chain_length = chain_length
        self.atm = atm
        self.strike_step = strike_step
        self.subscription = subs
        self.bid_ask = bid_ask
        self.greek_status = greek_status
        self.option_symbols = self.get_option_symbols( atm = self.atm)
        self.chain_dataframe =  self.init_dataframe()
        self.chain_status = False

    def get_option_symbols(self , atm ):
        expiry = self.expiry.strftime('%y%m%d')
        start_strike = atm - self.strike_step * int(self.chain_length / 2 )
        end_strike = atm + self.strike_step * int( self.chain_length / 2)
        req_strikes = np.arange( start_strike , end_strike  , self.strike_step )
        if isinstance( self.strike_step , float ) :
            req_strikes = list(map(lambda x: int(x) if x.is_integer() else x , req_strikes))
        symbols = list(map(lambda x: f'{self.symbol}{expiry}{x}CE', req_strikes))
        symbols.extend(list(map(lambda x: f'{self.symbol}{expiry}{x}PE', req_strikes )))
        return symbols

    def init_dataframe(self):
        my_chain_columns = deepcopy(chain_columns)
        my_chain_columns.extend(chain_greek_fields) if self.greek_status else chain_columns
        df = pd.DataFrame(columns= my_chain_columns) if self.subscription == 'tick' else pd.DataFrame(columns= my_chain_columns[:-4])
        df.symbols = self.option_symbols
        df.strike = df.symbols.apply(lambda x: str(re.search(r"\d+(\.\d+)?", x ).group(0) )[6:])
        df.type = df.symbols.apply(lambda x: re.findall(r'\D+' , x )[-1] )
        df.set_index('symbols' , inplace=True)
        df.sort_values(by=['strike' , 'type'] , inplace=True)
        return df

    def initial_update_from_touchline(self , data_dict , equivalent_fields , column):
        for symbol in self.option_symbols:
            try:
                tick_data = data_dict[symbol]
                live_data_attributes = list(map(lambda x: getattr(tick_data , x), equivalent_fields))
                self.chain_dataframe.loc[symbol , column] = live_data_attributes
            except TypeError:
                self.chain_dataframe.loc[symbol , column] = [ np.NaN for i in range(14)]
            except KeyError:
                pass
       
    def update_chain(self ):
        self.chain_status = True
        data_dict = self.TD_OBJ.live_data if self.subscription == 'tick' else self.TD_OBJ.one_min_live_data 
        chain_equivalent_columns = chain_live_update_column if self.subscription == 'tick' else chain_min_update_column
        equivalent_fields = chain_fields_from_live_dict if self.subscription == 'tick' else chain_fields_from_min_dict
        self.initial_update_from_touchline( data_dict = data_dict , equivalent_fields = equivalent_fields , column = chain_equivalent_columns )
        while self.chain_status:
            for symbol in self.option_symbols:
                try:
                    tick_data = data_dict[symbol]
                    live_data_attributes = list(map(lambda x: getattr(tick_data , x), equivalent_fields))
                    self.chain_dataframe.loc[symbol , chain_equivalent_columns] = live_data_attributes
                    if self.greek_status and symbol in self.TD_OBJ.greek_data.keys():
                        greek_data = self.TD_OBJ.greek_data[symbol]
                        greek_data_attributes = list(map(lambda x: getattr(greek_data , x), chain_greek_fields))
                        self.chain_dataframe.loc[symbol , chain_greek_fields] = greek_data_attributes
                except KeyError:
                    pass
            time.sleep(1)

    def get_option_chain(self):
        df = self.chain_dataframe.copy()
        # print(df)''
        df.dropna(subset= ['ltt'] , inplace=True)
        df = df.astype({'ltq' : np.int64 , 'volume': np.int64 })
        if not self.bid_ask and 'bid' in df.columns:
            df = df.drop(['bid' , 'bid_qty' , 'ask' , 'ask_qty'] , axis= 1  )
        return df

    def stop_option_chain(self):
        self.chain_status = False
        self.TD_OBJ.stop_live_data(self.option_symbols)

