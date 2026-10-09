from fastapi.testclient import TestClient
from app.main import app
from app.models.schemas import TraitResponse, GetTraitsResponse, GetTraitDuplicatesResponse

client = TestClient(app)


def test_get_traits():
    response = client.get("/v1/traits")
    assert response.status_code == 200
    traits = response.json()
    traits = GetTraitsResponse(**traits)
    assert traits is not None
    assert len(traits.traits) > 0
    for trait in traits.traits:
        assert trait.id is not None
        assert trait.trait_name is not None
        assert trait.sample_size is not None
        assert trait.category is not None
        assert trait.ancestry is not None
        assert trait.num_study_extractions is not None
        assert trait.num_coloc_groups is not None
        assert trait.num_coloc_studies is not None
        assert trait.num_rare_results is not None


def test_get_trait_duplicates():
    response = client.get("/v1/traits/duplicates")
    assert response.status_code == 200

    duplicates = GetTraitDuplicatesResponse(**response.json()).duplicates
    assert len(duplicates) > 0
    for duplicate in duplicates:
        assert duplicate.parent_trait_id is not None
        assert duplicate.trait_id != duplicate.parent_trait_id

    duplicates_by_trait_id = {duplicate.trait_id: duplicate for duplicate in duplicates}
    haematocrit = duplicates_by_trait_id[4760]
    assert haematocrit.trait_name == "Haematocrit percentage"
    assert haematocrit.parent_trait_id == 919
    assert haematocrit.parent_trait_name == "Hematocrit"

    haemoglobin_duplicate_ids = {d.trait_id for d in duplicates if d.parent_trait_id == 920}
    assert haemoglobin_duplicate_ids == {931, 1636, 2584, 4759}


def test_get_trait_duplicates_excludes_non_duplicated_traits():
    response = client.get("/v1/traits/duplicates")
    assert response.status_code == 200

    duplicate_trait_ids = {duplicate["trait_id"] for duplicate in response.json()["duplicates"]}
    # Parent traits (and unrelated traits) have no duplicate_of, so must not be listed as duplicates
    assert 919 not in duplicate_trait_ids
    assert 920 not in duplicate_trait_ids
    assert 5020 not in duplicate_trait_ids


def test_get_trait_duplicates_writes_to_cache(mock_redis_cache):
    response = client.get("/v1/traits/duplicates")
    assert response.status_code == 200

    mock_redis_cache.set_cached_data.assert_called_once()
    cache_key, cached_data, expire = mock_redis_cache.set_cached_data.call_args[0]
    assert cache_key == "studies_db_cache:get_trait_duplicates"
    assert GetTraitDuplicatesResponse.model_validate_json(cached_data).model_dump() == response.json()
    assert expire == 0


def test_get_trait_duplicates_returns_cached_response(mock_redis_cache, mocker):
    cached = {"duplicates": [{"trait_id": 1, "trait_name": "a", "parent_trait_id": 2, "parent_trait_name": "b"}]}
    mock_redis_cache.get_cached_data.return_value = cached
    db_query = mocker.patch("app.db.studies_db.StudiesDBClient.get_trait_duplicates")

    response = client.get("/v1/traits/duplicates")

    assert response.status_code == 200
    assert response.json() == cached
    db_query.assert_not_called()


def test_get_trait_by_id():
    trait_id = 5020
    response = client.get(f"/v1/traits/{trait_id}")
    print(response.json())
    assert response.status_code == 200
    traits = response.json()
    assert traits is not None

    trait_response = TraitResponse(**traits)
    assert trait_response.trait is not None
    assert trait_response.trait.id is not None
    assert trait_response.trait.trait_name is not None

    for coloc in trait_response.coloc_groups:
        assert coloc.coloc_group_id is not None
        assert coloc.study_extraction_id is not None
        assert coloc.chr is not None
        assert coloc.bp is not None
        assert coloc.min_p is not None
    grouped_colocs = {}

    for coloc in trait_response.coloc_groups:
        if coloc.coloc_group_id not in grouped_colocs:
            grouped_colocs[coloc.coloc_group_id] = []
        grouped_colocs[coloc.coloc_group_id].append(coloc)

    for group in grouped_colocs.values():
        assert any(coloc.trait_id == trait_id for coloc in group), "Each coloc group should contain the queried trait"

    for study in trait_response.study_extractions:
        assert study.unique_study_id is not None
        assert study.chr is not None
        assert study.bp is not None
        assert study.min_p is not None
    for rare_result in trait_response.rare_results:
        assert rare_result.study_extraction_id is not None
        assert rare_result.chr is not None
        assert rare_result.bp is not None
        assert rare_result.min_p is not None

    assert trait_response.upload_study_extractions is None


