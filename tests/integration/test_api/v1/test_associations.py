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


def test_bad_get_associations_full_query():
    response = client.get("v1/associations/full")
    assert response.status_code == 422


def test_get_associations_full_not_found():
    response = client.get("v1/associations/full?trait_id=999999999")
    assert response.status_code == 404


def test_get_associations_full_by_trait_id():
    trait_id = 926
    response = client.get(f"v1/associations/full?trait_id={trait_id}")
    assert response.status_code == 200

    associations = response.json()["associations"]
    assert len(associations) > 0
    assert any(association["study_id"] == trait_id for association in associations)
    for association in associations:
        assert "beta" in association
        assert "se" in association
        assert "p" in association
        assert "eaf" in association
        assert "imputed" in association


def test_get_associations_full_includes_study_extractions_not_in_colocs():
    trait_id = 926
    response = client.get(f"v1/associations/full?trait_id={trait_id}")
    assert response.status_code == 200

    associations = response.json()["associations"]
    assert any(a["variant_id"] == 80717 and a["study_id"] == trait_id for a in associations)


def test_get_associations_full_uses_trait_id_cache(mocker):
    import json

    stored = {}
    mock_redis = mocker.patch("app.services.redis_decorator.RedisClient")
    redis_instance = mock_redis.return_value
    redis_instance.get_cached_data.side_effect = lambda key: json.loads(stored[key]) if key in stored else None
    redis_instance.set_cached_data.side_effect = lambda key, data, expire: stored.update({key: data})

    trait_id = 926
    service = AssociationsService()
    fetch = mocker.spy(service, "_fetch_associations_full_for_pairs")
    result_first = service.get_associations_full(trait_id)
    result_second = service.get_associations_full(trait_id)

    assert result_first == result_second
    assert fetch.call_count == 1
    assert redis_instance.set_cached_data.call_count == 1
    assert redis_instance.get_cached_data.call_count == 2
    assert f"associations_full_cache:_get_associations_full_cached:{trait_id}" in stored
