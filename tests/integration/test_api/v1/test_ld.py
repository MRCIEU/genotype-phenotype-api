from fastapi.testclient import TestClient
from app.main import app
from app.models.schemas import Ld

client = TestClient(app)


def test_get_ld_matrix_with_snp_ids():
    response = client.get("/v1/ld/matrix?snp_ids=5758009&snp_ids=5757997")
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
    response = client.get("/v1/ld/matrix?variants=3:45579683_A_C&variants=3:45582317_G_T")
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
    response = client.get("/v1/ld/proxies?snp_ids=5758009&snp_ids=5757997")
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
    response = client.get("/v1/ld/proxies?variants=3:45576631_A_G&variants=3:45579683_A_C")
    assert response.status_code == 200
    ld_proxy = response.json()
    assert len(ld_proxy) > 0
    for row in ld_proxy:
        ld = Ld(**row)
        assert ld.lead_snp_id is not None
        assert ld.variant_snp_id is not None
        assert ld.r is not None
        assert ld.ld_block_id is not None
