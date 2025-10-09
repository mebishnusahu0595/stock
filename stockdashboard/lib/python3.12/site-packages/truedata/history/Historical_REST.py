from .utils import historical_decorator, access_token_decorator, check_response
from io import StringIO
from datetime import datetime, timedelta
from datetime import datetime as dt
from logging import Logger
from threading import RLock
from colorama import Style, Fore
from typing import List, Dict
import os
import requests
import pandas as pd
import lz4.block 
import struct

class HistoricalREST:

    def __init__(self, login_id: str, password: str, url: str, logger: Logger):  # NO PORT, broker token needed from now on
        self.login_id = login_id
        self.password = password
        self.url = url
        self.logger = logger
        self.thread_lock = RLock()
        self.access_token = None
        self.bhavcopy_last_completed = None
        self.access_token_expiry_time = None
        try:
            self.hist_login()
        except Exception as e:
            self.logger.error(f"Failed to connect REST historical API -> {type(e)} = {e}")

    def get_new_token(self ):
        url_auth = "https://auth.truedata.in/token"
        payload = f"username={self.login_id}&password={self.password}&grant_type=password"
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        token_json = requests.request("POST", url_auth, headers=headers, data=payload).json()
        return token_json

    def hist_login(self):
        token_json = self.get_new_token()
        try:
            if token_json['access_token']:
                self.access_token = token_json['access_token']
                self.access_token_expiry_time = datetime.now() + timedelta(seconds=token_json['expires_in'] - 15)  # 15 seconds is random buffer time
                self.logger.warning(f"{Style.NORMAL}{Fore.BLUE}Connected successfully to TrueData Historical Data Service... {Style.RESET_ALL}")
        except Exception as e:
            self.logger.error(f"Failed to connect -> {token_json['error_description']}{type(e)} = {e}")
            self.access_token = None

    # noinspection PyUnusedLocal
    @access_token_decorator
    @historical_decorator
    def get_n_historic_bars(self, contract, end_time, no_of_bars, bar_size, bidask=False):
        end_point = 'getlastnbars'
        try:
            headers = {'Authorization': f'Bearer {self.access_token}'}
            encoded_payload = { 'symbol': contract, 'interval': bar_size, 'response': 'csv', 'bidask': 0 ,'comp': 'true',}
            if bar_size == 'tick':
                encoded_payload['nticks'] = no_of_bars
                end_point = 'getlastnticks'
                if bidask:
                    encoded_payload['bidask'] = 1
            else:  # Not ticks
                encoded_payload['nbars'] = no_of_bars
            with self.thread_lock:
                url = f"{self.url}/{end_point}"
                response = requests.get(url, headers=headers, params=encoded_payload)
                check_response(response)
                hist_data = HistoricalREST.decompress_data(response.content)
                hist_data = self.parse_data(hist_data)
        except Exception as e:
            self.logger.error(f"{type(e)} -> {e}")
            return None
        return hist_data 
    
    @access_token_decorator
    @historical_decorator
    def get_historic_data(self, contract, end_time, start_time, bar_size, delivery = False , bidask=False ):
        end_point = 'getbars'
        try:
            encoded_payload = {'symbol': contract,'interval': bar_size,'response': 'csv','comp': 'true',}
            encoded_payload.update({'delivery' : 'true'}) if delivery and bar_size =="eod" else 0
            unencoded_payload = [f"from={start_time}", f"to={end_time}"]
            unencoded_payload = "&".join(unencoded_payload)
            if bar_size == 'tick':
                encoded_payload['bidask'] = 0
                end_point = 'getticks'
                if bidask:
                    encoded_payload['bidask'] = 1
            headers = { 'Authorization': f'Bearer {self.access_token}'}
            with self.thread_lock:
                url = f"{self.url}/{end_point}?{unencoded_payload}"
                response = requests.get(url, headers=headers, params=encoded_payload)
                check_response(response)
                hist_data = HistoricalREST.decompress_data(response.content)
                hist_data = self.parse_data(hist_data)
        except Exception as e:
            self.logger.error(f"{type(e)} -> {e}")
            return None
        return hist_data

    def get_gainers_losers(self , segment, topn , gainers  ):
        source_string = "gettopngainers" if gainers else "gettopnlosers"
        headers = {'Authorization': f'Bearer {self.access_token}'}
        payload = {'segment': segment , 'topn': topn , 'response':'csv' }
        url = f"{self.url}/{source_string}?"
        try:
            with self.thread_lock:
                response = requests.get(url, headers=headers , params=payload )
                check_response(response)
                data = response.text
            data = self.parse_data(data)
        except Exception as e:
            self.logger.error(f"{type(e)} -> No match found for this segment {segment}")
            return None
        return data

    def parse_data(self, data):
        df = pd.read_csv(StringIO(data) , index_col = None)
        df.timestamp = pd.to_datetime(df.timestamp)
        return df

    def bhavcopy_status(self, segment: str):
        url = f'{self.url}/getbhavcopystatus?segment={segment}&response=csv'
        headers = {'Authorization': f'Bearer {self.access_token}'}
        response = requests.request("GET", url, headers=headers)
        status = response.text.strip().split('\r\n')[-1].split(',')
        assert segment == status[0]
        self.bhavcopy_last_completed = datetime.strptime(status[1], "%Y-%m-%dT%H:%M:%S")

    @access_token_decorator
    def bhavcopy(self, segment: str, date: datetime) -> List[Dict]:
        try:
            self.bhavcopy_status(segment)
            if date > self.bhavcopy_last_completed:
                self.logger.error(f"{Style.BRIGHT}{Fore.RED}No complete bhavcopy found for requested date."
                                    f" Last available for {self.bhavcopy_last_completed.strftime('%Y-%m-%d %H:%M:%S')}.{Style.RESET_ALL}")
                return []
            url_bhavcopy = f"{self.url}/getbhavcopy?segment={segment}&date={date.strftime('%Y-%m-%d')}&response=csv"
            payload = { 'comp' : 'true' }
            headers = {'Authorization': f'Bearer {self.access_token}'}
            response = requests.request( "GET", url_bhavcopy, headers=headers, params=payload )
            check_response(response)
            response = HistoricalREST.decompress_data( response.content )
            data = self.parse_data(response)
            return data 
        except Exception as e:
            self.logger.error(f"{type(e)} -> {e}")

    @staticmethod
    def decompress_data(data):
        uncom_length = struct.unpack('<I', data[:4])[0]
        com_length = struct.unpack('<I', data[4:8])[0]
        dc = lz4.block.decompress( data[8:], uncom_length ) if com_length != uncom_length else data[8:]
        return dc.decode()
