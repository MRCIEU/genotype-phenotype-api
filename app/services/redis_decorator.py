from pydantic import BaseModel
from typing import Callable
from functools import wraps
import json
import hashlib
from app.logging_config import get_logger
from app.db.redis import RedisClient

logger = get_logger(__name__)


def redis_cache(expire: int = 0, prefix: str = "db_cache", model_class: BaseModel = None):
    """
    Redis caching decorator for database methods.

    Args:
        expire: Cache expiration time in seconds (default: 0 = never expire)
        prefix: Key prefix for Redis cache keys
        model_class: Pydantic model class to cache
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            redis_client = RedisClient()
            cache_key = f"{prefix}:{func.__name__}"
            if args or kwargs:
                args_str = json.dumps([str(arg) for arg in args], sort_keys=True)
                kwargs_str = json.dumps(kwargs, sort_keys=True)
                key_hash = hashlib.md5(f"{args_str}:{kwargs_str}".encode()).hexdigest()[:8]
                cache_key = f"{cache_key}:{key_hash}"

            try:
                cached_data = redis_client.get_cached_data(cache_key)
                if cached_data is not None:
                    logger.debug(f"Cache hit for {cache_key}")
                    if model_class is not None:
                        return model_class.model_validate(cached_data)
                    else:
                        return cached_data
            except Exception as e:
                logger.warning(f"Redis cache get failed for {cache_key}: {e}")

            try:
                result = func(self, *args, **kwargs)
                if model_class is not None:
                    cached_data = result.model_dump_json()
                else:
                    cached_data = json.dumps(result)

                redis_client.set_cached_data(cache_key, cached_data, expire)
                logger.debug(f"Set cached for {cache_key}")
                return result
            except Exception as e:
                logger.error(f"Function execution failed for {cache_key}: {e}")
                raise

        return wrapper

    return decorator
