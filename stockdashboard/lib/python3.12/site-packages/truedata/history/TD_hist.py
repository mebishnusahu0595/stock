from .utils import TDHistoricDataError
from .Historical_REST import HistoricalREST 
from datetime import datetime
from dateutil.relativedelta import relativedelta                                # type: ignore
from typing import List, Dict
import logging


class TD_hist:

    def __init__(   self, login_id, password, log_level=logging.WARNING,
                    log_handler=None, log_format=None, hist_url='https://history.truedata.in' ):
        self.historical_datasource = None
        self.login_id = login_id
        self.password = password
        self.hist_url = hist_url
        self.set_custom_log(log_level , log_handler , log_format)
        self.connect()

    def connect(self):
        self.historical_datasource = HistoricalREST(self.login_id, self.password, self.hist_url, self.logger)
        
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

    @staticmethod
    def truedata_duration_map(regular_format, end_date):
        duration_units = regular_format.split()[1].upper()
        if len(duration_units) > 1:
            raise TDHistoricDataError("Misconfigured duration argument")
        duration_size = int(regular_format.split()[0])
        if duration_units == 'D':
            return (end_date - relativedelta(days=duration_size - 1)).date()
        elif duration_units == 'W':
            return (end_date - relativedelta(weeks=duration_size)).date()
        elif duration_units == 'M':
            return (end_date - relativedelta(months=duration_size)).date()
        elif duration_units == 'Y':
            return (end_date - relativedelta(years=duration_size)).date()

    def get_historic_data(  self, contract, end_time=None, duration=None,
                            start_time=None, bar_size="1 min", bidask=False, delivery=False):
        if delivery and not bar_size.lower() == "eod":
            delivery = False
        if start_time is not None and duration is None:
            return self.get_historical_data_from_start_time(contract=contract, end_time=end_time,
                                                            start_time=start_time, bar_size=bar_size,
                                                            bidask=bidask, delivery = delivery)
        else:
            return self.get_historical_data_from_duration(contract=contract, end_time=end_time,
                                                          duration=duration, bar_size=bar_size,
                                                        bidask=bidask, delivery = delivery)

    def get_n_historical_bars(  self, contract, end_time: datetime = None, 
                                no_of_bars: int = 1, bar_size="1 min", bidask=False):
        if end_time is None:
            end_time = datetime.today()
        end_time = end_time.strftime('%y%m%dT%H:%M:%S')    # This is the request format
        hist_data = self.historical_datasource.get_n_historic_bars(contract, end_time, no_of_bars,
                                                                   bar_size, bidask=bidask)
        return hist_data

    def get_historical_data_from_duration(  self, contract, delivery, end_time: datetime = None, duration=None,
                                            bar_size="1 min", bidask=False ):
        if duration is None:
            duration = "1 D"
        if end_time is None:
            end_time = datetime.today()
        start_time = self.truedata_duration_map(duration, end_time)
        end_time = end_time.strftime('%y%m%d') + 'T23:59:59'    # This is the request format
        start_time = start_time.strftime('%y%m%d') + 'T00:00:00'    # This is the request format
        hist_data = self.historical_datasource.get_historic_data(   contract, end_time, start_time, bar_size, 
                                                                    bidask=bidask ,delivery = delivery )
        return hist_data

    def get_historical_data_from_start_time(self, contract,delivery, end_time: datetime = None,
                                            start_time: datetime = None, bar_size="1 min", bidask=False):
        if end_time is None:
            end_time = datetime.today().replace(hour=23, minute=59, second=59)
        if start_time is None:
            start_time = datetime.today().replace(hour=0, minute=0, second=0)
        end_time = end_time.strftime('%y%m%dT%H:%M:%S')    # This is the request format
        start_time = start_time.strftime('%y%m%dT%H:%M:%S')    # This is the request format
        hist_data = self.historical_datasource.get_historic_data(   contract, end_time, start_time, bar_size, 
                                                                    bidask=bidask , delivery = delivery )
        return hist_data

    def get_bhavcopy(self, segment: str, date: datetime = None) -> List[Dict]:
        if date is None:
            date = datetime.now().replace(hour=0, minute=0, second=0)
        return self.historical_datasource.bhavcopy(segment, date)

    def get_gainers(self , segment , topn , df_style = True ):
        topn = 10 if topn is None else topn
        return self.historical_datasource.get_gainers_losers(segment, topn , gainers = True  )

    def get_losers(self , segment , topn , df_style = True ):
        topn = 10 if topn is None else topn
        return self.historical_datasource.get_gainers_losers(segment , topn , gainers = False  )