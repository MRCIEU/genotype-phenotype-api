import json
import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


@pytest.fixture
def mock_redis_client():
    """Create a mock RedisClient with mocked Redis instance."""
    mock_redis = Mock()
    mock_redis.lrange.return_value = []
    mock_redis.delete.return_value = 1
    mock_redis.rpush.return_value = 1
    mock_redis.lpush.return_value = 1
    mock_redis.llen.return_value = 5

    with patch("app.db.redis.Redis", return_value=mock_redis):
        from app.db.redis import RedisClient

        redis_client = RedisClient()
        redis_client.redis = mock_redis
        return redis_client


def test_clear_cache(mock_redis_cache):
    response = client.post("v1/internal/clear-cache/all")
    assert response.status_code == 200

    assert response.json() == {"message": "All caches cleared"}


def test_clear_cache_studies(mock_redis_cache):
    response = client.post("v1/internal/clear-cache/studies")
    assert response.status_code == 200

    assert response.json() == {"message": "Studies cache cleared"}


def test_retry_gwas_dlq_by_guid_success(mock_redis_client):
    """Test successfully retrying a specific GUID from DLQ."""
    guid = "test-guid-123"
    dlq_message = {
        "original_message": {"file_location": "/path/to/file.tsv.gz", "metadata": {"guid": guid}},
        "error": "Processing failed",
        "timestamp": "2024-01-01T00:00:00Z",
    }

    mock_redis_client.redis.lrange.return_value = [json.dumps(dlq_message)]

    with patch("app.api.v1.endpoints.internal.RedisClient", return_value=mock_redis_client):
        with patch.object(mock_redis_client, "add_to_queue", return_value=True):
            response = client.post(f"/v1/internal/gwas-dlq/retry/{guid}")

            assert response.status_code == 200
            assert f"Successfully moved message with GUID {guid}" in response.json()["message"]


def test_retry_gwas_dlq_by_guid_not_found(mock_redis_client):
    """Test retrying a GUID that doesn't exist in DLQ."""
    guid = "non-existent-guid"

    # DLQ has a different GUID
    dlq_message = {"original_message": {"metadata": {"guid": "different-guid"}}}
    mock_redis_client.redis.lrange.return_value = [json.dumps(dlq_message)]

    with patch("app.api.v1.endpoints.internal.RedisClient", return_value=mock_redis_client):
        response = client.post(f"/v1/internal/gwas-dlq/retry/{guid}")

        assert response.status_code == 404
        assert "not found in dead letter queue" in response.json()["detail"]


def test_retry_gwas_dlq_by_guid_empty_dlq(mock_redis_client):
    """Test retrying from empty DLQ."""
    guid = "test-guid-123"
    mock_redis_client.redis.lrange.return_value = []

    with patch("app.api.v1.endpoints.internal.RedisClient", return_value=mock_redis_client):
        response = client.post(f"/v1/internal/gwas-dlq/retry/{guid}")

        assert response.status_code == 404


def test_retry_all_gwas_dlq_success(mock_redis_client):
    """Test successfully retrying all messages from DLQ."""
    guids = ["guid-1", "guid-2", "guid-3"]

    with patch("app.api.v1.endpoints.internal.RedisClient", return_value=mock_redis_client):
        with patch.object(mock_redis_client, "get_all_guids_from_dlq", return_value=guids):
            with patch.object(mock_redis_client, "retry_guid_from_dlq", side_effect=[True, True, True]):
                response = client.post("/v1/internal/gwas-dlq/retry")

                assert response.status_code == 200
                assert response.json()["count"] == 3
                assert "Successfully moved 3 message(s)" in response.json()["message"]


def test_retry_all_gwas_dlq_partial_success(mock_redis_client):
    """Test retrying all messages with some failures."""
    guids = ["guid-1", "guid-2", "guid-3"]

    with patch("app.api.v1.endpoints.internal.RedisClient", return_value=mock_redis_client):
        with patch.object(mock_redis_client, "get_all_guids_from_dlq", return_value=guids):
            with patch.object(mock_redis_client, "retry_guid_from_dlq", side_effect=[True, False, True]):
                response = client.post("/v1/internal/gwas-dlq/retry")

                assert response.status_code == 200
                assert response.json()["count"] == 2
                assert "Successfully moved 2 message(s)" in response.json()["message"]


