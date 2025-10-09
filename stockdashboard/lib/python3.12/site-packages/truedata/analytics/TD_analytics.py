from .decorators import access_token_decorator
from io import StringIO
from datetime import datetime as dt , timedelta , date
from threading import RLock
from colorama import Style, Fore
from functools import reduce
import logging
import requests
import pandas as pd
import lz4.block
import struct
import base64

class TD_analytics:

    def __init__(self, login_id, password, log_level = logging.WARNING , log_handler = None , log_format = None):  
        
        self.login_id = login_id
        self.password = password
        self.analytics_url = "https://analytics.truedata.in/api/"
        self.greeks_url = "https://greeks.truedata.in/api/"
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
        self.thread_lock = RLock()
        self.access_token = None
        self.access_token_expiry_time = None
        self.available_oi_sort_by = [ "futureswithhighestoi" , "optionswithhighestoi" , "oigainers" , "oilosers",
                                    "oigainerspricegainers" , "oigainerspricelosers" , "oiloserspricegainers" ,
                                    "oiloserspricegainers" ,]
        try:
            self.hist_login()
        except Exception as e:
            self.logger.error(f"Failed to connect REST historical API -> {type(e)} = {e}")

    def get_new_token(self ):
        url_auth = "https://auth.truedata.in/token"
        payload = f"username={self.login_id}&password={self.password}&grant_type=password"
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        token_json = requests.request("POST", url_auth, headers=headers, data=payload).json()
        return token_json

    def hist_login(self):
        token_json = self.get_new_token()
        try:
            if token_json['access_token']:
                self.access_token = token_json['access_token']
                self.access_token_expiry_time = dt.now() + timedelta(seconds=token_json['expires_in'] - 15)  # 15 seconds is random buffer time
                self.logger.warning(f"{Style.NORMAL}{Fore.BLUE}Connected successfully to TrueData Anaytical Data Service... {Style.RESET_ALL}")
        except Exception as e:
            self.logger.error(f"Failed to connect -> {token_json['error_description']}{type(e)} = {e}")
            self.access_token = None

    @staticmethod
    def decompress_data(data):
        uncom_length = struct.unpack('<I', data[:4])[0]
        com_length = struct.unpack('<I', data[4:8])[0]
        dc = lz4.block.decompress( data[8:], uncom_length ) if com_length != uncom_length else data[8:]
        return dc.decode()

    @staticmethod
    def clean_data_to_df( data):   
        df = pd.read_csv(StringIO(data) , dtype='unicode' )
        return df

    @access_token_decorator
    def get_option_chain(self, symbol, expiry, greeks = False):
        try:
            if not isinstance (expiry , date):
                raise TypeError("Expiry must be a type of date") 
            headers = {'Authorization': f'Bearer {self.access_token}'}
            payload = {'symbol' : symbol , "expiry" : expiry.strftime("%d-%m-%Y"), 'comp': 'true'}
            end_point = "getoptionchain" if not greeks else "getoptionchainwithgreeks"
            url = f"{self.analytics_url}{end_point}" if not greeks else f"{self.greeks_url}{end_point}"
            with self.thread_lock:
                response = requests.get( url , headers=headers, params=payload)
                if response.status_code == 429:
                    error = base64.b64decode(response.content).decode('utf-8')
                    raise TooManyRequestsError(error)
                elif not response.status_code == 200:
                    raise response.raise_for_status()
                try:
                    res = TD_analytics.decompress_data(response.content)
                except Exception as decompress_error:
                    self.logger.warning("Decompression failed, treating content as raw text.")
                    res = response.content.decode('utf-8')

                df = self.clean_data_to_df(res)
                return df 
        except Exception as e:
            self.logger.error(f"{type(e)} -> {e}")
            return None

    @access_token_decorator
    def get_oi_gainer_losers(self, top , series , sort_by  ):
        try:
            if not sort_by.lower() in self.available_oi_sort_by: 
                raise TypeError("please provide valid sort_by option from the documentation") 
            headers = {'Authorization': f'Bearer {self.access_token}'}
            payload = {'top' : top , "series" : series }
            end_point = f"get{sort_by.lower()}"
            with self.thread_lock:
                response = requests.get(f"{self.analytics_url}{end_point}", headers=headers, params=payload)
                if response.status_code == 429:
                    error = base64.b64decode(response.content).decode('utf-8')
                    raise TooManyRequestsError(error)
                elif not response.status_code == 200:
                    raise response.raise_for_status()
                df = self.clean_data_to_df(response.text)
                return df 
        except Exception as e:
            self.logger.error(f"{type(e)} -> {e}")
            return None
    
    @access_token_decorator
    def get_index_gainer_losers(self, top  , segment , index_name , sort_by  ):
        try:
            if not sort_by.lower() in ["gainers" , "losers"]: 
                raise TypeError("please provide valid sort_by option from the documentation") 
            headers = {'Authorization': f'Bearer {self.access_token}'}
            payload = {'top' : top , "indexname" : index_name , "segment": segment }
            end_point = f"getindex{sort_by.lower()}"
            with self.thread_lock:
                response = requests.get(f"{self.analytics_url}{end_point}", headers=headers, params=payload)
                if response.status_code == 429:
                    error = base64.b64decode(response.content).decode('utf-8')
                    raise TooManyRequestsError(error)
                elif not response.status_code == 200:
                    raise response.raise_for_status()
                df = self.clean_data_to_df(response.text)
                return df 
        except Exception as e:
            self.logger.error(f"{type(e)} -> {e}")
            return None
    
    @access_token_decorator
    def get_industry_gainer_losers(self, top , segment , industry , sort_by  ):
        try:
            if not sort_by.lower() in ["gainers" , "losers"]: 
                raise TypeError("please provide valid sort_by option from the documentation") 
            headers = {'Authorization': f'Bearer {self.access_token}'}
            payload = {'top' : top , "segment": segment , "industry" : industry }
            end_point = f"getindustry{sort_by.lower()}"
            with self.thread_lock:
                response = requests.get(f"{self.analytics_url}{end_point}", headers=headers, params=payload)
                if response.status_code == 429:
                    error = base64.b64decode(response.content).decode('utf-8')
                    raise TooManyRequestsError(error)
                elif not response.status_code == 200:
                    raise response.raise_for_status()
                df = self.clean_data_to_df(response.text)
                return df 
        except Exception as e:
            self.logger.error(f"{type(e)} -> {e}")
            return None
   
    @access_token_decorator
    def get_history_greeks(self, symbol , expiry , strike , series , ltp = False  ):
        try:
            if not isinstance (expiry , date):
                raise TypeError("Expiry must be a type of date") 
            headers = {'Authorization': f'Bearer {self.access_token}'}
            payload = { 'symbol' : symbol , "expiry": expiry.strftime("%d-%m-%Y") ,
                        "strike" : strike, "series" : series }
            end_point = f"getltpwithgreeks" if ltp else "getTickHistorywithGreeks"
            with self.thread_lock:
                response = requests.get(f"{self.greeks_url}{end_point}", headers=headers, params=payload)
                if response.status_code == 429:
                    error = base64.b64decode(response.content).decode('utf-8')
                    raise TooManyRequestsError(error)
                elif not response.status_code == 200:
                    raise response.raise_for_status()
                df = self.clean_data_to_df(response.text)
                return df 
        except Exception as e:
            self.logger.error(f"{type(e)} -> {e}")
            return None
        
    @access_token_decorator
    def get_bulk_spot_ltp(self, symbols ):
        try:
            headers = {'Authorization': f'Bearer {self.access_token}'}
            symbols = reduce(lambda x, y: x + ',' + y, symbols)
            payload = { 'symbols' : symbols }
            end_point = "getLTPSpotbulk"
            with self.thread_lock:
                response = requests.get(f"{self.analytics_url}{end_point}", headers=headers, params=payload)
                if response.status_code == 429:
                    error = base64.b64decode(response.content).decode('utf-8')
                    raise TooManyRequestsError(error)
                elif not response.status_code == 200:
                    raise response.raise_for_status()
                df = self.clean_data_to_df(response.text)
                return df 
        except Exception as e:
            self.logger.error(f"{type(e)} -> {e}")
            return None
        
    @access_token_decorator
    def get_spot_ltp(self, symbol  ):
        try:
            headers = {'Authorization': f'Bearer {self.access_token}'}
            payload = { 'symbol' : symbol }
            end_point = "getLTPspot"
            with self.thread_lock:
                response = requests.get(f"{self.analytics_url}{end_point}", headers=headers, params=payload)
                if response.status_code == 429:
                    error = base64.b64decode(response.content).decode('utf-8')
                    raise TooManyRequestsError(error)
                elif not response.status_code == 200:
                    raise response.raise_for_status()
                df = self.clean_data_to_df(response.text)
                return df 
        except Exception as e:
            self.logger.error(f"{type(e)} -> {e}")
            return None
    
    @access_token_decorator
    def get_fno_ltp(self, symbol , expiry , strike = 0 , series = 'XX' ):
        try:
            if not isinstance (expiry , date):
                raise TypeError("Expiry must be a type of date") 
            headers = {'Authorization': f'Bearer {self.access_token}'}
            payload = { 'symbol' : symbol , "expiry": expiry.strftime("%d-%m-%Y") ,
                        "strike" : strike, "series" : series }
            end_point = f"getLTP"
            with self.thread_lock:
                response = requests.get(f"{self.analytics_url}{end_point}", headers=headers, params=payload)
                if response.status_code == 429:
                    error = base64.b64decode(response.content).decode('utf-8')
                    raise TooManyRequestsError(error)
                elif not response.status_code == 200:
                    raise response.raise_for_status()
                df = self.clean_data_to_df(response.text)
                return df 
        except Exception as e:
            self.logger.error(f"{type(e)} -> {e}")
            return None    


class TooManyRequestsError(Exception):
    def __init__(self, msg):
        self.msg = msg
    def __str__(self ):
        return self.msg
