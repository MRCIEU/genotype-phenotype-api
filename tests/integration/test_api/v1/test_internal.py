from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_clear_cache(mock_redis_cache):
    response = client.post("v1/internal/clear-cache")
    assert response.status_code == 200

    assert response.json() == {"message": "Cache cleared"}
