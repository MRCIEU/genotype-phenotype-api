from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    STUDIES_DB_PATH: str
    ASSOCIATIONS_DB_PATH: str
    LD_DB_PATH: str
    GWAS_UPLOAD_DB_PATH: str
    REDIS_HOST: str
    REDIS_PORT: int
    DEBUG: bool = False
    GWAS_DIR: str
    DATA_DIR: str
    SENTRY_DSN: str

    model_config = {
        "env_file": ".env"
    }

@lru_cache()
def get_settings():
    return Settings() 