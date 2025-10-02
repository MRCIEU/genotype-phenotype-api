import pytest
from unittest.mock import Mock, patch
import json

variant_data = {
    "8466140": {"rsid": "rs10085558", "variant": "7:37945678"},
    "8466253": {"rsid": "rs79590116", "variant": "7:37964907"},
}


@pytest.fixture(scope="session")
def variants_in_studies_db():
    return variant_data


@pytest.fixture(scope="session")
def variants_in_ld_db():
    return {
        "8466140": "7:37945678",
        "8466253": "7:37964907",
    }


@pytest.fixture(scope="session")
def variants_in_grange():
    return "7:37945678-37964907"


@pytest.fixture(autouse=True)
def mock_redis_cache():
    """Mock Redis cache calls for all tests - always cache miss, stub set operations"""
    
    # Mock the Redis client methods
    mock_redis_client = Mock()
    mock_redis_client.get_cached_data.return_value = None  # Always return None (cache miss)
    mock_redis_client.set_cached_data.return_value = None  # Stub set operation
    mock_redis_client.redis = Mock()
    mock_redis_client.redis.keys.return_value = []
    mock_redis_client.redis.delete.return_value = 0
    
    # Patch the Redis client in the decorator and service
    with patch('app.services.redis_decorator.RedisClient', return_value=mock_redis_client), \
         patch('app.services.studies_service.RedisClient', return_value=mock_redis_client):
        yield mock_redis_client
