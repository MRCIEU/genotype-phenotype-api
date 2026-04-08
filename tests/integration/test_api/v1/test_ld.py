from fastapi.testclient import TestClient
from app.main import app
from app.models.schemas import Lds

client = TestClient(app)


def test_get_ld_matrix_with_variant_ids(variants_in_ld_db):
    variant_ids = list(variants_in_ld_db.keys())
    response = client.get(f"v1/ld/matrix?variant_ids={variant_ids[0]}&variant_ids={variant_ids[1]}")
    print(response.json())
    assert response.status_code == 200

    ld_matrix = response.json()
    assert len(ld_matrix["lds"]) > 0
    lds = Lds(**ld_matrix)
    for row in lds.lds:
        assert row.lead_variant_id is not None
        assert row.proxy_variant_id is not None
        assert row.ld_block_id is not None
        assert row.r is not None


def test_get_ld_matrix_with_variants(variants_in_ld_db):
    variants = list(variants_in_ld_db.values())
    response = client.get(f"v1/ld/matrix?variants={variants[0]}&variants={variants[1]}")
    print(response.json())
    assert response.status_code == 200

    ld_matrix = response.json()
    assert len(ld_matrix["lds"]) > 0
    lds = Lds(**ld_matrix)
    for row in lds.lds:
        assert row.lead_variant_id is not None
        assert row.proxy_variant_id is not None
        assert row.ld_block_id is not None
        assert row.r is not None


def test_get_ld_proxy_with_variant_ids(variants_in_ld_db):
    variant_ids = list(variants_in_ld_db.keys())
    response = client.get(f"v1/ld/proxies?variant_ids={variant_ids[0]}&variant_ids={variant_ids[1]}")
    print(response.json())
    assert response.status_code == 200
    ld_proxy = response.json()
    assert len(ld_proxy["lds"]) > 0
    lds = Lds(**ld_proxy)
    for row in lds.lds:
        assert row.lead_variant_id is not None
        assert row.proxy_variant_id is not None
        assert row.r is not None
        assert row.ld_block_id is not None


def test_get_ld_proxies_with_rsquared_threshold(variants_in_ld_db):
    variants = list(variants_in_ld_db.values())

    # Test with default threshold (0.8)
    response_default = client.get(f"v1/ld/proxies?variants={variants[0]}&variants={variants[1]}")
    print(response_default.json())
    assert response_default.status_code == 200
    proxies_default = response_default.json()["lds"]

    # Test with higher threshold (0.9)
    response_high = client.get(f"v1/ld/proxies?variants={variants[0]}&variants={variants[1]}&rsquared_threshold=0.9")
    print(response_high.json())
    assert response_high.status_code == 200
    proxies_high = response_high.json()["lds"]

    assert len(proxies_high) <= len(proxies_default)
    for proxy in proxies_high:
        assert proxy["r"] ** 2 >= 0.9

    # Test invalid threshold
    response_invalid = client.get(f"v1/ld/proxies?variants={variants[0]}&rsquared_threshold=0.5")
    assert response_invalid.status_code == 400
    assert "R squared threshold must be between 0.8 and 1" in response_invalid.json()["detail"]


def test_get_ld_proxy_with_variants(variants_in_ld_db):
    variants = list(variants_in_ld_db.values())
    response = client.get(f"v1/ld/proxies?variants={variants[0]}&variants={variants[1]}")
    print(response.json())
    assert response.status_code == 200
    ld_proxy = response.json()
    assert len(ld_proxy["lds"]) > 0
    lds = Lds(**ld_proxy)
    for row in lds.lds:
        assert row.lead_variant_id is not None
        assert row.proxy_variant_id is not None
        assert row.r is not None
        assert row.ld_block_id is not None
