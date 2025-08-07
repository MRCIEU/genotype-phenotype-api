from fastapi.testclient import TestClient
from app.main import app
from app.models.schemas import (
    Association,
    ColocPair,
    ExtendedColocGroup,
    Variant,
    VariantResponse,
)


client = TestClient(app)


def test_get_variants_by_variants(variants_in_studies_db):
    snp_ids = list(variants_in_studies_db.keys())
    response = client.get(f"/v1/variants?snp_ids={snp_ids[0]}")
    assert response.status_code == 200
    variants = response.json()
    assert len(variants) > 0

    for row in variants:
        variant_model = Variant(**row)
        for field in variant_model.model_fields:
            if field != "canonical" and field != "gene_id" and field != "associations":
                assert getattr(variant_model, field) is not None, f"{field} should not be None"


def test_get_variants_by_variants_with_associations(variants_in_studies_db):
    snp_ids = list(variants_in_studies_db.keys())
    response = client.get(f"/v1/variants?snp_ids={snp_ids[0]}&include_associations=true")
    assert response.status_code == 200
    variants = response.json()
    assert len(variants) > 0

    for row in variants:
        variant_model = Variant(**row)
        for field in variant_model.model_fields:
            if field != "canonical" and field != "gene_id":
                assert getattr(variant_model, field) is not None, f"{field} should not be None"
        assert variant_model.associations is not None
        assert len(variant_model.associations) > 0
        for association in variant_model.associations:
            assert association.snp_id is not None
            assert association.study_id is not None
            assert association.p is not None
            assert association.beta is not None
            assert association.se is not None


def test_get_variants_by_variants_with_associations_and_possible_p_value_threshold(variants_in_studies_db):
    snp_ids = list(variants_in_studies_db.keys())
    response = client.get(f"/v1/variants?snp_ids={snp_ids[0]}&include_associations=true&p_value_threshold=5e-5")
    assert response.status_code == 200
    variants = response.json()
    assert len(variants) > 0

    for row in variants:
        variant_model = Variant(**row)
        for field in variant_model.model_fields:
            if field != "canonical" and field != "gene_id":
                assert getattr(variant_model, field) is not None, f"{field} should not be None"
        assert variant_model.associations is not None
        assert len(variant_model.associations) > 0
        for association in variant_model.associations:
            assert association.snp_id is not None
            assert association.study_id is not None
            assert association.p is not None
            assert association.beta is not None
            assert association.se is not None


def test_get_variants_by_variants_with_associations_and_impossible_p_value_threshold(variants_in_studies_db):
    snp_ids = list(variants_in_studies_db.keys())
    response = client.get(f"/v1/variants?snp_ids={snp_ids[0]}&include_associations=true&p_value_threshold=-1")
    assert response.status_code == 200
    variants = response.json()
    assert len(variants) > 0

    for row in variants:
        variant_model = Variant(**row)
        for field in variant_model.model_fields:
            if field != "canonical" and field != "gene_id":
                assert getattr(variant_model, field) is not None, f"{field} should not be None"
        assert variant_model.associations is not None
        assert len(variant_model.associations) == 0


def test_get_variants_by_rsids(variants_in_studies_db):
    rsids = [variant["rsid"] for variant in variants_in_studies_db.values()]
    response = client.get(f"/v1/variants?rsids={rsids[0]}&rsids={rsids[1]}")
    assert response.status_code == 200
    variants = response.json()
    assert len(variants) > 0
    for row in variants:
        variant_model = Variant(**row)
        for field in variant_model.model_fields:
            if field != "canonical" and field != "gene_id" and field != "associations":
                assert getattr(variant_model, field) is not None, f"{field} should not be None"


def test_get_variants_by_rsids_with_associations(variants_in_studies_db):
    rsids = [variant["rsid"] for variant in variants_in_studies_db.values()]
    response = client.get(f"/v1/variants?rsids={rsids[0]}&include_associations=true")
    assert response.status_code == 200
    variants = response.json()
    assert len(variants) > 0
    for row in variants:
        variant_model = Variant(**row)
        for field in variant_model.model_fields:
            if field != "canonical" and field != "gene_id":
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
            if field != "canonical" and field != "gene_id" and field != "associations":
                assert getattr(variant_model, field) is not None, f"{field} should not be None"


def test_get_variants_by_grange_with_associations():
    response = client.get("/v1/variants?grange=3:45576630-45579689&include_associations=true")
    assert response.status_code == 200
    variants = response.json()
    assert len(variants) > 0
    for row in variants:
        variant_model = Variant(**row)
        for field in variant_model.model_fields:
            if field != "canonical" and field != "gene_id":
                assert getattr(variant_model, field) is not None, f"{field} should not be None"
        assert variant_model.associations is not None
        for association in variant_model.associations:
            assert isinstance(association, Association)
            assert association.snp_id is not None
            assert association.study_id is not None
            assert association.p is not None
            assert association.beta is not None
            assert association.se is not None


def test_get_variant_by_id(variants_in_studies_db):
    snp_ids = list(variants_in_studies_db.keys())
    response = client.get(f"/v1/variants/{snp_ids[0]}")
    assert response.status_code == 200
    variant = response.json()
    assert variant is not None
    variant_response = VariantResponse(**variant)
    assert variant_response.variant is not None
    assert variant_response.coloc_groups is not None

    for coloc in variant_response.coloc_groups:
        assert isinstance(coloc, ExtendedColocGroup)
        assert coloc.coloc_group_id is not None
        assert coloc.study_extraction_id is not None
        assert coloc.chr is not None
        assert coloc.bp is not None
        assert coloc.min_p is not None
        if coloc.association is not None:
            assert isinstance(coloc.association, Association)


def test_get_variant_by_id_with_coloc_pairs(variants_in_studies_db):
    snp_ids = list(variants_in_studies_db.keys())
    response = client.get(f"/v1/variants/{snp_ids[0]}?include_coloc_pairs=true")
    assert response.status_code == 200
    variant = response.json()
    assert variant is not None
    variant_response = VariantResponse(**variant)
    assert variant_response.variant is not None
    assert variant_response.coloc_groups is not None

    for coloc in variant_response.coloc_groups:
        assert isinstance(coloc, ExtendedColocGroup)
        if coloc.association is not None:
            assert isinstance(coloc.association, Association)
    assert variant_response.coloc_pairs is not None
    assert len(variant_response.coloc_pairs) > 0
    for coloc_pair in variant_response.coloc_pairs:
        assert isinstance(coloc_pair, ColocPair)


def test_get_variant_summary_stats(variants_in_studies_db):
    snp_ids = list(variants_in_studies_db.keys())
    response = client.get(f"/v1/variants/{snp_ids[0]}/summary-stats")
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/zip"
    assert response.headers["Content-Disposition"] == f"attachment; filename=variant_{snp_ids[0]}_summary_stats.zip"
