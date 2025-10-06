from fastapi.testclient import TestClient
from app.main import app
from app.models.schemas import GPMapMetadata, StudySource

from app.config import get_settings

client = TestClient(app)


def test_get_version():
    response = client.get("/v1/info/version")
    assert response.status_code == 200
    version = response.json()
    assert version is not None
    assert version["version"] == get_settings().VERSION


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


def test_get_study_sources():
    response = client.get("/v1/info/study_sources")
    assert response.status_code == 200

    study_source_response = response.json()
    assert study_source_response is not None
    study_sources = [StudySource(**source) for source in study_source_response["sources"]]
    assert len(study_sources) > 0
    for source in study_sources:
        assert source.name is not None
        assert source.source is not None
        assert source.doi is not None
