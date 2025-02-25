import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_get_studies():
    response = client.get("/v1/studies")
    assert response.status_code == 200
    studies = response.json()
    assert isinstance(studies, list)
    if len(studies) > 0:
        study = studies[0]
        assert "study_name" in study
        assert "trait" in study
        assert "data_type" in study 