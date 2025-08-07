from fastapi.testclient import TestClient
from app.main import app
from app.models.schemas import ColocGroup, Gene, RareResult, RegionResponse, Variant

client = TestClient(app)


def test_get_region():
    response = client.get("/v1/regions/1309")
    region = response.json()
    assert response.status_code == 200
    region_model = RegionResponse(**region)
    assert region_model.region.chr is not None
    assert region_model.region.start is not None
    assert region_model.region.stop is not None
    assert region_model.region.ancestry is not None

    for coloc in region_model.coloc_groups:
        assert isinstance(coloc, ColocGroup)
        assert coloc.coloc_group_id is not None
        assert coloc.study_extraction_id is not None
        assert coloc.chr is not None
        assert coloc.bp is not None
        assert coloc.min_p is not None

    for gene in region_model.genes_in_region:
        assert isinstance(gene, Gene)

    for rare_result in region_model.rare_results:
        assert isinstance(rare_result, RareResult)

    for variant in region_model.variants:
        assert isinstance(variant, Variant)

    for tissue in region_model.tissues:
        assert isinstance(tissue, str)
