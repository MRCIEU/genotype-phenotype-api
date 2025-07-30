from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    STUDIES_DB_PATH: str
    ASSOCIATIONS_DB_PATH: str
    COLOC_PAIRS_DB_PATH: str
    LD_DB_PATH: str
    GWAS_UPLOAD_DB_PATH: str
    SUMMARY_STATS_DIR: str
    REDIS_HOST: str
    REDIS_PORT: int
    DEBUG: bool = False
    GWAS_DIR: str
    DATA_DIR: str
    SENTRY_DSN: str
    EMAIL_FROM: str = "gpmap@opengwas.io"
    EMAIL_SERVER: str = "smtp.email.uk-london-1.oci.oraclecloud.com"
    EMAIL_PORT: int = 587
    EMAIL_TLS: bool = True
    EMAIL_USERNAME: str
    EMAIL_PASSWORD: str
    WEBSITE_URL: str = "https://gpmap.opengwas.io"


    model_config = {
        "env_file": ".env"
    }

@lru_cache()
def get_settings():
    return Settings() 