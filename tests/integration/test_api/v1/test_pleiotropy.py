from fastapi.testclient import TestClient
from app.main import app
from app.models.schemas import GenePleiotropyResponse, SnpPleiotropyResponse

client = TestClient(app)

pleiotropy_score_fields = [
    "distinct_trait_categories_cis_gws",
    "distinct_trait_categories_cis_all",
    "distinct_trait_categories_cis_trans_gws",
    "distinct_trait_categories_cis_trans_all",
    "distinct_protein_coding_genes_cis_gws",
    "distinct_protein_coding_genes_cis_all",
    "distinct_protein_coding_genes_cis_trans_gws",
    "distinct_protein_coding_genes_cis_trans_all",
]

# IGSF9 and variant 80732 have different gws and all scores in studies_small
igsf9_pleiotropy = {
    "distinct_trait_categories": 4,
    "distinct_protein_coding_genes": 8,
    "distinct_trait_categories_cis_gws": 2,
    "distinct_trait_categories_cis_all": 4,
    "distinct_trait_categories_cis_trans_gws": 2,
    "distinct_trait_categories_cis_trans_all": 4,
    "distinct_protein_coding_genes_cis_gws": 6,
    "distinct_protein_coding_genes_cis_all": 8,
    "distinct_protein_coding_genes_cis_trans_gws": 6,
    "distinct_protein_coding_genes_cis_trans_all": 8,
}
# NELL2 has different cis and cis + trans scores in studies_small
nell2_pleiotropy = {
    "distinct_trait_categories": 10,
    "distinct_protein_coding_genes": 59,
    "distinct_trait_categories_cis_gws": 1,
    "distinct_trait_categories_cis_all": 1,
    "distinct_trait_categories_cis_trans_gws": 10,
    "distinct_trait_categories_cis_trans_all": 10,
    "distinct_protein_coding_genes_cis_gws": 2,
    "distinct_protein_coding_genes_cis_all": 2,
    "distinct_protein_coding_genes_cis_trans_gws": 57,
    "distinct_protein_coding_genes_cis_trans_all": 59,
}
gene_pleiotropy_by_symbol = {"IGSF9": igsf9_pleiotropy, "NELL2": nell2_pleiotropy}
variant_80732_pleiotropy = {
    "distinct_trait_categories": 4,
    "distinct_protein_coding_genes": 0,
    "distinct_trait_categories_cis_gws": 3,
    "distinct_trait_categories_cis_all": 4,
    "distinct_trait_categories_cis_trans_gws": 3,
    "distinct_trait_categories_cis_trans_all": 4,
    "distinct_protein_coding_genes_cis_gws": 0,
    "distinct_protein_coding_genes_cis_all": 0,
    "distinct_protein_coding_genes_cis_trans_gws": 0,
    "distinct_protein_coding_genes_cis_trans_all": 0,
}


def test_get_genes_pleiotropy():
    response = client.get("v1/pleiotropy/genes")
    print(response.json())
    assert response.status_code == 200
    genes_pleiotropy = response.json()
    genes_pleiotropy = GenePleiotropyResponse(**genes_pleiotropy)
    assert len(genes_pleiotropy.genes) > 0

    for gene in genes_pleiotropy.genes:
        assert gene.gene_id is not None
        assert gene.gene is not None
        assert gene.distinct_trait_categories is not None
        assert gene.distinct_protein_coding_genes is not None
        for field in pleiotropy_score_fields:
            assert getattr(gene, field) is not None, f"{field} should not be None"
        # The unsuffixed scores are kept for API compatibility, using the cis + trans, all results scores
        assert gene.distinct_trait_categories == gene.distinct_trait_categories_cis_trans_all
        assert gene.distinct_protein_coding_genes == gene.distinct_protein_coding_genes_cis_trans_all

    for symbol, expected in gene_pleiotropy_by_symbol.items():
        gene = next(gene for gene in genes_pleiotropy.genes if gene.gene == symbol)
        assert gene.model_dump(include=set(expected)) == expected


def test_get_snps_pleiotropy():
    response = client.get("v1/pleiotropy/snps")
    assert response.status_code == 200
    snps_pleiotropy = response.json()
    snps_pleiotropy = SnpPleiotropyResponse(**snps_pleiotropy)
    assert len(snps_pleiotropy.snps) > 0

    for snp in snps_pleiotropy.snps:
        assert snp.variant_id is not None
        assert snp.display_snp is not None
        assert snp.distinct_trait_categories is not None
        assert snp.distinct_protein_coding_genes is not None
        for field in pleiotropy_score_fields:
            assert getattr(snp, field) is not None, f"{field} should not be None"
        assert snp.distinct_trait_categories == snp.distinct_trait_categories_cis_trans_all
        assert snp.distinct_protein_coding_genes == snp.distinct_protein_coding_genes_cis_trans_all

    variant = next(snp for snp in snps_pleiotropy.snps if snp.variant_id == 80732)
    assert variant.model_dump(include=set(variant_80732_pleiotropy)) == variant_80732_pleiotropy


def test_get_gene_includes_pleiotropy_scores():
    for symbol, expected in gene_pleiotropy_by_symbol.items():
        response = client.get(f"/v1/genes/{symbol}")
        assert response.status_code == 200
        gene = response.json()["gene"]
        assert {field: gene[field] for field in expected} == expected


def test_get_genes_includes_pleiotropy_scores():
    response = client.get("/v1/genes")
    assert response.status_code == 200
    genes = response.json()["genes"]
    for symbol, expected in gene_pleiotropy_by_symbol.items():
        gene = next(gene for gene in genes if gene["gene"] == symbol)
        assert {field: gene[field] for field in expected} == expected


def test_get_variant_includes_pleiotropy_scores():
    response = client.get("/v1/variants/80732")
    assert response.status_code == 200
    variant = response.json()["variant"]
    assert {field: variant[field] for field in variant_80732_pleiotropy} == variant_80732_pleiotropy
