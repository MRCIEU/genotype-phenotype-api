import pytest
import json
from unittest.mock import Mock, patch
from app.db.redis import RedisClient


class TestRedisDLQ:
    """Unit tests for Redis dead letter queue functionality."""

    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis instance."""
        return Mock()

    @pytest.fixture
    def redis_client(self, mock_redis):
        """Create a RedisClient instance with mocked Redis."""
        with patch("app.db.redis.Redis", return_value=mock_redis):
            client = RedisClient()
            client.redis = mock_redis
            return client

    @pytest.fixture
    def sample_dlq_message(self):
        """Sample DLQ message structure."""
        original_message = {
            "file_location": "/path/to/file.tsv.gz",
            "metadata": {"guid": "test-guid-123", "email": "test@example.com", "name": "Test Study"},
        }
        return {"original_message": original_message, "error": "Processing failed", "timestamp": "2024-01-01T00:00:00Z"}

    def test_get_all_guids_from_dlq_success(self, redis_client, mock_redis, sample_dlq_message):
        """Test getting all GUIDs from DLQ successfully."""
        dlq_name = "process_gwas_dlq"
        mock_redis.lrange.return_value = [json.dumps(sample_dlq_message)]

        guids = redis_client.get_all_guids_from_dlq(redis_client.process_gwas_queue)

        assert guids == ["test-guid-123"]
        mock_redis.lrange.assert_called_once_with(dlq_name, 0, -1)

    def test_get_all_guids_from_dlq_multiple_messages(self, redis_client, mock_redis):
        """Test getting GUIDs from multiple DLQ messages."""
        messages = [
            {"original_message": {"metadata": {"guid": "guid-1"}}},
            {"original_message": {"metadata": {"guid": "guid-2"}}},
            {"original_message": {"metadata": {"guid": "guid-3"}}},
        ]
        mock_redis.lrange.return_value = [json.dumps(msg) for msg in messages]

        guids = redis_client.get_all_guids_from_dlq(redis_client.process_gwas_queue)

        assert set(guids) == {"guid-1", "guid-2", "guid-3"}

    def test_get_all_guids_from_dlq_no_guid(self, redis_client, mock_redis):
        """Test handling messages without GUID."""
        message_without_guid = {"original_message": {"metadata": {}}}
        mock_redis.lrange.return_value = [json.dumps(message_without_guid)]

        guids = redis_client.get_all_guids_from_dlq(redis_client.process_gwas_queue)

        assert guids == []

    def test_get_all_guids_from_dlq_malformed_message(self, redis_client, mock_redis):
        """Test handling malformed messages."""
        mock_redis.lrange.return_value = ["invalid json", '{"incomplete":']

        guids = redis_client.get_all_guids_from_dlq(redis_client.process_gwas_queue)

        assert guids == []

    def test_get_all_guids_from_dlq_empty_queue(self, redis_client, mock_redis):
        """Test getting GUIDs from empty DLQ."""
        mock_redis.lrange.return_value = []

        guids = redis_client.get_all_guids_from_dlq(redis_client.process_gwas_queue)

        assert guids == []

    def test_retry_guid_from_dlq_success(self, redis_client, mock_redis, sample_dlq_message):
        """Test successfully retrying a GUID from DLQ."""
        queue_name = "process_gwas"
        dlq_name = f"{queue_name}_dlq"
        guid = "test-guid-123"

        # Mock DLQ containing the message
        mock_redis.lrange.return_value = [json.dumps(sample_dlq_message)]
        mock_redis.delete.return_value = 1
        mock_redis.rpush.return_value = 1

        # Mock add_to_queue to return True
        with patch.object(redis_client, "add_to_queue", return_value=True) as mock_add:
            result = redis_client.retry_guid_from_dlq(queue_name, guid)

            assert result is True
            mock_redis.lrange.assert_called_once_with(dlq_name, 0, -1)
            mock_redis.delete.assert_called_once_with(dlq_name)
            mock_add.assert_called_once_with(queue_name, sample_dlq_message["original_message"])

    def test_retry_guid_from_dlq_not_found(self, redis_client, mock_redis):
        """Test retrying a GUID that doesn't exist in DLQ."""
        queue_name = "process_gwas"
        guid = "non-existent-guid"

        message = {"original_message": {"metadata": {"guid": "different-guid"}}}
        mock_redis.lrange.return_value = [json.dumps(message)]

        result = redis_client.retry_guid_from_dlq(queue_name, guid)

        assert result is False

    def test_retry_guid_from_dlq_add_to_queue_fails(self, redis_client, mock_redis, sample_dlq_message):
        """Test when add_to_queue fails, message is put back in DLQ."""
        queue_name = "process_gwas"
        guid = "test-guid-123"

        mock_redis.lrange.return_value = [json.dumps(sample_dlq_message)]
        mock_redis.delete.return_value = 1
        mock_redis.rpush.return_value = 1

        # Mock add_to_queue to return False
        with patch.object(redis_client, "add_to_queue", return_value=False) as mock_add:
            result = redis_client.retry_guid_from_dlq(queue_name, guid)

            assert result is False
            mock_add.assert_called_once_with(queue_name, sample_dlq_message["original_message"])
            # Message should be put back in DLQ
            assert mock_redis.rpush.call_count >= 1

    def test_retry_guid_from_dlq_with_remaining_messages(self, redis_client, mock_redis):
        """Test retrying a GUID when there are other messages in DLQ."""
        queue_name = "process_gwas"
        guid = "guid-to-retry"

        message_to_retry = {"original_message": {"metadata": {"guid": guid}}}
        other_message = {"original_message": {"metadata": {"guid": "other-guid"}}}

        mock_redis.lrange.return_value = [json.dumps(message_to_retry), json.dumps(other_message)]
        mock_redis.delete.return_value = 1
        mock_redis.rpush.return_value = 1

        with patch.object(redis_client, "add_to_queue", return_value=True):
            result = redis_client.retry_guid_from_dlq(queue_name, guid)

            assert result is True
            # Should rebuild DLQ with remaining message
            assert mock_redis.rpush.call_count >= 1

    def test_retry_guid_from_dlq_invalid_queue_name(self, redis_client):
        """Test retrying with invalid queue name raises ValueError."""
        with pytest.raises(ValueError, match="Queue name.*is not accepted"):
            redis_client.retry_guid_from_dlq("invalid_queue", "test-guid")

    def test_clear_dlq_success(self, redis_client, mock_redis):
        """Test successfully clearing the DLQ."""
        dlq_name = "process_gwas_dlq"
        queue_name = "process_gwas"
        mock_redis.delete.return_value = 1

        result = redis_client.clear_dlq(queue_name)

        assert result is True
        mock_redis.delete.assert_called_once_with(dlq_name)

    def test_clear_dlq_failure(self, redis_client, mock_redis):
        """Test clearing DLQ when Redis delete fails."""
        queue_name = "process_gwas"
        mock_redis.delete.side_effect = Exception("Redis connection error")

        result = redis_client.clear_dlq(queue_name)

        assert result is False

    def test_clear_dlq_invalid_queue_name(self, redis_client):
        """Test clearing DLQ with invalid queue name raises ValueError."""
        with pytest.raises(ValueError, match="Queue name.*is not accepted"):
            redis_client.clear_dlq("invalid_queue")
