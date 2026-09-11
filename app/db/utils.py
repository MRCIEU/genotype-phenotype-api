import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial, wraps
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
            logger.bind(execution_time=f"{execution_time:.2f}ms").info(f"{func.__name__} completed")

    return wrapper


# Bounded so we don't let more than a handful of blocking DuckDB queries run in parallel per
# worker process and contend for a DB file's shared memory_limit at once.
_db_executor = ThreadPoolExecutor(max_workers=8)


async def run_sync(func, *args, **kwargs):
    """Run a blocking DB call off the event loop so it can't block other requests (incl. /health)."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_db_executor, partial(func, *args, **kwargs))
