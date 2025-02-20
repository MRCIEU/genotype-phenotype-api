import pytest
import duckdb

from app.config import Settings

@pytest.fixture(scope="session")
def test_settings():
    return Settings(
        DB_STUDIES_PATH="tests/test_data/test_studies.db",
        DB_ASSOCIATIONS_PATH="tests/test_data/test_assocs.db",
        REDIS_HOST="localhost",
        REDIS_PORT=6379,
        DEBUG=True
    )

@pytest.fixture(scope="session")
def test_db(test_settings):
    conn = duckdb.connect(test_settings.DB_STUDIES_PATH)
    conn = duckdb.connect(test_settings.DB_ASSOCIATIONS_PATH)
    yield conn
    conn.close()
