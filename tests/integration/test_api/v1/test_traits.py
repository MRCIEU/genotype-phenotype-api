from fastapi.testclient import TestClient
from app.main import app
from app.models.schemas import TraitResponse, GetTraitsResponse

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
        assert association["snp_id"] is not None
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
