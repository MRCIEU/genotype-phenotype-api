import io
import zipfile
from fastapi.testclient import TestClient
from app.main import app
from app.db.studies_db import StudiesDBClient
from app.models.schemas import (
    ExtendedColocGroup,
    ExtendedStudyExtraction,
    Variant,
    VariantResponse,
    GetVariantsResponse,
    convert_duckdb_to_pydantic_model,
)
from app.services.summary_stat_service import SummaryStatService


client = TestClient(app)


def test_get_variants_by_variants(variants_in_studies_db):
    variant_ids = list(variants_in_studies_db.keys())
    response = client.get(f"/v1/variants?variants={variant_ids[0]}")
    assert response.status_code == 200
    data = response.json()
    variants = data["variants"]
    assert len(variants) > 0

    for row in variants:
        variant_model = Variant(**row)
        assert variant_model.id is not None
        assert variant_model.snp is not None
        assert variant_model.display_snp is not None
        assert variant_model.chr is not None
        assert variant_model.bp is not None
        assert variant_model.ea is not None
        assert variant_model.oa is not None
        assert variant_model.ref_allele is not None
        assert variant_model.associations is None


def test_get_variants_by_rsids(variants_in_studies_db):
    rsids = [variant["rsid"] for variant in variants_in_studies_db.values()]
    response = client.get(f"/v1/variants?variants={rsids[0]}&variants={rsids[1]}")
    assert response.status_code == 200
    data = response.json()
    variants = data["variants"]
    assert len(variants) > 0
    for row in variants:
        variant_model = Variant(**row)
        assert variant_model.id is not None
        assert variant_model.snp is not None
        assert variant_model.display_snp is not None
        assert variant_model.chr is not None
        assert variant_model.bp is not None
        assert variant_model.ea is not None
        assert variant_model.oa is not None
        assert variant_model.ref_allele is not None
        assert variant_model.associations is None


def test_get_variants_mixed_variant_id_and_rsid(variants_in_studies_db):
    """Variants param auto-detects variant_ids vs rsids - mixed list works."""
    variant_ids = list(variants_in_studies_db.keys())
    rsids = [variant["rsid"] for variant in variants_in_studies_db.values()]
    response = client.get(f"/v1/variants?variants={variant_ids[0]}&variants={rsids[1]}")
    assert response.status_code == 200
    data = response.json()
    variants = data["variants"]
    assert len(variants) >= 1
    for row in variants:
        variant_model = Variant(**row)
        assert variant_model.id is not None
        assert variant_model.snp is not None
        assert variant_model.display_snp is not None
        assert variant_model.chr is not None
        assert variant_model.bp is not None
        assert variant_model.ea is not None
        assert variant_model.oa is not None
        assert variant_model.ref_allele is not None
        assert variant_model.associations is None


def test_get_variants_by_grange(variants_in_grange):
    response = client.get(f"/v1/variants?grange={variants_in_grange}")
    assert response.status_code == 200
    data = response.json()
    variants = data["variants"]
    assert len(variants) > 0
    for row in variants:
        variant_model = Variant(**row)
        for field in variant_model.model_fields:
            optional_fields = [
                "canonical",
                "gene_id",
                "associations",
                "distinct_trait_categories",
                "distinct_protein_coding_genes",
                "distinct_trait_categories_cis_gws",
                "distinct_trait_categories_cis_all",
                "distinct_trait_categories_cis_trans_gws",
                "distinct_trait_categories_cis_trans_all",
                "distinct_protein_coding_genes_cis_gws",
                "distinct_protein_coding_genes_cis_all",
                "distinct_protein_coding_genes_cis_trans_gws",
                "distinct_protein_coding_genes_cis_trans_all",
            ]
            if field not in optional_fields:
                assert getattr(variant_model, field) is not None, f"{field} should not be None"


def test_get_variants_expand_not_allowed_with_grange(variants_in_grange):
    response = client.get(f"/v1/variants?grange={variants_in_grange}&expand=true")
    assert response.status_code == 400
    assert "expand" in response.json()["detail"].lower()


def test_get_variants_expand_with_associations(variants_in_studies_db):
    variant_ids = list(variants_in_studies_db.keys())
    response = client.get(f"/v1/variants?variants={variant_ids[0]}&expand=true&include_associations=true")
    assert response.status_code == 200
    data = response.json()
    variants_response = GetVariantsResponse(**data)
    assert len(variants_response.variants) > 0
    for variant in variants_response.variants:
        assert variant.id is not None
    assert variants_response.coloc_groups is not None
    assert len(variants_response.coloc_groups) > 0
    assert variants_response.rare_results is not None
    assert len(variants_response.rare_results) == 0
    assert variants_response.study_extractions is not None
    assert len(variants_response.study_extractions) > 0
    assert variants_response.associations is not None
    assert len(variants_response.associations) > 0


def test_get_variant_by_id(variants_in_studies_db):
    variant_ids = list(variants_in_studies_db.keys())
    response = client.get(f"/v1/variants/{variant_ids[0]}")
    assert response.status_code == 200
    variant = response.json()
    assert variant is not None
    variant_response = VariantResponse(**variant)
    assert variant_response.variant is not None
    assert variant_response.coloc_groups is not None
    assert variant_response.ld_proxy_variants is None

    for coloc in variant_response.coloc_groups:
        assert isinstance(coloc, ExtendedColocGroup)
        assert coloc.coloc_group_id is not None
        assert coloc.study_extraction_id is not None
        assert coloc.chr is not None
        assert coloc.bp is not None
        assert coloc.min_p is not None
        if coloc.association is not None:
            assert isinstance(coloc.association, dict)


