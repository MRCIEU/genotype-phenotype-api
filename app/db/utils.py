import asyncio
import contextvars
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
    """Run a blocking DB call off the event loop so it can't block other requests (incl. /health).

    Copies the calling task's contextvars (e.g. Sentry's current request scope) into the
    executor call, the same way asyncio.to_thread does. Without this, the pool's worker
    threads pin whatever scope was active when each thread was first spawned (Sentry's
    ThreadingIntegration snapshots it once, at Thread.start time) and every later job on
    that thread reports the wrong request.
    """
    loop = asyncio.get_running_loop()
    ctx = contextvars.copy_context()
    return await loop.run_in_executor(_db_executor, ctx.run, partial(func, *args, **kwargs))
