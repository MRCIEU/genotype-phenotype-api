from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    DB_STUDIES_PATH: str
    DB_ASSOCIATIONS_PATH: str
    REDIS_HOST: str
    REDIS_PORT: int
    DEBUG: bool = False
    ANALYTICS_KEY: str
    LOCAL_DB_DIR: str

    model_config = {"env_file": ".env"}

@lru_cache()
def get_settings():
    return Settings() 