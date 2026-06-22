from fastapi.testclient import TestClient
from app.main import app
from app.services.associations_service import AssociationsService

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
    service._get_associations_full_cached(trait_id=926, cache_id="926")

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


def test_get_associations_full_uses_trait_id_cache(mocker):
    import json

    stored = {}
    mock_redis = mocker.patch("app.services.redis_decorator.RedisClient")
    redis_instance = mock_redis.return_value
    redis_instance.get_cached_data.side_effect = lambda key: json.loads(stored[key]) if key in stored else None
    redis_instance.set_cached_data.side_effect = lambda key, data, expire: stored.update({key: data})

    trait_id = 926
    service = AssociationsService()
    fetch = mocker.spy(service, "_fetch_associations_full")
    result_first = service.get_associations_full(trait_id)
    result_second = service.get_associations_full(trait_id)

    assert result_first == result_second
    assert fetch.call_count == 1
    assert redis_instance.set_cached_data.call_count == 1
    assert redis_instance.get_cached_data.call_count == 2
    assert f"associations_full_cache:_get_associations_full_cached:{trait_id}" in stored
