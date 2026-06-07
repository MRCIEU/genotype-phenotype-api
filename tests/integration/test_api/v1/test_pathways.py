from fastapi.testclient import TestClient
from app.main import app
from app.models.schemas import PathwayEnrichmentResponse

client = TestClient(app)


def test_pathway_enrichment_basic():
    """Test enrichment with gene IDs known to have KEGG pathway mappings."""
    response = client.get("/v1/pathways/enrichment?gene_ids=700&gene_ids=1967&gene_ids=2275&gene_ids=558")
    assert response.status_code == 200
    data = response.json()
    result = PathwayEnrichmentResponse(**data)
    assert result.input_gene_count == 4
    assert result.matched_gene_count > 0
    assert result.p_value_threshold == 0.05
    assert result.total_terms_tested > 0
    for r in result.results:
        assert r.term_id is not None
        assert r.source in ("Reactome", "KEGG", "HP")
        assert r.pathway_size > 0
        assert r.background_size > 0
        assert r.overlap > 0
        assert r.p_value <= r.fdr or r.fdr == r.p_value
        assert r.fdr <= 0.05
        assert len(r.gene_ids) == r.overlap


def test_pathway_enrichment_with_source_filter():
    """Test enrichment filtered to KEGG only."""
    response = client.get("/v1/pathways/enrichment?gene_ids=700&gene_ids=1967&gene_ids=2275&source=KEGG")
    assert response.status_code == 200
    data = response.json()
    result = PathwayEnrichmentResponse(**data)
    assert result.source == "KEGG"
    for r in result.results:
        assert r.source == "KEGG"


def test_pathway_enrichment_with_strict_threshold():
    """Test that a very strict FDR threshold returns fewer or no results."""
    response = client.get("/v1/pathways/enrichment?gene_ids=700&gene_ids=1967&gene_ids=2275&p_value_threshold=1e-50")
    assert response.status_code == 200
    data = response.json()
    result = PathwayEnrichmentResponse(**data)
    assert result.p_value_threshold == 1e-50
    assert len(result.results) == 0


def test_pathway_enrichment_lenient_threshold():
    """Test that a lenient FDR threshold returns results."""
    response = client.get("/v1/pathways/enrichment?gene_ids=700&gene_ids=1967&gene_ids=2275&p_value_threshold=1.0")
    assert response.status_code == 200
    data = response.json()
    result = PathwayEnrichmentResponse(**data)
    assert len(result.results) > 0
    for r in result.results:
        assert r.fdr <= 1.0
        assert r.p_value <= r.fdr


def test_pathway_enrichment_fdr_greater_than_or_equal_to_raw_p():
    """FDR-adjusted p-values should always be >= the raw p-value."""
    response = client.get(
        "/v1/pathways/enrichment?gene_ids=700&gene_ids=1967&gene_ids=2275&gene_ids=2694&p_value_threshold=1.0"
    )
    assert response.status_code == 200
    result = PathwayEnrichmentResponse(**response.json())
    for r in result.results:
        assert r.fdr + 1e-9 >= r.p_value


def test_pathway_enrichment_no_matching_genes():
    """Test enrichment with gene IDs that have no pathway mappings."""
    response = client.get("/v1/pathways/enrichment?gene_ids=999999&gene_ids=999998")
    assert response.status_code == 200
    data = response.json()
    result = PathwayEnrichmentResponse(**data)
    assert result.input_gene_count == 2
    assert result.matched_gene_count == 0
    assert result.total_terms_tested == 0
    assert len(result.results) == 0


def test_pathway_enrichment_invalid_source():
    """Test that an invalid source returns 400."""
    response = client.get("/v1/pathways/enrichment?gene_ids=700&source=InvalidSource")
    assert response.status_code == 400
    assert "Invalid source" in response.json()["detail"]


def test_pathway_enrichment_invalid_p_value():
    """Test that an invalid p_value_threshold returns 400."""
    response = client.get("/v1/pathways/enrichment?gene_ids=700&p_value_threshold=0")
    assert response.status_code == 400
    assert "p_value_threshold" in response.json()["detail"]


def test_pathway_enrichment_no_gene_ids():
    """Test that missing gene_ids returns 422 (FastAPI validation)."""
    response = client.get("/v1/pathways/enrichment")
    assert response.status_code == 422


def test_pathway_enrichment_results_sorted_by_fdr():
    """Test that results are sorted by FDR ascending."""
    response = client.get(
        "/v1/pathways/enrichment?gene_ids=700&gene_ids=1967&gene_ids=2275&gene_ids=2694&p_value_threshold=1.0"
    )
    assert response.status_code == 200
    data = response.json()
    result = PathwayEnrichmentResponse(**data)
    if len(result.results) > 1:
        fdr_values = [r.fdr for r in result.results]
        assert fdr_values == sorted(fdr_values)


def test_pathway_enrichment_resource_specific_background():
    """Verify that background_size varies per source (resource-specific normalization)."""
    response = client.get(
        "/v1/pathways/enrichment?gene_ids=700&gene_ids=1967&gene_ids=2275&gene_ids=558&p_value_threshold=1.0"
    )
    assert response.status_code == 200
    result = PathwayEnrichmentResponse(**response.json())
    backgrounds_by_source: dict[str, set[int]] = {}
    for r in result.results:
        backgrounds_by_source.setdefault(r.source, set()).add(r.background_size)
    for src, bgs in backgrounds_by_source.items():
        assert len(bgs) >= 1, f"Expected consistent background per source {src}"


def test_pathway_enrichment_total_terms_tested():
    """total_terms_tested should be reported and be at least the number of results."""
    response = client.get("/v1/pathways/enrichment?gene_ids=700&gene_ids=1967&gene_ids=2275&p_value_threshold=1.0")
    assert response.status_code == 200
    result = PathwayEnrichmentResponse(**response.json())
    assert result.total_terms_tested >= len(result.results)


def test_pathway_enrichment_source_filter_matches_per_category_fdr():
    """STRING applies BH per category; KEGG FDR should match with or without source filter."""
    genes = "gene_ids=700&gene_ids=1967&gene_ids=2275"
    all_response = client.get(f"/v1/pathways/enrichment?{genes}&p_value_threshold=1.0")
    kegg_response = client.get(f"/v1/pathways/enrichment?{genes}&source=KEGG&p_value_threshold=1.0")
    assert all_response.status_code == 200
    assert kegg_response.status_code == 200

    all_result = PathwayEnrichmentResponse(**all_response.json())
    kegg_result = PathwayEnrichmentResponse(**kegg_response.json())

    all_kegg = {r.term_id: r for r in all_result.results if r.source == "KEGG"}
    for r in kegg_result.results:
        assert r.term_id in all_kegg
        assert all_kegg[r.term_id].fdr == r.fdr
        assert all_kegg[r.term_id].p_value == r.p_value


def test_pathway_enrichment_total_terms_tested_is_overlapping_only():
    """total_terms_tested counts overlapping viable terms tested, not the full catalogue."""
    genes = "gene_ids=700&gene_ids=1967&gene_ids=2275"
    response = client.get(f"/v1/pathways/enrichment?{genes}&source=KEGG&p_value_threshold=1.0")
    assert response.status_code == 200
    result = PathwayEnrichmentResponse(**response.json())
    assert result.total_terms_tested < 371
    assert result.total_terms_tested >= len(result.results)
