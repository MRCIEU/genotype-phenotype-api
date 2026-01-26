from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    STUDIES_DB_PATH: str
    ASSOCIATIONS_DB_PATH: str
    ASSOCIATIONS_FULL_DB_PATH: str
    COLOC_PAIRS_DB_PATH: str
    LD_DB_PATH: str
    GWAS_UPLOAD_DB_PATH: str
    REDIS_HOST: str
    REDIS_PORT: int
    DEBUG: bool = False
    LOGS_DIR: str
    GWAS_DIR: str
    SENTRY_DSN: str
    EMAIL_FROM: str = "gpmap@opengwas.io"
    EMAIL_SERVER: str = "smtp.email.uk-london-1.oci.oraclecloud.com"
    EMAIL_PORT: int = 587
    EMAIL_TLS: bool = True
    EMAIL_USERNAME: str
    EMAIL_PASSWORD: str
    WEBSITE_URL: str = "https://gpmap.opengwas.io"
    VERSION: str = "1.0.0"
    GA4_MEASUREMENT_ID: str = ""
    GA4_API_SECRET: str = ""
    OCI_BUCKET_NAME: str = ""
    OCI_NAMESPACE: str = ""

    model_config = {"env_file": ".env"}


@lru_cache()
def get_settings():
    return Settings()
