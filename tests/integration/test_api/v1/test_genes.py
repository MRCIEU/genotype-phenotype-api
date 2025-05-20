import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.schemas import GeneResponse

client = TestClient(app)

def test_get_genes_with_colocs():
    response = client.get("/v1/genes/WNT7B")
    assert response.status_code == 200
    genes = response.json()
    assert genes is not None

    gene_response = GeneResponse(**genes)
    assert gene_response.gene is not None
    assert gene_response.gene.id is not None
    assert gene_response.gene.gene is not None
    assert gene_response.gene.chr is not None
    assert gene_response.gene.start is not None
    assert gene_response.gene.stop is not None
    assert gene_response.colocs is not None

    for coloc in gene_response.colocs:
        assert coloc.coloc_group_id is not None
        assert coloc.study_extraction_id is not None
        assert coloc.chr is not None
        assert coloc.bp is not None
        assert coloc.min_p is not None
    for study in gene_response.study_extractions:
        assert study.unique_study_id is not None
        assert study.chr is not None
        assert study.bp is not None
        assert study.min_p is not None
    for rare_result in gene_response.rare_results:
        assert rare_result.study_extraction_id is not None
        assert rare_result.chr is not None
        assert rare_result.bp is not None
        assert rare_result.min_p is not None



