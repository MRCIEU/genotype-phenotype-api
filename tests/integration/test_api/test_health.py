from datetime import UTC, datetime, timedelta
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
    system("git checkout tests/test_data/gwas_upload_small.db")
    recent = (datetime.now(UTC) - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
    conn = duckdb.connect(get_settings().GWAS_UPLOAD_DB_PATH)
    conn.executemany(
        """
        INSERT INTO gwas_upload (
            guid, email, name, sample_size, ancestry, category, is_published, status, failure_reason, created_at, updated_at
        ) VALUES (?, 'a@b.com', 'study', 100, 'EUR', 'continuous', false, ?, ?, ?, ?)
        """,
        [
            ("health-completed-1", "completed", None, "2026-01-01 00:00:00", "2026-01-01 01:00:00"),
            ("health-completed-2", "completed", None, "2026-01-01 00:00:00", "2026-01-01 01:00:00"),
            ("health-failed-1", "failed", "Validation error: missing columns", "2026-01-01 00:00:00", "2026-01-01 01:00:00"),
            ("health-failed-2", "failed", None, "2026-01-01 00:00:00", "2026-01-01 01:00:00"),
            ("health-failed-3", "failed", "Caught error: invalid file format", "2026-01-01 00:00:00", "2026-01-01 01:00:00"),
            ("health-failed-4", "failed", "Caught error during parsing", "2026-01-01 00:00:00", "2026-01-01 01:00:00"),
            ("health-processing-1", "processing", None, recent, None),
            ("health-processing-2", "processing", None, recent, None),
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
    assert data["processing_uploads"] == 2
    assert data["oldest_unprocessed_guid"] in {"health-processing-1", "health-processing-2"}
    assert data["oldest_unprocessed_age_seconds"] is not None
    assert data["oldest_unprocessed_age_seconds"] < 24 * 60 * 60
    assert set(data["processing_guids"]) == {"health-processing-1", "health-processing-2"}
    assert data["redis_queue_size"] == 0
    assert data["redis_in_progress_size"] == 0
    assert data["redis_dlq_size"] == 0
    assert data["redis_queue_guids"] == []
    assert data["redis_in_progress_guids"] == []
    assert set(data["processing_not_in_redis"]) == {"health-processing-1", "health-processing-2"}
    assert data["redis_not_in_db_processing"] == []


def test_upload_health_returns_503_when_processing_stuck_over_24h():
    system("git checkout tests/test_data/gwas_upload_small.db")
    stuck_since = (datetime.now(UTC) - timedelta(hours=25)).strftime("%Y-%m-%d %H:%M:%S")
    conn = duckdb.connect(get_settings().GWAS_UPLOAD_DB_PATH)
    conn.execute(
        """
        INSERT INTO gwas_upload (
            guid, email, name, sample_size, ancestry, category, is_published, status, failure_reason, created_at, updated_at
        ) VALUES (?, 'a@b.com', 'study', 100, 'EUR', 'continuous', false, 'processing', NULL, ?, NULL)
        """,
        ["health-stuck-1", stuck_since],
    )
    conn.close()

    response = client.get("/upload-health")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "unhealthy"
    assert data["oldest_unprocessed_guid"] == "health-stuck-1"
    assert data["oldest_unprocessed_age_seconds"] > 24 * 60 * 60
    assert "unhealthy_reason" in data
    assert "health-stuck-1" in data["unhealthy_reason"]
    assert ">24h" in data["unhealthy_reason"]
