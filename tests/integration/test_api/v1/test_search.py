import pytest
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
    
def test_search_variant_by_rsid():
    response = client.get("/v1/search/variant/rs6441921")
    assert response.status_code == 200
    variants = VariantSearchResponse(**response.json())
    assert isinstance(variants, VariantSearchResponse)

    assert len(variants.original_variants) > 0
    assert len(variants.proxy_variants) == 0
    assert variants.original_variants[0].num_colocs == 0
    assert variants.original_variants[0].num_rare_results == 0

def test_search_variant_by_chr_bp():
    response = client.get("/v1/search/variant/3:45576631")
    print(response.json())
    assert response.status_code == 200
    variants = VariantSearchResponse(**response.json())
    assert isinstance(variants, VariantSearchResponse)

    assert len(variants.original_variants) > 0
    assert len(variants.proxy_variants) == 0
    assert variants.original_variants[0].num_colocs == 0
    assert variants.original_variants[0].num_rare_results == 0
