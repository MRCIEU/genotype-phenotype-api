from fastapi.testclient import TestClient
from app.main import app
from app.models.schemas import SearchTerm, VariantSearchResponse

client = TestClient(app)


def test_get_search_options():
    response = client.get("/v1/search/options")
    assert response.status_code == 200
    search_options = response.json()
    assert isinstance(search_options, list)
    assert len(search_options) > 0

    for option in search_options:
        search_term = SearchTerm(**option)
        assert search_term.type is not None
        assert search_term.type_id is not None
        assert search_term.name is not None
        if search_term.type == "gene":
            assert search_term.alt_name is not None


def test_search_variant_by_rsid(variants_in_studies_db):
    rsids = [variant["rsid"] for variant in variants_in_studies_db.values()]
    response = client.get(f"/v1/search/variant/{rsids[0]}")
    assert response.status_code == 200
    variants = VariantSearchResponse(**response.json())
    assert isinstance(variants, VariantSearchResponse)

    assert len(variants.original_variants) > 0
    assert len(variants.original_variants[0].ld_proxies) > 0
    assert len(variants.proxy_variants) > 0
    assert len(variants.proxy_variants[0].ld_proxies) > 0


def test_search_variant_by_chr_bp(variants_in_studies_db):
    variants = [variant["variant"] for variant in variants_in_studies_db.values()]
    response = client.get(f"/v1/search/variant/{variants[0]}")
    assert response.status_code == 200
    variants = VariantSearchResponse(**response.json())
    assert isinstance(variants, VariantSearchResponse)

    assert len(variants.original_variants) > 0
    assert len(variants.original_variants[0].ld_proxies) > 0
    assert len(variants.proxy_variants) > 0
    assert len(variants.proxy_variants[0].ld_proxies) > 0
