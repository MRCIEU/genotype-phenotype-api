from fastapi.testclient import TestClient
from app.main import app
from app.models.schemas import GenePleiotropyResponse, SnpPleiotropyResponse

client = TestClient(app)


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


def test_get_snps_pleiotropy():
    response = client.get("v1/pleiotropy/snps")
    assert response.status_code == 200
    snps_pleiotropy = response.json()
    snps_pleiotropy = SnpPleiotropyResponse(**snps_pleiotropy)
    assert len(snps_pleiotropy.snps) > 0

    for snp in snps_pleiotropy.snps:
        assert snp.snp_id is not None
        assert snp.display_snp is not None
        assert snp.distinct_trait_categories is not None
        assert snp.distinct_protein_coding_genes is not None
