import json
from hashlib import sha1

from slowapi import Limiter
from starlette.requests import Request

from app.logging_config import get_logger

logger = get_logger("app.rate_limiting")


DEFAULT_RATE_LIMIT = "60/minute"


def rate_limit_identifier(request: Request) -> str:
    """
    Returns a hash of the request headers, which will generally remain the same for a session
    """
    try:
        header_hash = sha1(str(request.headers).encode()).hexdigest()
    except Exception as e:
        logger.error(e)
        raise
    return header_hash


limiter = Limiter(key_func=rate_limit_identifier)
