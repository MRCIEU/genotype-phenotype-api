from functools import wraps
import time
from loguru import logger


def log_performance(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            end_time = time.time()
            execution_time = (end_time - start_time) * 1000
            logger.bind(execution_time=f"{execution_time:.2f}ms").debug(f"{func.__name__} completed")

    return wrapper
