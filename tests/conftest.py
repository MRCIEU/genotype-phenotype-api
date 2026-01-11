import pytest
from unittest.mock import Mock, patch
from app.models.schemas import Singleton

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


@pytest.fixture(scope="module", autouse=True)
def mock_redis():
    """Mock the underlying Redis connection so actual RedisClient code runs."""
    from app.db.redis import RedisClient

    mock_redis_instance = Mock()
    mock_redis_instance.lpush.return_value = None
    mock_redis_instance.get.return_value = None
    mock_redis_instance.set.return_value = None
    mock_redis_instance.delete.return_value = None
    mock_redis_instance.rpop.return_value = None
    mock_redis_instance.brpop.return_value = None
    mock_redis_instance.llen.return_value = 0
    mock_redis_instance.lrange.return_value = []
    mock_redis_instance.rpush.return_value = None
    mock_redis_instance.zadd.return_value = None
    mock_redis_instance.zrangebyscore.return_value = []
    mock_redis_instance.zremrangebyscore.return_value = None
    mock_redis_instance.zrange.return_value = []
    mock_redis_instance.zcount.return_value = 0
    mock_redis_instance.keys.return_value = []

    # Patch redis.Redis so when RedisClient creates it, it gets our mock
    with patch("app.db.redis.Redis", return_value=mock_redis_instance):
        # Clear singleton instance so it's recreated with our mocked Redis
        if RedisClient in Singleton._instances:
            del Singleton._instances[RedisClient]

        yield mock_redis_instance


@pytest.fixture(autouse=True)
def mock_redis_cache():
    """Mock Redis Client for all tests - always cache miss, stub set operations"""

    mock_redis_client = Mock()
    mock_redis_client.get_cached_data.return_value = None
    mock_redis_client.set_cached_data.return_value = None
    mock_redis_client.redis = Mock()
    mock_redis_client.redis.keys.return_value = []
    mock_redis_client.redis.delete.return_value = 0

    with (
        patch("app.services.redis_decorator.RedisClient", return_value=mock_redis_client),
        patch("app.services.studies_service.RedisClient", return_value=mock_redis_client),
    ):
        yield mock_redis_client


@pytest.fixture(scope="module", autouse=True)
def mock_oci_service():
    """Mock OCI Service for all tests - stubs all OCI Object Storage operations"""

    mock_oci_service_instance = Mock()

    mock_oci_service_instance.upload_file.return_value = "mocked_object_name"
    mock_oci_service_instance.download_file.return_value = "/mocked/local/path"
    mock_oci_service_instance.delete_file.return_value = True
    mock_oci_service_instance.get_file_url.return_value = "https://mocked-url.example.com/file"

    mock_oci_service_instance.bucket_name = "test_bucket"
    mock_oci_service_instance.namespace = "test_namespace"
    mock_oci_service_instance.region = "us-ashburn-1"

    with (
        patch("app.api.v1.endpoints.gwas.OCIService", return_value=mock_oci_service_instance),
        patch("app.services.oci_service.OCIService", return_value=mock_oci_service_instance),
    ):
        yield mock_oci_service_instance
