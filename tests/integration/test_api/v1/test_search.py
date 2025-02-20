import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.schemas import SearchTerm

client = TestClient(app)

def test_get_search_options():
    response = client.get("/v1/search/options")
    assert response.status_code == 200
    search_options = response.json()
    assert isinstance(search_options, list)
    assert len(search_options) > 0

    for option in search_options:
        search_term = SearchTerm(**option)
        assert search_term.type is not None
        assert search_term.type_id is not None
        assert search_term.name is not None