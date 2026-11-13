import json

from fastapi.testclient import TestClient
from app.main import app
from app.services.associations_service import AssociationsService, ASSOCIATIONS_FULL_CACHE_MIN_ROWS

client = TestClient(app)


def test_bad_get_associations_query():
    response = client.get("v1/associations")
    assert response.status_code == 400


def test_get_associations_by_study_ids(snp_study_pairs_in_associations_db):
    study_ids = snp_study_pairs_in_associations_db["studies"]
    variant_ids = snp_study_pairs_in_associations_db["snps"]

    study_ids_param = "&".join([f"study_ids={study_id}" for study_id in study_ids])
    variant_ids_param = "&".join([f"variant_ids={variant_id}" for variant_id in variant_ids])

    response = client.get(f"v1/associations?{study_ids_param}&{variant_ids_param}")
    assert response.status_code == 200

    associations = response.json()["associations"]
    assert len(associations) > 2


def test_get_associations_full_uses_variant_and_study_sets(mocker):
    service = AssociationsService()
    fetch = mocker.spy(service, "_fetch_associations_full")
    service._get_associations_full_body(926, "rows")

    variant_ids, study_ids = fetch.call_args[0]
    assert variant_ids == {80717, 80732, 5553677}
    assert len(study_ids) > 1


def test_get_associations_full_filters_studies_by_table(mocker):
    service = AssociationsService()
    mocker.patch.object(
        service.associations_full_db,
        "get_study_ids_for_table_name",
        return_value=frozenset({926}),
    )
    query = mocker.spy(service.associations_full_db, "get_associations_by_table_name")

    service._fetch_associations_full({80717}, {926, 927, 932})

    assert query.call_count >= 1
    for call in query.call_args_list:
        assert call[0][2] == [926]


def _mock_redis_bytes(mocker, service):
    stored = {}
    redis_bytes = mocker.patch.object(service.redis_client, "redis_bytes")
    redis_bytes.get.side_effect = lambda key: stored.get(key)
    redis_bytes.set.side_effect = lambda key, value, ex: stored.update({key: value})
    return redis_bytes, stored


def test_get_associations_full_uses_trait_id_cache(mocker):
    # Test trait's result is far smaller than the real min-rows gate; disable it here so this
    # test can focus on the cache key mechanics (covered separately below).
    mocker.patch("app.services.associations_service.ASSOCIATIONS_FULL_CACHE_MIN_ROWS", 0)

    trait_id = 926
    service = AssociationsService()
    redis_bytes, stored = _mock_redis_bytes(mocker, service)
    fetch = mocker.spy(service, "_fetch_associations_full")
    result_first = service.get_associations_full(trait_id)
    result_second = service.get_associations_full(trait_id)

    assert isinstance(result_first, bytes)
    assert result_first == result_second
    assert fetch.call_count == 1
    assert redis_bytes.set.call_count == 1
    assert redis_bytes.get.call_count == 2
    assert f"associations_full_cache:{trait_id}:rows" in stored


def test_get_associations_full_rows_and_columnar_cache_keys_dont_collide(mocker):
    mocker.patch("app.services.associations_service.ASSOCIATIONS_FULL_CACHE_MIN_ROWS", 0)

    trait_id = 926
    service = AssociationsService()
    _, stored = _mock_redis_bytes(mocker, service)
    rows_body = service.get_associations_full(trait_id, format="rows")
    columnar_body = service.get_associations_full(trait_id, format="columnar")

    assert rows_body != columnar_body
    assert stored[f"associations_full_cache:{trait_id}:rows"] == rows_body
    assert stored[f"associations_full_cache:{trait_id}:columnar"] == columnar_body
    assert "associations_full_columns" in json.loads(service.get_associations_full(trait_id, format="columnar"))


def test_get_associations_full_skips_cache_write_for_small_result(mocker):
    """Results below ASSOCIATIONS_FULL_CACHE_MIN_ROWS shouldn't be written to Redis."""
    service = AssociationsService()
    redis_bytes, _ = _mock_redis_bytes(mocker, service)
    mocker.patch.object(
        service, "_fetch_associations_full", return_value=(["col"], [("row",)] * (ASSOCIATIONS_FULL_CACHE_MIN_ROWS - 1))
    )

    service.get_associations_full(926)

    redis_bytes.set.assert_not_called()


def test_get_associations_full_caches_large_result(mocker):
    """Results at/above ASSOCIATIONS_FULL_CACHE_MIN_ROWS should be written to Redis."""
    service = AssociationsService()
    redis_bytes, _ = _mock_redis_bytes(mocker, service)
    mocker.patch.object(
        service, "_fetch_associations_full", return_value=(["col"], [("row",)] * ASSOCIATIONS_FULL_CACHE_MIN_ROWS)
    )

    service.get_associations_full(926)

    redis_bytes.set.assert_called_once()
