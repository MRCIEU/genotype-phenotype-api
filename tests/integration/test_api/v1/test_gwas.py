from os import system
import os
import pytest
from unittest.mock import Mock
from fastapi.testclient import TestClient
from app.db.gwas_db import GwasDBClient
from app.main import app
from app.models.schemas import GwasStatus, TraitResponse
import json

client = TestClient(app)

guid = None

# @pytest.fixture(autouse=True)
# def setup_db():
#     gwas_db = GwasDBClient()
#     with gwas_db.connect() as conn:
#         conn.execute("DELETE FROM gwas_upload")
#         conn.execute("DELETE FROM study_extractions")
#         conn.execute("DELETE FROM colocalisations")

# @pytest.fixture(scope="module")
# def mock_redis_client(module_mocker):
#     mock = module_mocker.patch('app.db.redis.RedisClient')
#     mock_instance = Mock()
#     mock_instance.add_to_queue.return_value = None
#     mock_instance.process_gwas_queue = "process_gwas"
#     mock.return_value = mock_instance
#     return mock_instance

@pytest.fixture(scope="module")
def test_guid():
    with open('tests/test_data/test_upload.tsv.gz', 'rb') as f:
        request_data = {
            "reference_build": "GRCh38",
            "email": "ae@email.com",
            "name": "Example Study",
            "category": "continuous",
            "is_published": "false",
            "doi": None,
            "should_be_added": "false",
            "sample_size": "23423",
            "ancestry": "EUR",
            "column_names": {
                "chr": "CHR",
                "bp": "BP",
                "ea": "EA",
                "oa": "OA",
                "beta": "BETA",
                "se": "SE",
                "p": "P",
                "eaf": "EAF",
                "rsid": "RSID"
            }
        }
        
        response = client.post(
            "/v1/gwas/",
            data = {
                "request": json.dumps(request_data),
            },
            files = {"file": f} 
        )
 
    assert response.status_code == 200
    assert 'guid' in response.json()
    # mock_redis_client.add_to_queue.assert_called_once()
    return response.json()['guid']

# Sorry for the massive hack for resetting the database, couldn't think of a better way to reset the tests 
@pytest.fixture(scope="module", autouse=True)
def test_remove_all_data():
    yield
    system("git checkout tests/test_data/gwas_upload_small.db")

def test_get_gwas_not_found():
    response = client.get("/v1/gwas/nonexistent-guid")
    assert response.status_code == 404

def test_put_gwas(test_guid):
    with open('tests/test_data/update_gwas_payload.json', 'rb') as update_gwas_payload:
        update_gwas_payload = json.load(update_gwas_payload)
        response = client.put(f"/v1/gwas/{test_guid}", json=update_gwas_payload)
        
    assert response.status_code == 200
    assert response.json()['status'] == GwasStatus.COMPLETED.value

def test_put_gwas_not_found():
    with open('tests/test_data/update_gwas_payload.json', 'rb') as update_gwas_payload:
        update_gwas_payload = json.load(update_gwas_payload)
        response = client.put(f"/v1/gwas/bad-guid", json=update_gwas_payload)
        
    assert response.status_code == 404

def test_get_gwas(test_guid):
    response = client.get(f"/v1/gwas/{test_guid}")
    assert response.status_code == 200

    gwas_model = TraitResponse(**response.json())
    assert gwas_model.trait.guid == test_guid
    assert gwas_model.trait.status == GwasStatus.COMPLETED
    assert len(gwas_model.study_extractions) > 1
    assert len(gwas_model.upload_study_extractions) > 1
    assert len(gwas_model.colocs) > 1
