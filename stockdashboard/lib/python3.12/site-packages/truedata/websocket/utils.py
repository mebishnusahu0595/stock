from dataclasses import dataclass, field
from io import StringIO
from typing import List , Optional
from collections import namedtuple
from .constants import tick_fields , bar_fields , bid_ask_fields , greek_fields , full_feed_fields, min_fields, extended_bar_fields
from .exceptions import TDLiveCalcError
from colorama import Style, Fore    
from datetime import datetime as dt , timezone, timedelta
from .compression_map import msg_map
import shutil
import pickle
import requests
import os
import pandas as pd
from tqdm import tqdm as tq
import lz4.block , lz4.frame
import struct


@dataclass
class TouchlineData:
    raw_data : List[any] = field(init = True , repr = False)

    def __post_init__(self):
        self.symbol = self.raw_data[0]
        self.symbol_id = self.raw_data[1]
        self.timestamp = dt.strptime(self.raw_data[2], '%Y-%m-%dT%H:%M:%S')
        self.ltp = float(self.raw_data[3])
        self.ltq = float(self.raw_data[4])
        self.atp = float(self.raw_data[5])
        self.ttq = int(self.raw_data[6])
        self.day_open = float(self.raw_data[7])
        self.day_high = float(self.raw_data[8])
        self.day_low = float(self.raw_data[9])
        self.prev_day_close = float(self.raw_data[10])
        self.oi = int(self.raw_data[11])
        self.prev_day_oi = int(self.raw_data[12])
        self.turnover = float(self.raw_data[13])
        self.best_bid_price = float(self.raw_data[14])
        self.best_bid_qty = float(self.raw_data[15])
        self.best_ask_price = float(self.raw_data[16])
        self.best_ask_qty = float(self.raw_data[17])
        

@dataclass
class tick_feed:
    touchline: TouchlineData = field(init = True , repr = False)
    
    def __post_init__(self):
        self.timestamp = self.touchline.timestamp
        self.symbol = self.touchline.symbol
        self.symbol_id = self.touchline.symbol_id
        self.ltp = self.touchline.ltp
        self.ltq = self.touchline.ltq
        self.atp = self.touchline.atp
        self.ttq = self.touchline.ttq
        self.day_open = self.touchline.day_open
        self.day_high = self.touchline.day_high
        self.day_low = self.touchline.day_low
        self.prev_day_close = self.touchline.prev_day_close
        self.oi = self.touchline.oi
        self.prev_day_oi = self.touchline.prev_day_oi
        self.turnover = self.touchline.turnover
        self.special_tag = ""
        self.tick_seq = None
        self.best_bid_price = self.touchline.best_bid_price
        self.best_bid_qty = self.touchline.best_bid_qty
        self.best_ask_price = self.touchline.best_ask_price
        self.best_ask_qty = self.touchline.best_ask_qty

    def __repr__(self):
        tick_tuple = namedtuple('tick_feed', field_names= tick_fields)
        attributes = list(map(lambda x: getattr(self , x), tick_fields))
        return str(tick_tuple(*attributes))    
    
    def to_dict(self):
        return dict(map(lambda x: (x , getattr(self , x) ), tick_fields))
    
    @property
    def change(self):
        try:
            return self.ltp - self.prev_day_close
        except Exception as e:
            raise TDLiveCalcError(f"Encountered other change calculation error: {e} with symbol {self.symbol} and tick_seq={self.tick_seq}")
            
    @property
    def oi_change(self):
        try:
            return self.oi - self.prev_day_oi
        except Exception as e:
            raise TDLiveCalcError(f"Encountered other change calculation error: {e} with symbol {self.symbol} and tick_seq={self.tick_seq}")
       
    @property
    def change_perc(self):
        try:
            return self.change * 100 / self.prev_day_close
        except ZeroDivisionError:
            return 0
        except Exception as e:
            raise TDLiveCalcError(f"Encountered other change calculation error: {e} with symbol {self.symbol} and tick_seq={self.tick_seq}")
   
    @property
    def oi_change_perc(self):
        try:
            return self.oi_change * 100 / self.prev_day_oi
        except ZeroDivisionError:
            return 0
        except Exception as e:
            raise TDLiveCalcError(f"Encountered other change calculation error: {e} with symbol {self.symbol} and tick_seq={self.tick_seq}")
        
