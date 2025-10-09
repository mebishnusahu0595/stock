from websocket import WebSocketApp, WebSocketTimeoutException
from threading import Thread
from datetime import datetime
from dateutil.relativedelta import relativedelta            # type: ignore
from copy import deepcopy
from .utils import full_feed , bidask_feed , bar_feed , greek_feed , tick_feed , min_feed, TouchlineData, decompress_data
from colorama import Style, Fore                            # type: ignore
import time
import json
import traceback
import pandas as pd
import os

class LiveClient(WebSocketApp):

    def __init__(self, parent_app, url, *args):
        WebSocketApp.__init__(self, url, on_open=self.ws_open, on_error=self.ws_error, on_message=self.on_msg_func, on_close=self.ws_close, *args)
        self.segments = []
        self.max_symbols = 0
        self.remaining_symbols = 0
        self.valid_until = ''
        self.subscription_type = ''
        self.confirm_heartbeats = 1
        self.store_last_n_heartbeats = self.confirm_heartbeats + 7
        self.heartbeat_interval = 5
        self.heartbeat_buffer = 1
        self.parent_app = parent_app
        self.symbol_id_map = {}
        time_of_creation = datetime.now()
        self.last_n_heartbeat = [time_of_creation - relativedelta(seconds=i * self.heartbeat_interval) for i in range(-self.store_last_n_heartbeats, 0)]
        self.logger = self.parent_app.logger
        self.disconnect_flag = False
        # self.heartbeat_check_thread = Thread(target=self.check_heartbeat, daemon=True)
        self.trade_callback = None
        self.full_feed_trade_callback = None
        self.full_feed_bar_callback = None
        self.bidask_callback = None
        self.one_min_bar_callback = None
        self.five_min_bar_callback = None
        self.greek_callback = None
        self.subs = ''


    def check_connection(self):
        base_heartbeat = self.last_n_heartbeat[-self.confirm_heartbeats]
        check_time = datetime.now()
        time_diff = check_time - base_heartbeat
        is_connected = time_diff.total_seconds() > ((self.heartbeat_interval + self.heartbeat_buffer) * self.confirm_heartbeats)  # 3 > 5 + 0.5
        return is_connected

    def check_heartbeat(self):
        while True:
            time.sleep(self.heartbeat_interval)
            if self.disconnect_flag:
                self.logger.info(f"{Fore.WHITE}Removing hand from the pulse...{Style.RESET_ALL}")
                break
            if self.check_connection():
                self.logger.debug(f"{Style.BRIGHT}{Fore.RED}Failed Heartbeat @ {datetime.now()} because of last at {self.last_n_heartbeat[-self.confirm_heartbeats]}{Style.RESET_ALL}")
                self.logger.info(f"{Style.BRIGHT}{Fore.RED}Attempting reconnect @ {Fore.CYAN}{datetime.now()}{Style.RESET_ALL}")
                restart_successful = self.reconnect()
                if restart_successful:
                    self.logger.info(f"{Style.BRIGHT}{Fore.GREEN}Successful restart @ {Fore.CYAN}{datetime.now()}{Style.RESET_ALL}")
                    time.sleep((self.heartbeat_interval + self.heartbeat_buffer))
                    recover_start, recover_end = self.get_largest_diff(self.last_n_heartbeat)
                    self.recover_from_time_missed(recover_start, recover_end)
                else:
                    self.logger.info(f"{Style.BRIGHT}{Fore.RED}Failed restart @ {Fore.CYAN}{datetime.now()}{Style.RESET_ALL}")

    @staticmethod
    def get_largest_diff(time_series):
        big_li = deepcopy(time_series.pop(0))
        small_li = deepcopy(time_series.pop())
        diffs = [i[0]-i[1] for i in zip(big_li, small_li)]
        start_gap_index = max(range(len(diffs)), key=lambda i: diffs[i])
        return time_series[start_gap_index], time_series[start_gap_index+1]

    def recover_from_time_missed(self, start_time, end_time):
        self.logger.info(f"{Style.BRIGHT}{Fore.YELLOW}Initiating recovery from {Fore.GREEN}{start_time}{Fore.YELLOW} till {Fore.GREEN}{end_time}{Fore.YELLOW} "
                         f"which are last green heartbeats from server...{Style.RESET_ALL}")

    def reconnect(self):
        self.close()
        time.sleep(2)
        t = Thread(target=self.run_forever, daemon=True)
        t.start()
        is_td_connected = False
        while not is_td_connected:
            time.sleep(self.heartbeat_interval + self.heartbeat_buffer)
            is_td_connected = self.check_connection()
        return is_td_connected

    def handle_message_data(self, msg):
        if msg['success']:
            if msg['message'] == 'HeartBeat':
                self.handle_heartbeat(msg['timestamp'])
            elif msg['message'] == 'TrueData Real Time Data Service':  # Connection success message
                self.logger.warning(f"{Style.NORMAL}{Fore.BLUE}Connected successfully to {msg['message']}... {Style.RESET_ALL}")
                self.subscription_type = msg['subscription']
                self.subs = self.subscription_type.split('+')
                # print(self.subscription_type)
            elif msg['message'] in ['symbols added', 'touchline']:
                # print(msg['symbollist'])
                self.update_symbols_data(msg['symbollist'])
            elif msg['message'] == 'symbols removed':
                self.remove_symbols(msg['symbollist'])
            elif msg['message'] == 'marketstatus':
                self.logger.debug(f"Market status message -> {msg['data']}") 
        else:
            self.logger.error(f"{Style.BRIGHT}{Fore.RED}The request encountered an error - {msg['message']}{Style.RESET_ALL}")

    def handle_heartbeat(self, server_timestamp):
        self.logger.debug(f'Server heartbeat received at {server_timestamp}')
        if self.parent_app.compression:
            timestamp = datetime.strptime(server_timestamp, "%Y-%m-%dT%H:%M:%S")
        else:
            timestamp = datetime.strptime(server_timestamp, "%Y-%m-%dT%H:%M:%S.%f")
        self.last_n_heartbeat = self.last_n_heartbeat[1:]
        self.last_n_heartbeat.append(timestamp)

    def remove_symbols(self, symbols):
        for symbol in symbols:
            symb = symbol.split(':')[0]
            self.parent_app.touchline_data.pop(symb, None) 
            self.parent_app.live_data.pop(symb, None) 
            self.parent_app.one_min_live_data.pop(symb, None) 
            self.parent_app.five_min_live_data.pop(symb, None) 

    def update_symbols_data(self, symbols_data):
        for symbol_data in symbols_data:
            symbol = symbol_data[0]
            self.symbol_id_map[symbol_data[1]] = symbol
            self.parent_app.touchline_data[symbol] = TouchlineData(raw_data= symbol_data)
            if 'tick' in self.subs:
                self.parent_app.live_data[symbol] = tick_feed(touchline = self.parent_app.touchline_data[symbol])
            if '1min' in self.subs:
                self.parent_app.one_min_live_data[symbol] = min_feed(touchline = self.parent_app.touchline_data[symbol])
            if '5min' in self.subs:
                self.parent_app.five_min_live_data[symbol] = min_feed(touchline = self.parent_app.touchline_data[symbol])
            self.logger.info(f"Updated touchline data for {symbol} and related live data objects...")

    def update_trade_data(self, trade_tick):
        try:
            symbol = self.symbol_id_map[trade_tick[0]]
            self.parent_app.live_data[symbol].timestamp = datetime.strptime(trade_tick[1], '%Y-%m-%dT%H:%M:%S')
            self.parent_app.live_data[symbol].ltp =  float(trade_tick[2])
            self.parent_app.live_data[symbol].ltq = float(trade_tick[3])
            self.parent_app.live_data[symbol].atp = float(trade_tick[4])
            self.parent_app.live_data[symbol].ttq = float(trade_tick[5])
            self.parent_app.live_data[symbol].day_open = float(trade_tick[6])
            self.parent_app.live_data[symbol].day_high = float(trade_tick[7])
            self.parent_app.live_data[symbol].day_low = float(trade_tick[8])
            self.parent_app.live_data[symbol].prev_day_close = float(trade_tick[9])
            self.parent_app.live_data[symbol].oi = int(trade_tick[10])
            self.parent_app.live_data[symbol].prev_day_oi = int(trade_tick[11])
            self.parent_app.live_data[symbol].turnover = float(trade_tick[12])
            self.parent_app.live_data[symbol].special_tag = str(trade_tick[13])
            self.parent_app.live_data[symbol].tick_seq = int(trade_tick[14])
            if len(trade_tick) > 15:
                self.parent_app.live_data[symbol].best_bid_price = float(trade_tick[15])
                self.parent_app.live_data[symbol].best_bid_qty = int(trade_tick[16])
                self.parent_app.live_data[symbol].best_ask_price = float(trade_tick[17])
                self.parent_app.live_data[symbol].best_ask_qty = int(trade_tick[18])
            return self.parent_app.live_data[symbol]
        except Exception as e:
            self.logger.error(f'{Style.BRIGHT}{Fore.RED}Encountered error with tick feed - {type(e)}{Style.RESET_ALL}')

    def update_bar_data(self, bar_data , bar_type ):
        try:
            symbol = self.symbol_id_map[bar_data[0]]
            obj_to_edit = self.parent_app.one_min_live_data[symbol] if bar_type == '1min' else self.parent_app.five_min_live_data[symbol] 
            obj_to_edit.timestamp = datetime.strptime(bar_data[1], '%Y-%m-%dT%H:%M:%S')
            obj_to_edit.open = float(bar_data[2])
            obj_to_edit.high = bar_high = float(bar_data[3])
            if bar_high > obj_to_edit.day_high:
                obj_to_edit.day_high = bar_high
            obj_to_edit.low = bar_low = float(bar_data[4])
            if bar_low < obj_to_edit.day_low:
                obj_to_edit.day_low = bar_low
            obj_to_edit.close = float(bar_data[5])
            obj_to_edit.volume = float(bar_data[6])
            obj_to_edit.oi = float(bar_data[7])
            if self.one_min_bar_callback and bar_type == '1min' :
                self.execute_callbacks(  obj_to_edit , '1min')  
            elif self.five_min_bar_callback and bar_type == '5min' :
                self.execute_callbacks(  obj_to_edit , '5min' ) 
        except Exception as e:
            self.logger.error(f'{Style.BRIGHT}{Fore.RED}Bar feed encountered - {e}{Style.RESET_ALL}')

    def get_symbol_with_id(self, symbol_id):
        try:
            symbol=self.parent_app.symbol_id_map_dict[str(symbol_id)]
            return symbol
        except KeyError as e:
            self.logger.warning(f"{Style.BRIGHT}{Fore.RED}Symbol id - {e.args[0]} is not availavble in the masters and cannot be mapped.{Style.RESET_ALL}")
            return None

    def handle_fullfeed(self , msg ):
        msg_keys = msg.keys()
        if 'trade' in msg_keys:
            symbol = self.get_symbol_with_id(msg['trade'][0])
            if symbol is None:
                return False
            feed_tick = full_feed( raw_tick=msg['trade'] ,symbol=symbol )
            self.full_feed_trade_callback( feed_tick ) if self.full_feed_trade_callback else None   
        elif ('bidask' in msg_keys or 'bidaskL2' in msg_keys )  :
            if 'bidask' in msg_keys:
                symbol = self.get_symbol_with_id(msg['bidask'][0])
                if symbol is None:
                    return False
                bid_ask = bidask_feed( raw_tick=msg['bidask'] , symbol=symbol , level= "L1" )
            else:
                symbol = self.get_symbol_with_id(msg['bidaskL2'][0])
                if symbol is None:
                    return False
                bid_ask = bidask_feed( raw_tick=msg['bidaskL2'] , symbol=symbol , level= "L2" )
            self.bidask_callback( bid_ask ) if self.bidask_callback else None  
        elif 'greeks' in msg_keys:
            symbol = self.get_symbol_with_id(msg['greeks'][0])
            if symbol is None:
                return False
            greeks = greek_feed( raw_tick=msg['greeks'] , symbol= symbol )
            self.greek_callback(greeks) if self.greek_callback else None
        elif 'interval' in msg_keys  :
            if self.parent_app.change_bar:
                symbol_list  = list(map(lambda x : str(x[1]), msg["data"])) 
                prev_day_data = self.parent_app.symbol_id_map_df.loc[symbol_list]
                prev_day_data[['pclose', 'poi']] = prev_day_data[['pclose', 'poi']].apply(pd.to_numeric)
                prev_day_dict = prev_day_data.to_dict(orient='index')
                bar_data = map(lambda x : bar_feed(x , self.parent_app.symbol_id_map_dict[ str( x[1]) ] ,
                                                    change_bar =self.parent_app.change_bar , prev_day_values= prev_day_dict[str( x[1])] ), msg["data"])
            else:
                bar_data = map(lambda x : bar_feed(x , self.parent_app.symbol_id_map_dict[ str( x[1]) ] ,
                                                    change_bar =self.parent_app.change_bar  ), msg["data"]) 
            for bar in list(bar_data):
                self.full_feed_bar_callback ( bar ) if self.full_feed_bar_callback else None

    def handle_fullfeed_with_compression(self, msg):
        msg_code = msg.pop("msg_code")
        raw_data = list(msg.values())
        symbol = self.get_symbol_with_id(msg['symbol_id'])
        if symbol is None:
            return False
        if msg_code in  ["T" , "W" ]:
            feed_tick = full_feed( raw_tick=raw_data ,symbol=symbol )
            self.full_feed_trade_callback( feed_tick ) if self.full_feed_trade_callback else None   
        elif msg_code == "G":
            greeks = greek_feed( raw_tick= raw_data, symbol= symbol )
            self.greek_callback(greeks) if self.greek_callback else None
        elif msg_code in ["B" , "D"]:
            if  msg_code == "B":
                bid_ask = bidask_feed( raw_tick=raw_data , symbol=symbol , level= "L1" )
            else:
                bid_ask = bidask_feed( raw_tick=raw_data , symbol=symbol , level= "L2" )
            self.bidask_callback( bid_ask ) if self.bidask_callback else None

    def handle_normalfeed_with_compression(self, msg):
        msg_code = msg.pop("msg_code")
        raw_data = list(msg.values())
        symbol = self.symbol_id_map[msg['symbol_id']]
        if msg_code in ["T" , "W"]:
            trade_tick = self.update_trade_data( raw_data )
            self.trade_callback(trade_tick) if self.trade_callback else None
        elif msg_code == "G":
            greeks = greek_feed( raw_tick=raw_data , symbol=symbol)
            self.parent_app.greek_data[greeks.symbol] = greeks
            self.greek_callback(greeks) if self.greek_callback else None
        elif msg_code in ["B" , "D"]:
            if  msg_code == "B":
                bid_ask = bidask_feed( raw_tick=raw_data , symbol=symbol , level = "L1" )
            else:
                bid_ask = bidask_feed( raw_tick=raw_data , symbol=symbol , level = "L2" )
            self.bidask_callback( bid_ask ) if self.bidask_callback else None
        elif msg_code in ["O" , "F"]:
            self.update_bar_data( raw_data , bar_type= '1min' ) if msg_code == "O" else self.update_bar_data( raw_data , bar_type= '5min')


    def handle_normalfeed(self, msg):
        msg_keys = msg.keys()
        if 'trade' in msg_keys:
            trade_tick = self.update_trade_data( msg['trade'] )
            self.trade_callback(trade_tick) if self.trade_callback else None
        elif ('bidask' in msg_keys or 'bidaskL2' in msg_keys ) :
            if 'bidask' in msg_keys:
                bid_ask = bidask_feed( raw_tick=msg['bidask'] , symbol=self.symbol_id_map[msg['bidask'][0]] , level = "L1" )
            else:
                bid_ask = bidask_feed( raw_tick=msg['bidaskL2'] , symbol=self.symbol_id_map[msg['bidaskL2'][0]] , level = "L2" )
            self.bidask_callback( bid_ask ) if self.bidask_callback else None
        elif 'bar1min' in msg_keys:
            self.update_bar_data( msg['bar1min'] , bar_type= '1min' )
        elif 'bar5min' in msg_keys:
            self.update_bar_data( msg['bar5min'] , bar_type= '5min')
        elif 'greeks' in msg_keys:
            greeks = greek_feed( raw_tick=msg['greeks'] , symbol=self.symbol_id_map[msg['greeks'][0]])
            self.parent_app.greek_data[greeks.symbol] = greeks
            self.greek_callback(greeks) if self.greek_callback else None

    def execute_callbacks(self , obj_to_edit , bar_type ):
        try:
            self.one_min_bar_callback( obj_to_edit) if bar_type == '1min' else self.five_min_bar_callback( obj_to_edit)
        except Exception as e:
            self.logger.error(f'{Style.BRIGHT}{Fore.RED}Encountered error with bar_callback - {type(e)} - {e}{Style.RESET_ALL}')

    def ws_error(self, *args):
        error = args[-1]
        if any(isinstance(error, conn_error) for conn_error in [ConnectionResetError, TimeoutError , WebSocketTimeoutException]):
            self.logger.error(f"Raising WS error = {error}")
            self.last_ping_tm = self.last_pong_tm = 0

    def ws_open(self, *args):
        self.last_ping_tm = time.time()
        self.sock.ping()
        self.sock.settimeout(15)
        if self.symbol_id_map:
            self.logger.info("connection dropped due to timeout. trying reconnecting.....")
            self.sock.ping()
            time.sleep(3)
            if not self.parent_app.full_feed:
                restart_symbols = list(self.symbol_id_map.values())
                self.logger.debug(f'{restart_symbols} needs resuming here.')
                self.parent_app.start_live_data(restart_symbols, restart_flag = True )
                self.logger.info(f'All streaming symbols have been resumed.')

    def on_msg_func(self, *args):
        try:
            message = args[-1]
            # print(message)
            msg = decompress_data(message) if self.parent_app.compression else json.loads(message)
            # print(msg) 
            msg_keys = msg.keys()
            if 'message' in msg_keys:
                self.handle_message_data(msg)
            elif self.parent_app.compression and self.parent_app.full_feed:
                self.handle_fullfeed_with_compression(msg)
            elif self.parent_app.full_feed:
                self.handle_fullfeed(msg)
            elif self.parent_app.compression and not self.parent_app.full_feed:
                self.handle_normalfeed_with_compression(msg)
            else:
                self.handle_normalfeed(msg)
        except Exception :
            print("crashed message ",args[-1])
            traceback.print_exc()
            exit()

    def ws_close(self, *args):
        self.sock.close() if self.sock is not None else 0
        self.sock = None
        if not self.disconnect_flag and ((self.last_ping_tm == 0 and self.last_pong_tm == 0) or (self.last_ping_tm > self.last_pong_tm)) :
            self.logger.debug('DISCONNECTED FROM SERVER. RETRYING IN 5 SEC......')
            try:
                time.sleep(5)
                self.run_forever(ping_interval=10, ping_timeout=5)
            except Exception as e:
                self.logger.error(f'{type(e)} in reconnection => {e}')
