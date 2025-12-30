import logging
import sys
import time
from pathlib import Path
from loguru import logger
from app.config import get_settings
from functools import wraps

settings = get_settings()

log_dir = Path(settings.LOGS_DIR, "logs")
log_dir.mkdir(exist_ok=True, parents=True)


def time_endpoint(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            end_time = time.time()
            execution_time = (end_time - start_time) * 1000  # Convert to milliseconds
            # TODO I can't figure out how to get the execution time into the log (using bind or opt), so just logging it here for now
            logger.info(f"{func.__name__} completed {execution_time:.2f}ms")

    return wrapper


class Formatter:
    def __init__(self):
        self.padding = 0
        self.fmt = {
            "level": {"color": True, "repr": True},
            "time": {"fmt": "%Y-%m-%d %H:%M:%S.%f"},
            "elapsed": {"fmt": "%Y-%m-%d %H:%M:%S.%f"},
            "name": {"padding": 25},
            "function": {"padding": 15},
            "message": {},
            "extra": {"execution_time": {"color": "yellow", "repr": True}},
        }

    def format(self, record):
        execution_time = record.get("extra", {}).get("execution_time", "")
        execution_time_str = f" | <yellow>{execution_time}</yellow>" if execution_time else ""
        return f"<green>{{time}}</green> {{elapsed}} | <level>{{level: <8}}</level> | <cyan>{{name}}</cyan>:<cyan>{{function}}</cyan>:<cyan>{{line}}</cyan> - <level>{{message}}</level>{execution_time_str}\n"


def path_filter(record):
    try:
        exclude_paths = ["/health", "/favicon.ico"]
        return not any(path in record["message"] for path in exclude_paths)
    except Exception:
        return True


def is_running_tests():
    return "pytest" in sys.modules


# Remove default handlers
logger.remove()

if not is_running_tests():
    logger.add(
        sys.stderr,
        format=Formatter().format,
        filter=path_filter,
        level="DEBUG" if settings.DEBUG else "INFO",
        backtrace=True,
        diagnose=True,
        serialize=False,
    )

if not settings.DEBUG:
    logger.add(
        str(log_dir / "fastapi.log"),
        format=Formatter().format,
        filter=path_filter,
        rotation="10 MB",
        retention="1 month",
        level="INFO",
        backtrace=True,
        diagnose=True,
        serialize=False,
    )


class InterceptHandler(logging.Handler):
    def emit(self, record):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


# Configure standard library logging to use our handler
logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

# Replace uvicorn and other libraries' logging
for name in logging.root.manager.loggerDict.keys():
    logging.getLogger(name).handlers = []
    logging.getLogger(name).propagate = True

# Silence noisy HTTP client logs (e.g., httpx) at INFO level
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name):
    return logger.bind(name=name)
