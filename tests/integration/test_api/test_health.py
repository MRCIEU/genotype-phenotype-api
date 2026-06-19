from os import system

import duckdb
import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def reset_gwas_upload_db():
    yield
    system("git checkout tests/test_data/gwas_upload_small.db")


def test_upload_health_includes_upload_status_counts():
    conn = duckdb.connect(get_settings().GWAS_UPLOAD_DB_PATH)
    conn.executemany(
        """
        INSERT INTO gwas_upload (
            guid, email, name, sample_size, ancestry, category, is_published, status, failure_reason
        ) VALUES (?, 'a@b.com', 'study', 100, 'EUR', 'continuous', false, ?, ?)
        """,
        [
            ("health-completed-1", "completed", None),
            ("health-completed-2", "completed", None),
            ("health-failed-1", "failed", "Validation error: missing columns"),
            ("health-failed-2", "failed", None),
            ("health-failed-3", "failed", "Caught error: invalid file format"),
            ("health-failed-4", "failed", "Caught error during parsing"),
            ("health-processing-1", "processing", None),
        ],
    )
    conn.close()

    response = client.get("/upload-health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["completed_uploads"] == 2
    assert data["failed_uploads"] == 2
    assert data["failed_caught_error_uploads"] == 2
    assert "queue_size" not in data
