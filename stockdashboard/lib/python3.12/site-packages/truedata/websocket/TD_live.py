from .TD_ws import LiveClient
from .TD_chain import OptionChain
from .utils import remove_all_cache , cache_symbol_id , get_atm
from threading import Thread
from typing import Callable
from datetime import datetime
from colorama import Style, Fore                                                # type: ignore
import time
import json
import logging
import traceback

class TD_live:
    def __init__(self, login_id, password, url='push.truedata.in', live_port=8084, log_level=logging.WARNING,
                 log_handler=None, log_format=None, full_feed = False, dry_run = False , change_bar = False , compression = False ):
        self.login_id = login_id
        self.password = password
        self.live_url = url
        self.live_port = live_port
        self.full_feed = full_feed
        self.dry_run = dry_run
        self.change_bar = change_bar
        self.compression = compression
        self.live_websocket = None
        self.set_custom_log(log_level , log_handler , log_format)
        if live_port is None:
            self.connect_live = False
        else:
            self.connect_live = True
        self.live_data = {}
        self.one_min_live_data = {}
        self.five_min_live_data = {}
        self.touchline_data = {}
        self.greek_data = {}
        self.connect()

    def set_custom_log(self , log_level , log_handler , log_format ):
        if log_format is None:
            log_format = "(%(asctime)s) %(levelname)s :: %(message)s (PID:%(process)d Thread:%(thread)d)"
        if log_handler is None:
            log_formatter = logging.Formatter(log_format)
            self.log_handler = logging.StreamHandler()
            self.log_handler.setLevel(log_level)
            self.log_handler.setFormatter(log_formatter)
        else:
            self.log_handler = log_handler
        self.logger = logging.getLogger(__name__)
        self.logger.addHandler(self.log_handler)
        self.logger.setLevel(self.log_handler.level)
        self.logger.debug("Logger ready...")
  
    def connect_websocket(self):
        self.t.start()
        while self.connect_live and self.live_websocket.subscription_type == '':
            time.sleep(1)

    def connect(self):
        broker_append = ''
        if self.dry_run:
            remove_all_cache()
        self.symbol_id_map_dict , self.symbol_id_map_df = cache_symbol_id(self.login_id , self.password  , self ) if self.full_feed else (0,0)
        if self.connect_live:
            self.live_websocket = LiveClient(self, f"wss://{self.live_url}:{self.live_port}?user={self.login_id}&password={self.password}{broker_append}" )
            self.t = Thread(target=self.connect_thread, args=(), daemon=True)
            if self.full_feed:
                return#
        self.connect_websocket()
        

    def connect_thread(self):
        self.live_websocket.run_forever(ping_interval=10, ping_timeout=5)
        while not self.live_websocket.disconnect_flag:
            self.logger.info(f"{Style.BRIGHT}{Fore.RED}Connection dropped due to no network , Attempting reconnect @ {Fore.CYAN}{datetime.now()}{Style.RESET_ALL}")
            self.live_websocket.reconnect()
            time.sleep(10)
        self.logger.debug('Goodbye (properly) !!')

    def disconnect(self):
        if self.connect_live:
            self.live_websocket.disconnect_flag = True
            self.live_websocket.close()
            self.logger.warning(f"{Style.NORMAL}{Fore.BLUE}Disconnected from Real Time Data WebSocket Connection !{Style.RESET_ALL}")

    def start_live_data(self, symbols , restart_flag = False):  # TODO: Prevent reuse of req_ids
        if restart_flag:
            self.live_websocket.send(json.dumps({"method": "addsymbol", "symbols": symbols}))
            return True
        symbols_to_call = []
        symbols = list(set(symbols))
        for symbol in symbols:
            symbol = symbol.upper()
            symbols_to_call.append(symbol)
        if len(symbols_to_call) > 0:
            self.live_websocket.send(json.dumps({"method": "addsymbol", "symbols": symbols_to_call}))
        return True
        
    def stop_live_data(self, symbols):  
        self.live_websocket.send(json.dumps({"method": "removesymbol", "symbols": symbols}))

    def trade_callback(self, func: Callable):
        self.logger.info(f"Defining {func} as trade_callback...")
        self.live_websocket.trade_callback = func

    def clear_trade_callback(self):
        self.logger.info(f"Clearing trade_callback...")
        self.live_websocket.trade_callback = None

    def bidask_callback(self, func: Callable):
        self.logger.info(f"Defining bidask_callback...")
        self.live_websocket.bidask_callback = func

    def clear_bidask_callback(self):
        self.logger.info(f"Clearing bidask_callback...")
        self.live_websocket.bidask_callback = None

    def one_min_bar_callback(self, func: Callable):
        self.logger.info(f"Defining one min bar_callback...")
        self.live_websocket.one_min_bar_callback = func

    def clear_one_min_bar_callback(self):
        self.logger.info(f"Clearing one min bar_callback...")
        self.live_websocket.one_min_bar_callback = None

    def five_min_bar_callback(self, func: Callable) :
        self.logger.info(f"Defining five min bar_callback...")
        self.live_websocket.five_min_bar_callback = func

    def clear_five_min_bar_callback(self):
        self.logger.info(f"Clearing five min bar_callback...")
        self.live_websocket.five_min_bar_callback = None

    def full_feed_trade_callback(self , func: Callable ):
        self.logger.info(f"Defining full feed tick_callback...")
        self.live_websocket.full_feed_trade_callback = func

    def clear_full_feed_trade_callback(self):
        self.logger.info(f"Clearing full feed trade_callback...")
        self.live_websocket.full_feed_trade_callback = None
    
    def full_feed_bar_callback(self , func: Callable ):
        self.logger.info(f"Defining full feed bar_callback...")
        self.live_websocket.full_feed_bar_callback = func

    def clear_full_feed_bar_callback(self):
        self.logger.info(f"Clearing full feed bar_callback...")
        self.live_websocket.full_feed_bar_callback = None

    def greek_callback(self , func: Callable ):
        self.logger.info(f"Defining greek feed callback...")
        self.live_websocket.greek_callback = func

    def clear_greek_callback(self):
        self.logger.info(f"Clearing greek feed callback...")
        self.live_websocket.greek_callback = None

    # def get_touchline(self):
    #     self.live_websocket.send(json.dumps({"method": "touchline"}))

    def start_option_chain( self , symbol , expiry , chain_length = None , bid_ask = False , greek = False ):
        chain_length = 10 if chain_length is None else chain_length  # setting default value for chain length
        try:
            atm , strike_step  = get_atm(self.login_id , self.password , symbol , expiry  )
            chain = OptionChain(self , symbol, expiry , chain_length , atm , strike_step , bid_ask , self.live_websocket.subscription_type , greek )
        except Exception as e:
            self.logger.warning(f'Please check symbol: {symbol} and its expiry: {expiry.date()}')
            exit()
        self.start_live_data(chain.option_symbols)
        time.sleep(2)
        option_thread = Thread(target=chain.update_chain, args=( ), daemon=True)
        option_thread.start()
        return chain
