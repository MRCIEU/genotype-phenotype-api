import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.schemas import TraitResponse

client = TestClient(app)

def test_get_trait_by_id():
    response = client.get("/v1/traits/5020")
    assert response.status_code == 200
    traits = response.json()
    assert traits is not None

    trait_response = TraitResponse(**traits)
    assert trait_response.trait is not None
    assert trait_response.trait.id is not None
    assert trait_response.trait.trait_name is not None

    for coloc in trait_response.colocs:
        assert coloc.coloc_group_id is not None
        assert coloc.study_extraction_id is not None
        assert coloc.chr is not None
        assert coloc.bp is not None
        assert coloc.min_p is not None
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
