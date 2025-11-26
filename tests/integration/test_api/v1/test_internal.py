from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_clear_cache(mock_redis_cache):
    response = client.post("v1/internal/clear-cache/all")
    assert response.status_code == 200

    assert response.json() == {"message": "All caches cleared"}

def test_clear_cache_studies(mock_redis_cache):
    response = client.post("v1/internal/clear-cache/studies")
    assert response.status_code == 200

    assert response.json() == {"message": "Studies cache cleared"}
