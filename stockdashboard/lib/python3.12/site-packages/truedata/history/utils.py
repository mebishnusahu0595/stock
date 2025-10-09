from colorama import Style, Fore         # type: ignore
from functools import wraps
from datetime import datetime
import base64

class TDHistoricDataError(Exception):
    def __str__(self):
        return f"{Style.BRIGHT}{Fore.RED}Something's wrong with the historical data- {self.args[0]}{Style.RESET_ALL}"

class TooManyRequestsError(Exception):
    def __init__(self, msg):
        self.msg = msg
    def __str__(self ):
        return self.msg

class NotFoundError(Exception):
    def __init__(self, msg):
        self.msg = msg
    def __str__(self ):
        return self.msg

def historical_decorator(func):
    @wraps(func)
    def dec_helper(obj, contract, end_time, start_time, bar_size, delivery = False, bidask=False):
        if bar_size.lower() == 'tick' or bar_size.lower() == 'ticks':
            bar_size = 'tick'            
        elif bar_size.lower() == 'eod' or bar_size.lower() == 'week' or bar_size.lower() == 'month':
            bar_size = bar_size.lower()
        else:
            bar_size = bar_size.replace(' ', '')
            if bar_size[-1] == 's':
                bar_size = bar_size[:-1]
        if delivery:
            return func(obj, contract, end_time, start_time, bar_size, delivery, bidask)
        return func(obj, contract, end_time, start_time, bar_size, bidask = bidask)
    return dec_helper


def access_token_decorator(func):
    @wraps(func)
    def dec_helper(obj, *args, **kwargs):
        if obj.access_token_expiry_time < datetime.now():
            obj.hist_login()
        return func(obj, *args, **kwargs)
    return dec_helper


def check_response(response):
    if response.status_code == 429:
        error = base64.b64decode(response.content).decode('utf-8')
        raise TooManyRequestsError(error)
    elif response.status_code == 404:
        error = response.text
        raise NotFoundError(error)
    elif response.status_code == 200:
        return None
    else:
        error = response.text
        raise Exception(error)