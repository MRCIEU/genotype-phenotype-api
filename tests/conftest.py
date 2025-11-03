import pytest
from unittest.mock import Mock, patch

variant_data = {
    "8466160": {"rsid": "rs16879765", "variant": "7:37949493"},
    "8466304": {"rsid": "rs145159117", "variant": "7:37979301"},
}


@pytest.fixture(scope="session")
def variants_in_studies_db():
    return variant_data


@pytest.fixture(scope="session")
def variants_in_ld_db(variants_in_studies_db):
    # Reformat variant_data to the LD format { snp_id: "chr:bp" }
    return {snp_id: data["variant"] for snp_id, data in variants_in_studies_db.items()}


@pytest.fixture(scope="session")
def variants_in_grange():
    return "7:37945678-37964907"


@pytest.fixture(scope="session")
def snp_study_pairs_in_associations_db():
    return {
        "studies": [4870, 5020],
        "snps": [
            80750,
            156076,
            449749,
            598663,
            601653,
            782722,
            912733,
            1188361,
            1207496,
            1208704,
            2124941,
            2174388,
            2285209,
            2549800,
            2608076,
            2608105,
        ],
    }

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
    with (
        patch("app.services.redis_decorator.RedisClient", return_value=mock_redis_client),
        patch("app.services.studies_service.RedisClient", return_value=mock_redis_client),
    ):
        yield mock_redis_client
