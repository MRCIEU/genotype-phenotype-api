# import pytest
# from fastapi.testclient import TestClient
# from app.main import app
# from app.models.schemas import Ld

# client = TestClient(app)

# def test_get_ld_proxy():
#     response = client.get("/v1/ld/proxies?variants=7:102472533_A_G&variants=7:99912611_A_C")
#     assert response.status_code == 200
#     ld_proxy = response.json()
#     assert len(ld_proxy) > 0
#     for row in ld_proxy:
#         ld_model = Ld(**row)
#         assert ld_model.lead is not None
#         assert ld_model.variant is not None
#         assert ld_model.r is not None
#         assert ld_model.ld_block is not None

# def test_get_ld_matrix():
#     response = client.get("/v1/ld/matrix?variants=7:102472533_A_G&variants=7:99912611_A_C")
#     assert response.status_code == 200
#     ld_matrix = response.json()
#     assert len(ld_matrix) > 0
#     for row in ld_matrix:
#         ld_model = Ld(**row)
#         assert ld_model.lead is not None
#         assert ld_model.variant is not None
#         assert ld_model.r is not None
#         assert ld_model.ld_block is not None