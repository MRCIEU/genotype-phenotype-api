import logging
import sys
from pathlib import Path
from loguru import logger
from app.config import get_settings

settings = get_settings()

# Create logs directory if it doesn't exist
log_dir = Path(settings.DATA_DIR, "logs")
log_dir.mkdir(exist_ok=True, parents=True)

class Formatter:
    def __init__(self):
        self.padding = 0
        self.fmt = {
            "level": {"color": True, "repr": True},
            "time": {"fmt": "%Y-%m-%d %H:%M:%S.%f"},
            "name": {"padding": 25},
            "function": {"padding": 15},
            "message": {},
        }

    def format(self, record):
        return "<green>{time}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>\n"



def path_filter(record):
    try:
        exclude_paths = ["/health", "/favicon.ico"]
        return not any(path in record["message"] for path in exclude_paths)
    except:
        return True

# Remove default handlers
logger.remove()

# Add console handler with filter
logger.add(
    sys.stderr,
    format=Formatter().format,
    filter=path_filter,
    level="DEBUG" if settings.DEBUG else "INFO",
    backtrace=True,
    diagnose=True
)

if not settings.DEBUG:
    # Add file handler with same filter
    logger.add(
        str(log_dir / "app.log"),
        format=Formatter().format,
        filter=path_filter,
        rotation="10 MB",
        retention="1 week",
        level="WARNING",
        backtrace=True,
        diagnose=True
    )

# Intercept standard library logging
class InterceptHandler(logging.Handler):
    def emit(self, record):
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )

# Configure standard library logging to use our handler
logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

# Replace uvicorn and other libraries' logging
for name in logging.root.manager.loggerDict.keys():
    logging.getLogger(name).handlers = []
    logging.getLogger(name).propagate = True

# Get logger instance
def get_logger(name):
    return logger.bind(name=name) 