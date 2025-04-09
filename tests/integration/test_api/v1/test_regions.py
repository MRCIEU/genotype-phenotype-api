import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.schemas import Coloc, GeneMetadata, RegionResponse

client = TestClient(app)

def test_get_region():
    response = client.get("/v1/regions/1309")
    assert response.status_code == 200
    region = response.json()
    region_model = RegionResponse(**region)
    assert region_model.region.chr is not None
    assert region_model.region.start is not None
    assert region_model.region.end is not None
    assert region_model.region.ancestry is not None

    for coloc in region_model.colocs:
        assert isinstance(coloc, Coloc)
        assert coloc.coloc_group_id is not None
        assert coloc.study_extraction_id is not None
        assert coloc.chr is not None
        assert coloc.bp is not None
        assert coloc.min_p is not None
        assert coloc.posterior_prob is not None

    for gene_metadata in region_model.genes:
        assert isinstance(gene_metadata, GeneMetadata)
        assert gene_metadata.symbol is not None
        assert gene_metadata.chr is not None