def test_retry_all_gwas_dlq_empty(mock_redis_client):
    """Test retrying all from empty DLQ."""
    with patch("app.api.v1.endpoints.internal.RedisClient", return_value=mock_redis_client):
        with patch.object(mock_redis_client, "get_all_guids_from_dlq", return_value=[]):
            response = client.post("/v1/internal/gwas-dlq/retry")

            assert response.status_code == 200
            assert response.json()["count"] == 0
            assert "Successfully moved 0 message(s)" in response.json()["message"]


def test_retry_all_gwas_dlq_exception(mock_redis_client):
    """Test retrying all handles exceptions."""
    with patch("app.api.v1.endpoints.internal.RedisClient", return_value=mock_redis_client):
        with patch.object(mock_redis_client, "get_all_guids_from_dlq", side_effect=Exception("Redis error")):
            response = client.post("/v1/internal/gwas-dlq/retry")

            assert response.status_code == 500


def test_clear_gwas_dlq_success(mock_redis_client):
    """Test successfully clearing the DLQ."""
    with patch("app.api.v1.endpoints.internal.RedisClient", return_value=mock_redis_client):
        with patch.object(mock_redis_client, "clear_dlq", return_value=True) as mock_clear:
            response = client.delete("/v1/internal/gwas-dlq")

            assert response.status_code == 200
            assert "Successfully cleared all messages" in response.json()["message"]
            mock_clear.assert_called_once_with(mock_redis_client.process_gwas_queue)


def test_clear_gwas_dlq_failure(mock_redis_client):
    """Test clearing DLQ when it fails."""
    with patch("app.api.v1.endpoints.internal.RedisClient", return_value=mock_redis_client):
        with patch.object(mock_redis_client, "clear_dlq", return_value=False):
            response = client.delete("/v1/internal/gwas-dlq")

            assert response.status_code == 500
            assert "Failed to clear dead letter queue" in response.json()["detail"]


def test_clear_gwas_dlq_exception(mock_redis_client):
    """Test clearing DLQ handles exceptions."""
    with patch("app.api.v1.endpoints.internal.RedisClient", return_value=mock_redis_client):
        with patch.object(mock_redis_client, "clear_dlq", side_effect=Exception("Redis error")):
            response = client.delete("/v1/internal/gwas-dlq")

            assert response.status_code == 500


def test_add_to_gwas_queue_success(mock_redis_client):
    """Test successfully adding a message to the GWAS queue."""
    test_message = {
        "file_location": "gwas_upload/test-guid/test_file.tsv.gz",
        "metadata": {
            "guid": "test-guid-123",
            "name": "Test Study",
            "email": "test@example.com",
        },
    }

    with patch("app.api.v1.endpoints.internal.RedisClient", return_value=mock_redis_client):
        with patch.object(mock_redis_client, "add_to_queue", return_value=True):
            with patch.object(mock_redis_client, "get_queue_size", return_value=5):
                response = client.post("/v1/internal/gwas-queue/add", json=test_message)

                assert response.status_code == 200
                assert "Successfully added message to process_gwas_queue" in response.json()["message"]
                assert response.json()["queue_size"] == 5
                mock_redis_client.add_to_queue.assert_called_once_with(
                    mock_redis_client.process_gwas_queue, test_message
                )


def test_add_to_gwas_queue_failure(mock_redis_client):
    """Test adding a message when add_to_queue returns False."""
    test_message = {"file_location": "test.tsv.gz", "metadata": {"guid": "test-guid"}}

    with patch("app.api.v1.endpoints.internal.RedisClient", return_value=mock_redis_client):
        with patch.object(mock_redis_client, "add_to_queue", return_value=False):
            response = client.post("/v1/internal/gwas-queue/add", json=test_message)

            assert response.status_code == 500
            assert "Failed to add message to queue" in response.json()["detail"]


def test_add_to_gwas_queue_exception(mock_redis_client):
    """Test adding a message handles exceptions."""
    test_message = {"file_location": "test.tsv.gz", "metadata": {"guid": "test-guid"}}

    with patch("app.api.v1.endpoints.internal.RedisClient", return_value=mock_redis_client):
        with patch.object(mock_redis_client, "add_to_queue", side_effect=Exception("Redis error")):
            response = client.post("/v1/internal/gwas-queue/add", json=test_message)

            assert response.status_code == 500


def test_delete_gwas_success(mock_oci_service):
    """Test successfully deleting a GWAS upload."""
    guid = "test-guid-123"

    with patch("app.api.v1.endpoints.internal.OCIService", return_value=mock_oci_service):
        response = client.delete(f"/v1/internal/gwas/{guid}")

        assert response.status_code == 200
        assert (
            f"Successfully deleted GWAS upload with GUID {guid} and all associated data" in response.json()["message"]
        )
