import json
from os import system
import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def reset_gwas_upload_db():
    yield
    system("git checkout tests/test_data/gwas_upload_small.db")


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


def test_retry_gwas_dlq_by_guid_success(mock_redis_client, mocker):
    """Test successfully retrying a specific GUID from DLQ."""
    guid = "test-guid-123"
    dlq_message = {
        "original_message": {"file_location": "/path/to/file.tsv.gz", "metadata": {"guid": guid}},
        "error": "Processing failed",
        "timestamp": "2024-01-01T00:00:00Z",
    }

    mock_redis_client.redis.lrange.return_value = [json.dumps(dlq_message)]

    mocker.patch("app.api.v1.endpoints.internal.RedisClient", return_value=mock_redis_client)
    mocker.patch.object(mock_redis_client, "retry_guid_from_dlq", return_value=True)
    mocker.patch.object(mock_redis_client, "get_all_guids_from_dlq", return_value=[guid])

    response = client.post(f"/v1/internal/gwas-dlq/{guid}/retry")
    print(response.json())

    assert response.status_code == 200
    assert mock_redis_client.get_all_guids_from_dlq.return_value == [guid]
    assert mock_redis_client.retry_guid_from_dlq.return_value
    assert f"Successfully moved message with GUID {guid}" in response.json()["message"]


def test_retry_gwas_dlq_by_guid_not_found(mock_redis_client, mocker):
    """Test retrying a GUID that doesn't exist in DLQ."""
    guid = "non-existent-guid"

    # DLQ has a different GUID
    dlq_message = {"original_message": {"metadata": {"guid": "different-guid"}}}
    mock_redis_client.redis.lrange.return_value = [json.dumps(dlq_message)]

    mocker.patch("app.api.v1.endpoints.internal.RedisClient", return_value=mock_redis_client)

    response = client.post(f"/v1/internal/gwas-dlq/{guid}/retry")

    assert response.status_code == 404
    assert "not found in dead letter queue" in response.json()["detail"]


def test_retry_gwas_dlq_by_guid_empty_dlq(mock_redis_client, mocker):
    """Test retrying from empty DLQ."""
    guid = "test-guid-123"
    mock_redis_client.redis.lrange.return_value = []

    mocker.patch("app.api.v1.endpoints.internal.RedisClient", return_value=mock_redis_client)

    response = client.post(f"/v1/internal/gwas-dlq/{guid}/retry")

    assert response.status_code == 404


def test_retry_all_gwas_dlq_success(mock_redis_client, mocker):
    """Test successfully retrying all messages from DLQ."""
    guids = ["guid-1", "guid-2", "guid-3"]

    mocker.patch("app.api.v1.endpoints.internal.RedisClient", return_value=mock_redis_client)
    mocker.patch.object(mock_redis_client, "get_all_guids_from_dlq", return_value=guids)
    mocker.patch.object(mock_redis_client, "retry_guid_from_dlq", side_effect=[True, True, True])

    response = client.post("/v1/internal/gwas-dlq/retry")

    assert response.status_code == 200
    assert response.json()["count"] == 3
    assert "Successfully moved 3 message(s)" in response.json()["message"]


def test_retry_all_gwas_dlq_partial_success(mock_redis_client, mocker):
    """Test retrying all messages with some failures."""
    guids = ["guid-1", "guid-2", "guid-3"]

    mocker.patch("app.api.v1.endpoints.internal.RedisClient", return_value=mock_redis_client)
    mocker.patch.object(mock_redis_client, "get_all_guids_from_dlq", return_value=guids)
    mocker.patch.object(mock_redis_client, "retry_guid_from_dlq", side_effect=[True, False, True])

    response = client.post("/v1/internal/gwas-dlq/retry")

    assert response.status_code == 200
    assert response.json()["count"] == 2
    assert "Successfully moved 2 message(s)" in response.json()["message"]


def test_retry_all_gwas_dlq_empty(mock_redis_client, mocker):
    """Test retrying all from empty DLQ."""
    mocker.patch("app.api.v1.endpoints.internal.RedisClient", return_value=mock_redis_client)
    mocker.patch.object(mock_redis_client, "get_all_guids_from_dlq", return_value=[])

    response = client.post("/v1/internal/gwas-dlq/retry")

    assert response.status_code == 200
    assert response.json()["count"] == 0
    assert "Successfully moved 0 message(s)" in response.json()["message"]


def test_retry_all_gwas_dlq_exception(mock_redis_client, mocker):
    """Test retrying all handles exceptions."""
    mocker.patch("app.api.v1.endpoints.internal.RedisClient", return_value=mock_redis_client)
    mocker.patch.object(mock_redis_client, "get_all_guids_from_dlq", side_effect=Exception("Redis error"))

    response = client.post("/v1/internal/gwas-dlq/retry")

    assert response.status_code == 500


def test_clear_gwas_dlq_success(mock_redis_client, mocker):
    """Test successfully clearing the DLQ."""
    mocker.patch("app.api.v1.endpoints.internal.RedisClient", return_value=mock_redis_client)
    mock_clear = mocker.patch.object(mock_redis_client, "clear_dlq", return_value=True)

    response = client.delete("/v1/internal/gwas-dlq")

    assert response.status_code == 200
    assert "Successfully cleared all messages" in response.json()["message"]
    mock_clear.assert_called_once_with(mock_redis_client.process_gwas_queue)