@dataclass
class min_feed:

    touchline: TouchlineData = field(init = True , repr = False)
    
    def __post_init__(self):
        self.symbol = self.touchline.symbol
        self.symbol_id = self.touchline.symbol_id
        self.day_open = self.touchline.day_open
        self.day_high = self.touchline.day_high
        self.day_low = self.touchline.day_low
        self.prev_day_close = self.touchline.prev_day_close
        self.prev_day_oi = self.touchline.prev_day_oi
        self.oi = self.touchline.oi
        self.ttq = self.touchline.ttq
        self.timestamp = None
        self.open = None
        self.high = None
        self.low = None
        self.close = None
        self.volume = None

    def __repr__(self):
        min_feed_tuple = namedtuple('min_feed', field_names= min_fields)
        attributes = list(map(lambda x: getattr(self , x), min_fields))
        return str(min_feed_tuple(*attributes))    
    
    def to_dict(self):
        return dict(map(lambda x: (x , getattr(self , x) ), min_fields))

    @property
    def change(self):
        try:
            return self.close - self.prev_day_close
        except TypeError:
            return 0
        except Exception as e:
            raise TDLiveCalcError(f"Encountered other change calculation error: {e} with symbol {self.symbol} with timestamp={self.timestamp}")
       
    @property
    def oi_change(self):
        try:
            return self.oi - self.prev_day_oi
        except Exception as e:
            raise TDLiveCalcError(f"Encountered other change calculation error: {e} with symbol {self.symbol} with timestamp={self.timestamp}")

    @property
    def change_perc(self):
        try:
            return self.change * 100 / self.prev_day_close
        except ZeroDivisionError:
            return 0
        except Exception as e:
            raise TDLiveCalcError(f"Encountered other change calculation error: {e} with symbol {self.symbol} with timestamp={self.timestamp}")

    @property
    def oi_change_perc(self):
        try:
            return self.oi_change * 100 / self.prev_day_oi
        except ZeroDivisionError:
            return 0
        except Exception as e:
            raise TDLiveCalcError(f"Encountered other change calculation error: {e} with symbol {self.symbol} with timestamp={self.timestamp}")


@dataclass
class full_feed:
    raw_tick : List[any] = field(init = True , repr = False )
    symbol : str = field(init = True )

    def __post_init__(self):
        self.symbol_id = int(self.raw_tick[0])
        self.timestamp = dt.strptime(self.raw_tick[1], '%Y-%m-%dT%H:%M:%S')
        self.ltp = float(self.raw_tick[2])
        self.ltq = int (self.raw_tick[3])
        self.atp = float(self.raw_tick[4])
        self.ttq = float(self.raw_tick[5])
        self.day_open =  float(self.raw_tick[6])
        self.day_high = float(self.raw_tick[7])
        self.day_low = float(self.raw_tick[8])
        self.prev_day_close = float(self.raw_tick[9])
        self.oi = int(self.raw_tick[10])
        self.prev_day_oi = int(self.raw_tick[11])
        self.turnover = float(self.raw_tick[12])
        self.tick_seq = int(self.raw_tick[14])
        if len(self.raw_tick) > 15:
            self.best_bid_price = float(self.raw_tick[15])
            self.best_bid_qty   =  int(float(self.raw_tick[16]))
            self.best_ask_price = float(self.raw_tick[17])
            self.best_ask_qty   = int(float(self.raw_tick[18]))
        else:
            self.best_bid_price = 0
            self.best_bid_qty   =  0
            self.best_ask_price = 0
            self.best_ask_qty   = 0

    def __repr__(self):
        full_feed_tuple = namedtuple('full_feed', field_names= full_feed_fields)
        attributes = list(map(lambda x: getattr(self , x), full_feed_fields))
        return str(full_feed_tuple(*attributes))    
    
    def to_dict(self):
        return dict(map(lambda x: (x , getattr(self , x) ), full_feed_fields))


@dataclass
class bidask_feed:
    raw_tick : List[any] = field(init = True , repr = False )
    level : str = field(init = True , repr = False )
    symbol : str = field(init = True )

    def __post_init__(self):
        self.symbol_id = int(self.raw_tick[0])
        self.timestamp = dt.strptime(self.raw_tick[1], '%Y-%m-%dT%H:%M:%S')
        if self.level == "L1":
            self.bid = [ ( float(self.raw_tick[2]) , int(float(self.raw_tick[3])) ) ]
            self.ask = [ ( float(self.raw_tick[4]) , int(float(self.raw_tick[5])) ) ]
            self.total_bid = None
            self.total_ask = None
        elif self.level == "L2":
            bidask = list(zip(*[iter(self.raw_tick[3:])]*3) )
            self.bid = bidask[0:5]
            self.ask = bidask[5:]
            self.total_bid = self.raw_tick[-2]
            self.total_ask = self.raw_tick[-1]
    
    def __repr__(self):
        bid_ask_tuple = namedtuple('bidask_feed', field_names= bid_ask_fields)
        attributes = list(map(lambda x: getattr(self , x), bid_ask_fields))
        return str(bid_ask_tuple(*attributes))    

    def to_dict(self):
        return dict(map(lambda x: (x , getattr(self , x) ), bid_ask_fields))


