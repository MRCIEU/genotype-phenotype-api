from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_bad_get_associations_query():
    response = client.get("v1/associations")
    assert response.status_code == 400


def test_get_associations_by_study_ids(snp_study_pairs_in_associations_db):
    study_ids = snp_study_pairs_in_associations_db["studies"]
    variant_ids = snp_study_pairs_in_associations_db["snps"]

    study_ids_param = "&".join([f"study_ids={study_id}" for study_id in study_ids])
    variant_ids_param = "&".join([f"variant_ids={variant_id}" for variant_id in variant_ids])

    response = client.get(f"v1/associations?{study_ids_param}&{variant_ids_param}")
    assert response.status_code == 200

    associations = response.json()["associations"]
    assert len(associations) > 2
