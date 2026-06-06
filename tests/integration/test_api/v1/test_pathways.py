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
    for r in result.results:
        assert r.term_id is not None
        assert r.source in ("Reactome", "KEGG", "HP")
        assert r.pathway_size > 0
        assert r.overlap > 0
        assert r.p_value <= 0.05
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


def test_pathway_enrichment_with_p_value_threshold():
    """Test that a very strict p-value threshold returns fewer or no results."""
    response = client.get("/v1/pathways/enrichment?gene_ids=700&gene_ids=1967&gene_ids=2275&p_value_threshold=1e-50")
    assert response.status_code == 200
    data = response.json()
    result = PathwayEnrichmentResponse(**data)
    assert result.p_value_threshold == 1e-50
    assert len(result.results) == 0


def test_pathway_enrichment_lenient_threshold():
    """Test that a lenient p-value threshold returns results."""
    response = client.get("/v1/pathways/enrichment?gene_ids=700&gene_ids=1967&gene_ids=2275&p_value_threshold=1.0")
    assert response.status_code == 200
    data = response.json()
    result = PathwayEnrichmentResponse(**data)
    assert len(result.results) > 0
    for r in result.results:
        assert r.p_value <= 1.0


def test_pathway_enrichment_no_matching_genes():
    """Test enrichment with gene IDs that have no pathway mappings."""
    response = client.get("/v1/pathways/enrichment?gene_ids=999999&gene_ids=999998")
    assert response.status_code == 200
    data = response.json()
    result = PathwayEnrichmentResponse(**data)
    assert result.input_gene_count == 2
    assert result.matched_gene_count == 0
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


def test_pathway_enrichment_results_sorted_by_p_value():
    """Test that results are sorted by p-value ascending."""
    response = client.get(
        "/v1/pathways/enrichment?gene_ids=700&gene_ids=1967&gene_ids=2275&gene_ids=2694&p_value_threshold=1.0"
    )
    assert response.status_code == 200
    data = response.json()
    result = PathwayEnrichmentResponse(**data)
    if len(result.results) > 1:
        p_values = [r.p_value for r in result.results]
        assert p_values == sorted(p_values)
