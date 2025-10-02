from fastapi.testclient import TestClient
from app.main import app
from app.models.schemas import Lds

client = TestClient(app)


def test_get_ld_matrix_with_snp_ids(variants_in_ld_db):
    snp_ids = list(variants_in_ld_db.keys())
    response = client.get(f"v1/ld/matrix?snp_ids={snp_ids[0]}&snp_ids={snp_ids[1]}")
    assert response.status_code == 200

    ld_matrix = response.json()
    assert len(ld_matrix) > 0
    lds = Lds(**ld_matrix)
    for row in lds.lds:
        assert row.lead_snp_id is not None
        assert row.variant_snp_id is not None
        assert row.ld_block_id is not None
        assert row.r is not None


def test_get_ld_matrix_with_variants(variants_in_ld_db):
    variants = list(variants_in_ld_db.values())
    response = client.get(f"v1/ld/matrix?variants={variants[0]}&variants={variants[1]}")
    assert response.status_code == 200

    ld_matrix = response.json()
    assert len(ld_matrix) > 0
    lds = Lds(**ld_matrix)
    for row in lds.lds:
        assert row.lead_snp_id is not None
        assert row.variant_snp_id is not None
        assert row.ld_block_id is not None
        assert row.r is not None


def test_get_ld_proxy_with_snp_ids(variants_in_ld_db):
    snp_ids = list(variants_in_ld_db.keys())
    response = client.get(f"v1/ld/proxies?snp_ids={snp_ids[0]}&snp_ids={snp_ids[1]}")
    assert response.status_code == 200
    ld_proxy = response.json()
    assert len(ld_proxy) > 0
    lds = Lds(**ld_proxy)
    for row in lds.lds:
        assert row.lead_snp_id is not None
        assert row.variant_snp_id is not None
        assert row.r is not None
        assert row.ld_block_id is not None


def test_get_ld_proxy_with_variants(variants_in_ld_db):
    variants = list(variants_in_ld_db.values())
    response = client.get(f"v1/ld/proxies?variants={variants[0]}&variants={variants[1]}")
    assert response.status_code == 200
    ld_proxy = response.json()
    assert len(ld_proxy) > 0
    lds = Lds(**ld_proxy)
    for row in lds.lds:
        assert row.lead_snp_id is not None
        assert row.variant_snp_id is not None
        assert row.r is not None
        assert row.ld_block_id is not None
