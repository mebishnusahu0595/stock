from datetime import datetime as dt
from functools import wraps


def access_token_decorator(func):
    @wraps(func)
    def dec_helper(obj, *args, **kwargs):
        if obj.access_token_expiry_time < dt.now():
            obj.hist_login()
        return func(obj, *args, **kwargs)
    return dec_helper