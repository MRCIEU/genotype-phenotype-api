import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.schemas import GwasStatus
import os
import json

client = TestClient(app)

@pytest.fixture
def test_files():
    # Create test file paths
    gwas_file = "tests/test_data/test.tsv.gz"
    coloc_file = "tests/test_data/coloc.tsv"
    extracted_file = "tests/test_data/extracted.tsv"
    
    # Create test files with minimal content
    with open(coloc_file, 'w') as f:
        f.write("snp\tp_value\tbeta\tse\n")
        f.write("rs123\t0.05\t0.1\t0.02\n")
    
    with open(extracted_file, 'w') as f:
        f.write("unique_study_id\tother_column\n")
        f.write("study1\tvalue1\n")
    
    yield {
        'gwas_file': gwas_file,
        'coloc_file': coloc_file,
        'extracted_file': extracted_file
    }
    
    # Cleanup
    os.remove(coloc_file)
    os.remove(extracted_file)

def test_post_gwas(test_files):
    # Prepare test data
    with open(test_files['gwas_file'], 'rb') as f:
        files = {
            'file': ('test.tsv.gz', f, 'application/gzip')
        }
        data = {
            'request': json.dumps({
                'trait_name': 'Test Trait',
                'sample_size': 1000,
                'ancestry': 'EUR',
                'study_type': 'continuous',
                'is_published': False,
                'doi': '',
                'permanent': False,
                'column_names': {
                    'chr': 'CHR',
                    'bp': 'BP',
                    'ea': 'EA',
                    'oa': 'OA',
                    'beta': 'BETA',
                    'se': 'SE',
                    'pval': 'P',
                    'eaf': 'EAF',
                    'rsid': 'RSID'
                }
            })
        }
        
        response = client.post("/api/v1/gwas/", files=files, data=data)
        
    assert response.status_code == 200
    assert 'guid' in response.json()

def test_get_gwas():
    # First create a GWAS upload
    response = test_post_gwas(test_files)
    guid = response.json()['guid']
    
    # Then test getting it
    response = client.get(f"/api/v1/gwas/{guid}")
    assert response.status_code == 200
    assert response.json()['guid'] == guid
    assert response.json()['status'] == GwasStatus.PROCESSING.value

def test_get_gwas_not_found():
    response = client.get("/api/v1/gwas/nonexistent-guid")
    assert response.status_code == 404

def test_put_gwas(test_files):
    # First create a GWAS upload
    response = test_post_gwas(test_files)
    guid = response.json()['guid']
    
    # Then test updating it
    with open(test_files['coloc_file'], 'rb') as coloc_f, \
         open(test_files['extracted_file'], 'rb') as extracted_f:
        
        files = {
            'coloc_file': ('coloc.tsv', coloc_f, 'text/tab-separated-values'),
            'extracted_studies_file': ('extracted.tsv', extracted_f, 'text/tab-separated-values')
        }
        
        response = client.put(f"/api/v1/gwas/{guid}", files=files)
        
    assert response.status_code == 200
    assert response.json()['status'] == GwasStatus.COMPLETE.value

def test_put_gwas_not_found(test_files):
    with open(test_files['coloc_file'], 'rb') as coloc_f, \
         open(test_files['extracted_file'], 'rb') as extracted_f:
        
        files = {
            'coloc_file': ('coloc.tsv', coloc_f, 'text/tab-separated-values'),
            'extracted_studies_file': ('extracted.tsv', extracted_f, 'text/tab-separated-values')
        }
        
        response = client.put("/api/v1/gwas/nonexistent-guid", files=files)
        
    assert response.status_code == 404

@pytest.fixture(autouse=True)
def cleanup():
    # Setup - nothing needed
    yield
    # Cleanup - remove any test data
    import shutil
    if os.path.exists("data"):
        shutil.rmtree("data")