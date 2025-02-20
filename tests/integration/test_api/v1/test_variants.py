import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.schemas import Association, ExtendedColoc, Variant, VariantResponse

client = TestClient(app)

def test_get_variants_by_variants():
    response = client.get("/v1/variants?variants=1:796652_A_C")
    assert response.status_code == 200
    variants = response.json()
    assert len(variants) > 0

    for row in variants:
        variant_model = Variant(**row)
        for field in variant_model.model_fields:
            assert getattr(variant_model, field) is not None, f"{field} should not be None"


def test_get_variants_by_rsids():
    response = client.get("/v1/variants?rsids=rs61770163&rsids=rs11240777")
    assert response.status_code == 200
    variants = response.json()
    assert len(variants) > 0
    for row in variants:
        variant_model = Variant(**row)
        for field in variant_model.model_fields:
            assert getattr(variant_model, field) is not None, f"{field} should not be None"

def test_get_variants_by_grange():
    response = client.get("/v1/variants?grange=1:796652-796653")
    assert response.status_code == 200
    variants = response.json()
    assert len(variants) > 0
    for row in variants:
        variant_model = Variant(**row)
        for field in variant_model.model_fields:
            assert getattr(variant_model, field) is not None, f"{field} should not be None"

def test_get_variant_by_id():
    response = client.get("/v1/variants/1:796652_A_C")
    assert response.status_code == 200
    variant = response.json()
    assert variant is not None
    variant_response = VariantResponse(**variant)
    assert variant_response.variant is not None
    assert variant_response.colocs is not None

    for coloc in variant_response.colocs:
        assert isinstance(coloc, ExtendedColoc)
        assert coloc.id is not None
        assert coloc.study is not None
        assert coloc.chr is not None
        assert coloc.bp is not None
        assert coloc.min_p is not None
        assert coloc.posterior_prob is not None
        if coloc.association is not None:
            assert isinstance(coloc.association, Association)
        