def test_get_trait_by_name():
    trait_name = "ukb-d-M13-FIBROBLASTIC"
    response = client.get(f"/v1/traits/{trait_name}")
    assert response.status_code == 200
    traits = response.json()
    assert traits is not None
    trait_response = TraitResponse(**traits)

    assert trait_response.trait is not None
    assert trait_response.trait.id is not None
    assert trait_response.trait.trait_name is not None


def test_get_trait_by_id_with_associations():
    response = client.get("/v1/traits/5020?include_associations=true")
    print(response.json())
    traits = response.json()
    print(traits)
    assert response.status_code == 200
    assert traits is not None
    trait_response = TraitResponse(**traits)
    assert trait_response.associations is not None
    assert len(trait_response.associations) > 0
    for association in trait_response.associations:
        assert association["variant_id"] is not None
        assert association["study_id"] is not None
        assert association["beta"] is not None
        assert association["se"] is not None


def test_get_traits_batch_by_ids():
    trait_ids = [5020, 1993]
    query_params = "&".join([f"ids={tid}" for tid in trait_ids])
    response = client.get(f"/v1/traits?{query_params}")
    assert response.status_code == 200
    data = response.json()
    traits_response = GetTraitsResponse(**data)
    assert len(traits_response.traits) > 0
    for trait in traits_response.traits:
        assert trait.id in trait_ids
    assert traits_response.coloc_groups is not None
    assert len(traits_response.coloc_groups) > 0
    assert traits_response.rare_results is not None
    assert len(traits_response.rare_results) > 0
    assert traits_response.study_extractions is not None
    assert len(traits_response.study_extractions) > 0


def test_get_traits_batch_with_associations():
    trait_ids = [5020, 1993]
    query_params = "&".join([f"ids={tid}" for tid in trait_ids])
    response = client.get(f"/v1/traits?{query_params}&include_associations=true")
    assert response.status_code == 200
    data = response.json()
    traits_response = GetTraitsResponse(**data)
    assert len(traits_response.traits) > 0
    assert traits_response.associations is not None
    assert len(traits_response.associations) > 0


def test_get_traits_batch_too_many():
    trait_ids = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
    query_params = "&".join([f"ids={tid}" for tid in trait_ids])
    response = client.get(f"/v1/traits?{query_params}")
    assert response.status_code == 400
    assert "Can not request more than 10" in response.json()["detail"]


def test_get_trait_coloc_pairs():
    response = client.get("/v1/traits/5020/coloc-pairs")
    print(response.json())
    assert response.status_code == 200
    response_json = response.json()
    assert response_json is not None
    coloc_pairs = response_json["coloc_pair_rows"]
    assert len(coloc_pairs) > 0
    coloc_pair_columns = response_json["coloc_pair_column_names"]
    assert len(coloc_pair_columns) > 0


def _associations_full_as_dicts(response_json):
    columns = response_json["associations_full_column_names"]
    rows = response_json["associations_full_rows"]
    return [dict(zip(columns, row)) for row in rows]


def test_get_trait_associations_full_not_found():
    response = client.get("/v1/traits/999999999/associations-full")
    assert response.status_code == 404


def test_get_trait_associations_full_by_trait_id():
    trait_id = 926
    response = client.get(f"/v1/traits/{trait_id}/associations-full")
    assert response.status_code == 200

    response_json = response.json()
    assert len(response_json["associations_full_column_names"]) > 0
    associations = _associations_full_as_dicts(response_json)
    assert len(associations) > 0
    assert any(association["study_id"] == trait_id for association in associations)
    for association in associations:
        assert "beta" in association
        assert "se" in association
        assert "p" in association
        assert "eaf" in association
        assert "imputed" in association


def test_get_trait_associations_full_includes_study_extractions_not_in_colocs():
    trait_id = 926
    response = client.get(f"/v1/traits/{trait_id}/associations-full")
    assert response.status_code == 200

    associations = _associations_full_as_dicts(response.json())
    assert any(a["variant_id"] == 80717 and a["study_id"] == trait_id for a in associations)


def test_get_trait_associations_full_cross_product_includes_linked_study_associations():
    trait_id = 926
    response = client.get(f"/v1/traits/{trait_id}/associations-full")
    assert response.status_code == 200

    associations = _associations_full_as_dicts(response.json())
    assert any(a["variant_id"] == 80717 and a["study_id"] != trait_id for a in associations)
