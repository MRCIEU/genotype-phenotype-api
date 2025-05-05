import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.schemas import GPMapMetadata, Ld

client = TestClient(app)

def test_get_gpmap_metadata():
    response = client.get("/v1/info/gpmap_metadata")
    assert response.status_code == 200

    gpmap_metadata = response.json()
    metadata = GPMapMetadata(**gpmap_metadata)
    assert gpmap_metadata is not None
    assert metadata.num_common_studies is not None
    assert metadata.num_rare_studies is not None
    assert metadata.num_molecular_studies is not None
    assert metadata.num_coloc_groups is not None
    assert metadata.num_causal_variants is not None