def test_get_variant_by_rsid(variants_in_studies_db):
    """get_variant accepts rsid (auto-detected like get_variants)."""
    for variant_id, data in variants_in_studies_db.items():
        rsid = data.get("rsid")
        if rsid:
            response = client.get(f"/v1/variants/{rsid}")
            assert response.status_code == 200
            variant_response = VariantResponse(**response.json())
            assert variant_response.variant is not None
            assert variant_response.variant.id == int(variant_id)
            return


def test_get_variant_by_id_with_ld_proxy_fallback(variants_in_studies_db):
    """When variant has no coloc/rare, returns ld_proxy_variants (variants in high LD with results)."""
    variant_id_no_results = list(variants_in_studies_db.keys())[1]
    response = client.get(f"/v1/variants/{variant_id_no_results}?rsquared_threshold=0.9")
    assert response.status_code == 200
    data = response.json()
    variant_response = VariantResponse(**data)
    assert variant_response.variant is not None
    assert variant_response.variant.id == int(variant_id_no_results)
    print(variant_response.ld_proxy_variants)
    assert variant_response.ld_proxy_variants is not None
    for proxy_variant in variant_response.ld_proxy_variants:
        assert isinstance(proxy_variant, Variant)
        assert proxy_variant.id is not None


def test_get_variant_by_id_with_coloc_pairs(variant_coloc_pair_merge):
    mid = variant_coloc_pair_merge
    response = client.get(
        f"/v1/variants/{mid['variant_id']}?include_coloc_pairs=true&h4_threshold={mid['h4_threshold']}",
    )
    assert response.status_code == 200
    variant = response.json()
    assert variant is not None
    variant_response = VariantResponse(**variant)
    assert variant_response.variant is not None
    assert variant_response.coloc_groups is not None

    for coloc in variant_response.coloc_groups:
        assert isinstance(coloc, ExtendedColocGroup)
        if coloc.association is not None:
            assert isinstance(coloc.association, dict)
    assert variant_response.coloc_pairs is not None
    assert len(variant_response.coloc_pairs) > 0
    for coloc_pair in variant_response.coloc_pairs:
        assert isinstance(coloc_pair, dict)

    se_ids = {e.id for e in variant_response.study_extractions}
    assert mid["partner_study_extraction_id"] in se_ids
    pair_ids = set()
    for row in variant_response.coloc_pairs:
        for k in ("study_extraction_a_id", "study_extraction_b_id"):
            v = row.get(k)
            if v is not None:
                pair_ids.add(v)
    assert mid["partner_study_extraction_id"] in pair_ids


def test_get_variant_summary_stats(variants_in_studies_db, mock_oci_service):
    variant_ids = list(variants_in_studies_db.keys())

    response = client.get(f"/v1/variants/{variant_ids[0]}/summary-stats")

    assert response.status_code == 200
    assert mock_oci_service.get_file.call_count == variants_in_studies_db[variant_ids[0]]["num_studies"]
    assert response.headers["Content-Type"] == "application/zip"
    assert response.headers["Content-Disposition"] == f"attachment; filename=variant_{variant_ids[0]}_summary_stats.zip"

    zip_data = io.BytesIO(response.content)
    with zipfile.ZipFile(zip_data, "r") as zf:
        namelist = zf.namelist()
        assert len(namelist) == variants_in_studies_db[variant_ids[0]]["num_studies"]
        file_content = zf.read(namelist[0])
        assert file_content


def test_get_study_summary_stats_uses_file_for_rare_variant_studies(variants_in_studies_db, mock_oci_service):
    mock_oci_service.get_file.reset_mock()
    variant_id = int(list(variants_in_studies_db.keys())[0])
    study_extractions = StudiesDBClient().get_study_extractions_for_variant(variant_id)
    common_extraction = convert_duckdb_to_pydantic_model(ExtendedStudyExtraction, study_extractions)[0]

    # studies_small has a rare exome study (54929) but none of its study extractions, so build one
    rare_study_id = 54929
    rare_extraction = common_extraction.model_copy(
        update={
            "id": -1,
            "study_id": rare_study_id,
            "file": "study/ukb-wes-az-00008986/rare.tsv.gz",
            "file_with_lbfs": None,
        }
    )
    common_extraction_without_file = common_extraction.model_copy(
        update={"id": -2, "study_id": -2, "file_with_lbfs": None}
    )

    zip_buffer = SummaryStatService().get_study_summary_stats(
        [common_extraction, rare_extraction, common_extraction_without_file]
    )

    requested_object_names = [call.args[0] for call in mock_oci_service.get_file.call_args_list]
    assert requested_object_names == [
        common_extraction.file_with_lbfs.replace("//", "/"),
        "study/ukb-wes-az-00008986/rare.tsv.gz",
    ]
    with zipfile.ZipFile(zip_buffer, "r") as zf:
        assert zf.namelist() == [
            f"{common_extraction.study_id}_with_lbfs.tsv.gz",
            f"{rare_study_id}.tsv.gz",
        ]
