from os import system
import pytest
from fastapi.testclient import TestClient
from app.main import app
import json
from app.models.schemas import GwasStatus, UploadTraitResponse, GwasUpload

client = TestClient(app)

guid = None


# Sorry for the massive hack for resetting the database, couldn't think of a better way to reset the tests
@pytest.fixture(scope="module", autouse=True)
def test_remove_all_data():
    yield
    system("git checkout tests/test_data/gwas_upload_small.db")


@pytest.fixture(scope="module")
def test_guid(mock_redis, mock_oci_service):
    with open("tests/test_data/test_upload.tsv.gz", "rb") as f:
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
            "p_value_threshold": 1.5e-4,
            "column_names": {
                "chr": "CHR",
                "bp": "BP",
                "ea": "EA",
                "oa": "OA",
                "beta": "BETA",
                "se": "SE",
                "p": "P",
                "eaf": "EAF",
                "rsid": "RSID",
            },
        }

        response = client.post(
            "/v1/gwas/",
            data={
                "request": json.dumps(request_data),
            },
            files={"file": f},
        )

    print(response.json())
    assert response.status_code == 200
    assert "guid" in response.json()
    mock_redis.lpush.assert_called_once()
    mock_oci_service.upload_file.assert_called_once()
    return response.json()["guid"]


def test_get_gwas_not_found():
    response = client.get("/v1/gwas/nonexistent-guid")
    assert response.status_code == 404


def test_put_gwas_failure(test_guid, mock_email_service):
    with open("tests/test_data/update_gwas_failure_payload.json", "rb") as update_gwas_payload:
        update_gwas_payload = json.load(update_gwas_payload)
        response = client.put(f"/v1/gwas/{test_guid}", json=update_gwas_payload)

    print(response.json())
    assert response.status_code == 200
    assert response.json()["status"] == GwasStatus.FAILED.value
    mock_email_service.send_failure_email.assert_called_once()


def test_put_gwas_not_found():
    with open("tests/test_data/update_gwas_success_payload.json", "rb") as update_gwas_payload:
        update_gwas_payload = json.load(update_gwas_payload)
        response = client.put("/v1/gwas/bad-guid", json=update_gwas_payload)

    assert response.status_code == 404


def test_put_gwas_success(test_guid, mock_email_service):
    with open("tests/test_data/update_gwas_success_payload.json", "rb") as update_gwas_payload:
        update_gwas_payload = json.load(update_gwas_payload)
        response = client.put(f"/v1/gwas/{test_guid}", json=update_gwas_payload)

    print(response.json())
    assert response.status_code == 200
    gwas_model = GwasUpload(**response.json())
    assert gwas_model.status == GwasStatus.COMPLETED
    mock_email_service.send_results_email.assert_called_once()


def test_get_gwas(test_guid):
    response = client.get(f"/v1/gwas/{test_guid}")
    print(response.json())
    assert response.status_code == 200

    with open("tests/test_data/update_gwas_success_payload.json", "rb") as update_gwas_payload:
        update_gwas_payload = json.load(update_gwas_payload)

    gwas_model = UploadTraitResponse(**response.json())
    assert gwas_model.trait.guid == test_guid
    assert gwas_model.trait.status == GwasStatus.COMPLETED
    assert len(gwas_model.coloc_groups) == len(update_gwas_payload["coloc_groups"])
    assert len(gwas_model.coloc_pairs) == len(update_gwas_payload["coloc_pairs"])
    assert len(gwas_model.study_extractions) >= 1
    assert len(gwas_model.upload_study_extractions) >= 1
