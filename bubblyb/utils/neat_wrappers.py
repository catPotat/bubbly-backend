from functools import wraps
'''
def my_logger(orig_func): # for reference
    import logging
    logging.basicConfig(filename='{}.log'.format(orig_func.__name__), level=logging.INFO)
    @wraps(orig_func)
    def wrapper(*args, **kwargs):
        logging.info(
            'Ran with args: {}, and kwargs: {}'.format(args, kwargs))
        return orig_func(*args, **kwargs)
    return wrapper
'''
import time
def perf_timer(orig_func):
    @wraps(orig_func)
    def wrapper(*args, **kwargs):
        t1 = time.time()
        result = orig_func(*args, **kwargs)
        t2 = time.time() - t1
        print('{} ran in: {} sec'.format(orig_func.__name__, t2))
        return result
    return wrapper

from django.db import connection, reset_queries
def count_db_hits(orig_func):
    @wraps(orig_func)
    def wrapper(*args, **kwargs):
        do_queries = orig_func(*args, **kwargs)
        print (f'DB hits: {len(connection.queries)}')
        print ("-----------")
        reset_queries()
        return do_queries
    return wrapper
