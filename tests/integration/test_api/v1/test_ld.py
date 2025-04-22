import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.schemas import Ld

client = TestClient(app)

def test_get_ld_matrix_with_snp_ids():
    response = client.get("/v1/ld/matrix?snp_ids=4259899&snp_ids=4259944")
    assert response.status_code == 200

    ld_matrix = response.json()
    assert len(ld_matrix) > 0
    for row in ld_matrix:
        ld = Ld(**row)
        assert ld.lead_snp_id is not None
        assert ld.variant_snp_id is not None
        assert ld.ld_block_id is not None
        assert ld.r is not None

def test_get_ld_matrix_with_variants():
    response = client.get("/v1/ld/matrix?variants=19:57848276_G_T&variants=19:57855538_A_G")
    assert response.status_code == 200

    ld_matrix = response.json()
    assert len(ld_matrix) > 0
    for row in ld_matrix:
        ld = Ld(**row)
        assert ld.lead_snp_id is not None
        assert ld.variant_snp_id is not None
        assert ld.ld_block_id is not None
        assert ld.r is not None


def test_get_ld_proxy_with_snp_ids():
    response = client.get("/v1/ld/proxies?snp_ids=4259899&snp_ids=4259944")
    assert response.status_code == 200
    ld_proxy = response.json()
    assert len(ld_proxy) > 0
    for row in ld_proxy:
        ld = Ld(**row)
        assert ld.lead_snp_id is not None
        assert ld.variant_snp_id is not None
        assert ld.r is not None
        assert ld.ld_block_id is not None

def test_get_ld_proxy_with_variants():
    response = client.get("/v1/ld/proxies?variants=19:57848276_G_T&variants=19:57855538_A_G")
    assert response.status_code == 200
    ld_proxy = response.json()
    assert len(ld_proxy) > 0
    for row in ld_proxy:
        ld = Ld(**row)
        assert ld.lead_snp_id is not None
        assert ld.variant_snp_id is not None
        assert ld.r is not None
        assert ld.ld_block_id is not None