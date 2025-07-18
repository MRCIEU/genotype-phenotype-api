from fastapi.testclient import TestClient
from app.main import app
from app.models.schemas import Association, ExtendedColoc, Variant, VariantResponse


client = TestClient(app)

def test_get_variants_by_variants():
    response = client.get("/v1/variants?snp_ids=5758009")
    assert response.status_code == 200
    variants = response.json()
    assert len(variants) > 0

    for row in variants:
        variant_model = Variant(**row)
        for field in variant_model.model_fields:
            if field != 'canonical' and field != 'gene_id' and field != 'associations':
                assert getattr(variant_model, field) is not None, f"{field} should not be None"

def test_get_variants_by_variants_with_associations():
    response = client.get("/v1/variants?snp_ids=5758009&include_associations=true")
    assert response.status_code == 200
    variants = response.json()
    assert len(variants) > 0

    for row in variants:
        variant_model = Variant(**row)
        for field in variant_model.model_fields:
            if field != 'canonical' and field != 'gene_id':
                assert getattr(variant_model, field) is not None, f"{field} should not be None"
        assert variant_model.associations is not None
        assert len(variant_model.associations) > 0
        for association in variant_model.associations:
            assert association.snp_id is not None
            assert association.study_id is not None
            assert association.p is not None
            assert association.beta is not None
            assert association.se is not None

def test_get_variants_by_variants_with_associations_and_possible_p_value_threshold():
    response = client.get("/v1/variants?snp_ids=5758009&include_associations=true&p_value_threshold=5e-5")
    assert response.status_code == 200
    variants = response.json()
    assert len(variants) > 0

    for row in variants:
        variant_model = Variant(**row)
        for field in variant_model.model_fields:
            if field != 'canonical' and field != 'gene_id':
                assert getattr(variant_model, field) is not None, f"{field} should not be None"
        assert variant_model.associations is not None
        assert len(variant_model.associations) > 0
        for association in variant_model.associations:
            assert association.snp_id is not None
            assert association.study_id is not None
            assert association.p is not None
            assert association.beta is not None
            assert association.se is not None

def test_get_variants_by_variants_with_associations_and_impossible_p_value_threshold():
    response = client.get("/v1/variants?snp_ids=5758009&include_associations=true&p_value_threshold=0")
    assert response.status_code == 200
    variants = response.json()
    assert len(variants) > 0

    for row in variants:
        variant_model = Variant(**row)
        for field in variant_model.model_fields:
            if field != 'canonical' and field != 'gene_id':
                assert getattr(variant_model, field) is not None, f"{field} should not be None"
        assert variant_model.associations is not None
        assert len(variant_model.associations) == 0

def test_get_variants_by_rsids():
    response = client.get("/v1/variants?rsids=rs6441921&rsids=rs17078078")
    assert response.status_code == 200
    variants = response.json()
    assert len(variants) > 0
    for row in variants:
        variant_model = Variant(**row)
        for field in variant_model.model_fields:
            if field != 'canonical' and field != 'gene_id' and field != 'associations':
                assert getattr(variant_model, field) is not None, f"{field} should not be None"

def test_get_variants_by_rsids_with_associations():
    response = client.get("/v1/variants?rsids=rs6441921&rsids=rs17078078&include_associations=true")
    assert response.status_code == 200
    variants = response.json()
    assert len(variants) > 0
    for row in variants:
        variant_model = Variant(**row)
        for field in variant_model.model_fields:
            if field != 'canonical' and field != 'gene_id':
                assert getattr(variant_model, field) is not None, f"{field} should not be None"
        assert variant_model.associations is not None
        assert len(variant_model.associations) > 0
        for association in variant_model.associations:
            assert association.snp_id is not None
            assert association.study_id is not None
            assert association.p is not None
            assert association.beta is not None
            assert association.se is not None

def test_get_variants_by_grange():
    response = client.get("/v1/variants?grange=3:45576630-45579689")
    assert response.status_code == 200
    variants = response.json()
    assert len(variants) > 0
    for row in variants:
        variant_model = Variant(**row)
        for field in variant_model.model_fields:
            if field != 'canonical' and field != 'gene_id' and field != 'associations':
                assert getattr(variant_model, field) is not None, f"{field} should not be None"

def test_get_variants_by_grange_with_associations():
    response = client.get("/v1/variants?grange=3:45576630-45579689&include_associations=true")
    assert response.status_code == 200
    variants = response.json()
    assert len(variants) > 0
    for row in variants:
        variant_model = Variant(**row)
        for field in variant_model.model_fields:
            if field != 'canonical' and field != 'gene_id':
                assert getattr(variant_model, field) is not None, f"{field} should not be None"
        assert variant_model.associations is not None
        assert len(variant_model.associations) > 0
        for association in variant_model.associations:
            assert association.snp_id is not None
            assert association.study_id is not None
            assert association.p is not None
            assert association.beta is not None
            assert association.se is not None

def test_get_variant_by_id():
    response = client.get("/v1/variants/5758009")
    assert response.status_code == 200
    variant = response.json()
    assert variant is not None
    variant_response = VariantResponse(**variant)
    assert variant_response.variant is not None
    assert variant_response.colocs is not None

    for coloc in variant_response.colocs:
        assert isinstance(coloc, ExtendedColoc)
        assert coloc.coloc_group_id is not None
        assert coloc.study_extraction_id is not None
        assert coloc.chr is not None
        assert coloc.bp is not None
        assert coloc.min_p is not None
        assert coloc.posterior_prob is not None
        if coloc.association is not None:
            assert isinstance(coloc.association, Association)
        

def test_get_variant_summary_stats():
    response = client.get("/v1/variants/5758009/summary-stats")
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/zip"
    assert response.headers["Content-Disposition"] == "attachment; filename=variant_5758009_summary_stats.zip"