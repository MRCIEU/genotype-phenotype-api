import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.schemas import GeneResponse

client = TestClient(app)

def test_get_genes_with_no_colocs():
    response = client.get("/v1/genes/TTC34")
    assert response.status_code == 200
    genes = response.json()
    assert len(genes) > 0

    gene_response = GeneResponse(**genes)
    assert gene_response.gene is not None
    assert gene_response.gene.symbol is not None
    assert gene_response.gene.chr is not None
    assert gene_response.gene.min_bp is not None
    assert gene_response.gene.max_bp is not None
    assert gene_response.colocs is not None
    assert len(gene_response.colocs) == 0
    assert gene_response.variants is not None

def test_get_genes_with_colocs():
    response = client.get("/v1/genes/TTLL10")
    assert response.status_code == 200
    genes = response.json()
    assert len(genes) > 0

    gene_response = GeneResponse(**genes)
    assert gene_response.gene is not None
    assert gene_response.gene.symbol is not None
    assert gene_response.gene.chr is not None
    assert gene_response.gene.min_bp is not None
    assert gene_response.gene.max_bp is not None
    assert gene_response.colocs is not None

    for coloc in gene_response.colocs:
        assert coloc.id is not None
        assert coloc.study is not None
        assert coloc.chr is not None
        assert coloc.bp is not None
        assert coloc.min_p is not None