@dataclass
class bar_feed:
    raw_tick : List[any]= field(init = True , repr = False )
    symbol :str = field(init = True)
    change_bar:bool = field(init = True , repr = False)
    prev_day_values: Optional[List] = field(default=None)  
    
    def __post_init__(self):
        self.symbol_id  = int(self.raw_tick[1])
        self.timestamp  = dt.strptime(self.raw_tick[0], '%Y-%m-%dT%H:%M:%S')
        self.bar_open   = float(self.raw_tick[2])
        self.bar_high   = float (self.raw_tick[3])
        self.bar_low    = float(self.raw_tick[4])
        self.bar_close  = float(self.raw_tick[5])
        self.bar_volume =  int(self.raw_tick[6])
        self.oi         = int(self.raw_tick[7])
        self.ttq        = int(self.raw_tick[8])
        if self.prev_day_values:
            self.prev_day_close =  self.prev_day_values['pclose']
            self.prev_day_oi = self.prev_day_values['poi']  
            

    def __repr__(self):
        bar_map_fields = bar_fields if not self.change_bar else extended_bar_fields
        bar_tuple = namedtuple('bar_feed', field_names= bar_map_fields)
        attributes = list(map(lambda x: getattr(self , x), bar_map_fields))
        return str(bar_tuple(*attributes)) 
    
    def to_dict(self):
        bar_map_fields = bar_fields if not self.change_bar else extended_bar_fields
        return dict(map(lambda x: (x , getattr(self , x) ), bar_map_fields))
    
    @property
    def change(self):
        try:
            return self.bar_close - self.prev_day_close if self.change_bar else None
        except Exception as e:
            raise TDLiveCalcError(f"Encountered other change calculation error: {e} with symbol {self.symbol} and tick_seq={self.tick_seq}")
            
    @property
    def oi_change(self):
        try:
            return self.oi - self.prev_day_oi if self.change_bar else None
        except Exception as e:
            raise TDLiveCalcError(f"Encountered other change calculation error: {e} with symbol {self.symbol} and tick_seq={self.tick_seq}")
       
    @property
    def change_perc(self):
        try:
            return self.change * 100 / self.prev_day_close if self.change_bar else None
        except ZeroDivisionError:
            return 0
        except Exception as e:
            raise TDLiveCalcError(f"Encountered other change calculation error: {e} with symbol {self.symbol} and tick_seq={self.tick_seq}")
   
    @property
    def oi_change_perc(self):
        try:
            return self.oi_change * 100 / self.prev_day_oi if self.change_bar else None
        except ZeroDivisionError:
            return 0
        except Exception as e:
            raise TDLiveCalcError(f"Encountered other change calculation error: {e} with symbol {self.symbol} and tick_seq={self.tick_seq}")


@dataclass
class greek_feed:
    raw_tick : List[any] = field(init = True , repr = False )
    symbol :str = field(init = True)
    
    def __post_init__(self):
        self.symbol_id  = int(self.raw_tick[0])
        self.timestamp  = dt.strptime(self.raw_tick[1], '%Y-%m-%dT%H:%M:%S')
        self.iv     = float(self.raw_tick[2])
        self.delta  = float (self.raw_tick[3])
        self.theta  = float(self.raw_tick[4])
        self.gamma  = float(self.raw_tick[5])
        self.vega   =  float(self.raw_tick[6])
        self.rho    = float(self.raw_tick[7])

    def __repr__(self):
        greek_tuple = namedtuple('greek_feed', field_names= greek_fields)
        attributes = list(map(lambda x: getattr(self , x), greek_fields))
        return str(greek_tuple(*attributes))    
    
    def to_dict(self):
        return dict(map(lambda x: (x , getattr(self , x) ), greek_fields))

       
def get_symbol_id(segments , url , user_id , password , cache_dir):
    cache_df = pd.DataFrame()
    params =  { 'user': user_id ,'password' : password, 'csv':'true' }
    for segment in tq(segments):
        params.update({'segment': f'{segment}'.lower(),})
        response = requests.get(url, params= params).text
        df = pd.read_csv(StringIO(response) , dtype='unicode' )
        cache_df = cache_df.join(df , how = 'right' ) if cache_df.empty else pd.concat( [cache_df , df] , ignore_index= True )  
    os.makedirs(cache_dir , exist_ok=True )
    with open( f"{cache_dir}/sym_cache_{dt.now().strftime('%d%m%y')}.pkl" , 'wb') as pkl:
        cache_df.set_index('symbolid' , inplace = True )
        pickle.dump(cache_df , pkl)

