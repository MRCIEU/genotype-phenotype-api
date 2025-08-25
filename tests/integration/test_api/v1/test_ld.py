from fastapi.testclient import TestClient
from app.main import app
from app.models.schemas import Ld

client = TestClient(app)


def test_get_ld_matrix_with_snp_ids(variants_in_ld_db):
    snp_ids = list(variants_in_ld_db.keys())
    response = client.get(f"v1/ld/matrix?snp_ids={snp_ids[0]}&snp_ids={snp_ids[1]}")
    assert response.status_code == 200

    ld_matrix = response.json()
    assert len(ld_matrix) > 0
    for row in ld_matrix:
        ld = Ld(**row)
        assert ld.lead_snp_id is not None
        assert ld.variant_snp_id is not None
        assert ld.ld_block_id is not None
        assert ld.r is not None


def test_get_ld_matrix_with_variants(variants_in_ld_db):
    variants = list(variants_in_ld_db.values())
    response = client.get(f"v1/ld/matrix?variants={variants[0]}&variants={variants[1]}")
    assert response.status_code == 200

    ld_matrix = response.json()
    assert len(ld_matrix) > 0
    for row in ld_matrix:
        ld = Ld(**row)
        assert ld.lead_snp_id is not None
        assert ld.variant_snp_id is not None
        assert ld.ld_block_id is not None
        assert ld.r is not None


def test_get_ld_proxy_with_snp_ids(variants_in_ld_db):
    snp_ids = list(variants_in_ld_db.keys())
    response = client.get(f"v1/ld/proxies?snp_ids={snp_ids[0]}&snp_ids={snp_ids[1]}")
    print(response.json())
    assert response.status_code == 200
    ld_proxy = response.json()
    assert len(ld_proxy) > 0
    for row in ld_proxy:
        ld = Ld(**row)
        assert ld.lead_snp_id is not None
        assert ld.variant_snp_id is not None
        assert ld.r is not None
        assert ld.ld_block_id is not None


def test_get_ld_proxy_with_variants(variants_in_ld_db):
    variants = list(variants_in_ld_db.values())
    response = client.get(f"v1/ld/proxies?variants={variants[0]}&variants={variants[1]}")
    print(response.json())
    assert response.status_code == 200
    ld_proxy = response.json()
    assert len(ld_proxy) > 0
    for row in ld_proxy:
        ld = Ld(**row)
        assert ld.lead_snp_id is not None
        assert ld.variant_snp_id is not None
        assert ld.r is not None
        assert ld.ld_block_id is not None