def test_clear_gwas_dlq_failure(mock_redis_client, mocker):
    """Test clearing DLQ when it fails."""
    mocker.patch("app.api.v1.endpoints.internal.RedisClient", return_value=mock_redis_client)
    mocker.patch.object(mock_redis_client, "clear_dlq", return_value=False)

    response = client.delete("/v1/internal/gwas-dlq")

    assert response.status_code == 500
    assert "Failed to clear dead letter queue" in response.json()["detail"]


def test_clear_gwas_dlq_exception(mock_redis_client, mocker):
    """Test clearing DLQ handles exceptions."""
    mocker.patch("app.api.v1.endpoints.internal.RedisClient", return_value=mock_redis_client)
    mocker.patch.object(mock_redis_client, "clear_dlq", side_effect=Exception("Redis error"))

    response = client.delete("/v1/internal/gwas-dlq")

    assert response.status_code == 500


@pytest.fixture
def rerun_guid(mock_redis, mock_oci_service, mock_email_service):
    """Create a real GWAS upload record (via the upload endpoint) to rerun in tests."""
    request_data = {
        "reference_build": "GRCh38",
        "email": "ae@email.com",
        "name": "Example Study",
        "category": "continuous",
        "is_published": "false",
        "doi": None,
        "should_be_added": "false",
        "sample_size": "23423",
        "ancestry": "EUR",
        "p_value_threshold": 1.5e-4,
        "column_names": {
            "chr": "CHR",
            "bp": "BP",
            "ea": "EA",
            "oa": "OA",
            "beta": "BETA",
            "se": "SE",
            "p": "P",
            "eaf": "EAF",
            "rsid": "RSID",
        },
    }
    with open("tests/test_data/test_upload.tsv.gz", "rb") as f:
        response = client.post(
            "/v1/gwas/",
            data={"request": json.dumps(request_data)},
            files={"file": f},
        )
    assert response.status_code == 200
    return response.json()["guid"]


def test_rerun_gwas_success(rerun_guid, mock_redis_client, mock_oci_service, mocker):
    """Test that rerun-gwas reads file_location from study_metadata.json and re-queues the correct file."""
    guid = rerun_guid
    mocker.patch("app.api.v1.endpoints.internal.RedisClient", return_value=mock_redis_client)
    mocker.patch("app.api.v1.endpoints.internal.OCIService", return_value=mock_oci_service)

    study_metadata = {
        "file_location": f"/oradiskvdb1/data/gwas_upload/{guid}//metal_european_mothers_hdp.tsv.gz",
    }
    mocker.patch.object(mock_oci_service, "get_file", return_value=json.dumps(study_metadata).encode())

    response = client.post(f"/v1/internal/gwas/{guid}/rerun")

    assert response.status_code == 200
    assert f"Successfully rerun GWAS upload with GUID {guid}" in response.json()["message"]

    mock_oci_service.get_file.assert_called_once_with(f"gwas_upload/{guid}/study_metadata.json")

    mock_redis_client.redis.lpush.assert_called_once()
    queue_name, message = mock_redis_client.redis.lpush.call_args[0]
    assert queue_name == mock_redis_client.process_gwas_queue

    queued_message = json.loads(message)
    assert queued_message["file_location"] == f"gwas_upload/{guid}/metal_european_mothers_hdp.tsv.gz"
    assert queued_message["metadata"]["guid"] == guid


def test_rerun_gwas_not_found(mock_oci_service, mocker):
    """Test rerunning a GWAS that doesn't exist."""
    mocker.patch("app.api.v1.endpoints.internal.OCIService", return_value=mock_oci_service)

    response = client.post("/v1/internal/gwas/nonexistent-guid/rerun")

    assert response.status_code == 404
    assert "GWAS not found" in response.json()["detail"]


def test_rerun_gwas_missing_study_metadata(rerun_guid, mock_oci_service, mocker):
    """Test rerun when study_metadata.json can't be found in the bucket."""
    guid = rerun_guid
    mocker.patch("app.api.v1.endpoints.internal.OCIService", return_value=mock_oci_service)
    mocker.patch.object(mock_oci_service, "get_file", side_effect=Exception("Not found"))

    response = client.post(f"/v1/internal/gwas/{guid}/rerun")

    assert response.status_code == 404
    assert "study_metadata.json not found" in response.json()["detail"]


def test_rerun_gwas_missing_file_location(rerun_guid, mock_oci_service, mocker):
    """Test rerun when study_metadata.json has no file_location field."""
    guid = rerun_guid
    mocker.patch("app.api.v1.endpoints.internal.OCIService", return_value=mock_oci_service)
    mocker.patch.object(mock_oci_service, "get_file", return_value=json.dumps({}).encode())

    response = client.post(f"/v1/internal/gwas/{guid}/rerun")

    assert response.status_code == 404
    assert "No file_location found" in response.json()["detail"]


def test_delete_gwas_success(mock_oci_service, mocker):
    """Test successfully deleting a GWAS upload."""
    guid = "test-guid-123"

    mocker.patch("app.api.v1.endpoints.internal.OCIService", return_value=mock_oci_service)

    response = client.delete(f"/v1/internal/gwas/{guid}")

    assert response.status_code == 200
    assert f"Successfully deleted GWAS upload with GUID {guid} and all associated data" in response.json()["message"]