def cache_symbol_id(username , password , td_obj ):
    if os.name == 'nt':
        sym_cache_dir = '/'.join(__file__.split('\\')[:-1]) + '/cache/sym_cache/'
    else: 
        sym_cache_dir = '/'.join(__file__.split('/')[:-1]) + '/cache/sym_cache/'
    url = 'https://api.truedata.in/getprevcloseandoi?'
    segments = [ "EQ", "FO" , "MCX" , "CDS" , "IN" , "BSEEQ", "BSEFO" ]
    if not os.path.exists(sym_cache_dir) or not os.path.exists(f'{sym_cache_dir}/sym_cache_{dt.now().strftime("%d%m%y")}.pkl'):
        td_obj.logger.warning(f'{Style.NORMAL}{Fore.BLUE}please wait two minute to download master contracts for today{Style.RESET_ALL}')
        shutil.rmtree(sym_cache_dir, ignore_errors=True, onerror=None)
        get_symbol_id(segments , url , username , password , sym_cache_dir )
    with open( f"{sym_cache_dir}/sym_cache_{dt.now().strftime('%d%m%y')}.pkl" , 'rb') as pkl:
        cache_df = pickle.load(pkl)
        symbols_map = cache_df['symbol'].to_dict()
    return symbols_map , cache_df

def remove_all_cache():
    if os.name == 'nt':
        cache_dir = '/'.join(__file__.split('\\')[:-1]) + '/cache'
    else: 
        cache_dir = '/'.join(__file__.split('/')[:-1]) + '/cache'
    shutil.rmtree(cache_dir, ignore_errors=True, onerror=None)
    

def get_atm(username , password , symbol , expiry):
    url = "https://api.truedata.in/getATMStrike?"
    expiry = expiry.strftime("%Y%m%d")
    params = {"user": username, "password": password, "symbol": symbol , "expiry": expiry}
    response = requests.get(url , params= params)
    return response.json()['Records'].values()


def get_chunks(data , chunk_size ):
    indices = range(0, len(data), chunk_size)
    chunks = list(map(lambda i: data[i:i + chunk_size], indices))
    return chunks

def map_data_with_types(map_type , data):
    # print(map_type , data)
    start = map_type[2]
    end = start + map_type[3]
    match map_type[1]:
        case "str_var":
            return (map_type[0] , data[start:end].decode('utf-8').strip())
        case "bool_var":
            return (map_type[0] , bool(struct.unpack('<?', data[start:end])[0]))
        case "list_var":
            return (map_type[0] , data[start:end].decode('utf-8').strip().split(','))
        case "int_var":
            return (map_type[0] , struct.unpack('<i' , data[start:end])[0])
        case "long_var":
            return (map_type[0] , struct.unpack('<Q' , data[start:end])[0])
        case "float_var":
            return (map_type[0] , round(struct.unpack('<f' , data[start:end])[0],2))
        case "double_var":
            return (map_type[0] , struct.unpack('<d' , data[start:end])[0])
        case "epoch_var":
            epoch =  struct.unpack('<i' , data[start:end])[0] if map_type[3] == 4 else int(str(struct.unpack('<Q' , data[start:end])[0])[:-3])
            timestamp = dt.fromtimestamp(epoch , tz=timezone.utc).replace(tzinfo=None)
            return (map_type[0] , timestamp.strftime("%Y-%m-%dT%H:%M:%S"))
        case "add_symbol":
            chunks = get_chunks( data = data[start:] , chunk_size= map_type[3] )
            map_fields_with_bytes = msg_map["add_symbol"]
            symbol_data = []
            for chunk in chunks:
                sym_data = dict(map(lambda x: map_data_with_types(x , chunk) , map_fields_with_bytes ))
                symbol_data.append(list(sym_data.values()))
            return (map_type[0]  , symbol_data)
        case  "remove_symbol":
            chunks = get_chunks( data = data[start:] , chunk_size= map_type[3] )
            map_fields_with_bytes = msg_map["remove_symbol"]
            symbol_data = []
            for chunk in chunks:
                sym_data = dict(map(lambda x: map_data_with_types(x , chunk) , map_fields_with_bytes ))
                symbol_data.append( f"{list(sym_data.values())[0]}:{list(sym_data.values())[1]}" )
            return ("symbollist" , symbol_data)
        case _ :
            return (map_type[0], map_type[1] )

def decompress_data(data):
    try:
        uncomp_length = 1024
        decompressed = lz4.block.decompress(data, uncomp_length)
    except lz4.block.LZ4BlockError as e:
        uncomp_length = len(data)*5
        decompressed = lz4.block.decompress(data, uncomp_length)
    msg_code = decompressed[:1].decode('utf-8') 
    map_fields_with_bytes = msg_map[msg_code]
    data = dict(map(lambda x: map_data_with_types(x , decompressed) , map_fields_with_bytes ))
    return (data)
