from fastapi import FastAPI, HTTPException, Query
import duckdb
from typing import List, Optional
from pydantic import BaseModel
# Get variables from settings.py
from app.settings import DB_PROCESSED_PATH, DB_ASSOCS_PATH, ANALYTICS_KEY
from api_analytics.fastapi import Analytics

app = FastAPI(
    title="GPMap API",
    description="API for querying genetic studies data",
    version="0.0.0:9000"
)
app.add_middleware(Analytics, ANALYTICS_KEY)

def create_response_model(model: BaseModel, results):
    return [model(**{field: row[idx] for idx, field in enumerate(model.__fields__.keys())}) for row in results]


class Study(BaseModel):
    data_type: str
    data_format: str
    source: str
    study_name: str
    trait: str
    ancestry: Optional[str] = None
    sample_size: Optional[int] = None
    category: Optional[str] = None
    study_location: str
    extracted_location: str
    reference_build: str
    p_value_threshold: float
    variant_type: Optional[str] = None
    gene: Optional[str] = None
    probe: Optional[str] = None
    tissue: Optional[str] = None

@app.get("/studies", response_model=List[Study])
async def list_studies():
    """Retrieve all studies from the database."""
    conn = duckdb.connect(DB_PROCESSED_PATH, read_only=True)
    results = conn.execute("""
        SELECT *
        FROM studies_processed
    """).fetchall()
    conn.close()

    response = create_response_model(Study, results)
    return response


class Coloc(BaseModel):
    iteration: Optional[int] = None
    traits: Optional[str] = None
    posterior_prob: Optional[float] = None
    regional_prob: Optional[float] = None
    candidate_snp: Optional[str] = None
    posterior_explained_by_snp: Optional[float] = None
    dropped_trait: Optional[bool] = None
    id: Optional[int] = None
    study: Optional[str] = None
    chr: Optional[int] = None
    bp: Optional[int] = None
    min_p: Optional[float] = None
    cis_trans: Optional[str] = None
    ld_block: Optional[str] = None
    known_gene: Optional[str] = None

@app.get("/coloc/study", response_model=List[Coloc])
async def list_coloc(study: str = Query(None, description="Study identifier to filter results")):
    """Retrieve all coloc regions that contain the study"""
    conn = duckdb.connect(DB_PROCESSED_PATH, read_only=True)
    query = """
    SELECT * 
    FROM coloc
    WHERE id IN (
        SELECT id
        FROM coloc
        WHERE study IN (?)
    )"""
    results = conn.execute(query, (study,)).fetchall()
    conn.close()
    response = create_response_model(Coloc, results)
    return response



class Variants(BaseModel):
    SNP: Optional[str] = None
    CHR: Optional[int] = None
    BP: Optional[int] = None
    EA: Optional[str] = None
    OA: Optional[str] = None
    Gene: Optional[str] = None
    Feature_type: Optional[str] = None
    Consequence: Optional[str] = None
    cDNA_position: Optional[str] = None
    CDS_position: Optional[str] = None
    Protein_position: Optional[str] = None
    Amino_acids: Optional[str] = None
    Codons: Optional[str] = None
    RSID: Optional[str] = None
    impact: Optional[str] = None
    symbol: Optional[str] = None
    biotype: Optional[str] = None
    strand: Optional[int] = None
    canonical: Optional[str] = None
    ld_block: Optional[str] = None

@app.post("/variants/rsids", response_model=List[Variants])
async def list_variants(rsids: List[str]):
    """Retrieve all variants with the given rsids"""
    conn = duckdb.connect(DB_PROCESSED_PATH, read_only=True)
    query = """
    SELECT * 
    FROM variant_annotations
    WHERE RSID IN (?)"""
    formatted_rsids = ','.join(f"'{rsid}'" for rsid in rsids)
    query = query.replace('?', formatted_rsids)
    results = conn.execute(query).fetchall()
    conn.close()
    response = create_response_model(Variants, results)
    return response

@app.get("/variants/rsids", response_model=List[Variants])
async def list_variants(rsids: str = Query(None, description="Comma separated list of rsids")):
    """Retrieve all variants with the given rsids"""
    conn = duckdb.connect(DB_PROCESSED_PATH, read_only=True)
    query = """
    SELECT * 
    FROM variant_annotations
    WHERE RSID IN (?)"""
    formatted_rsids = ','.join(f"'{rsid}'" for rsid in rsids.split(","))
    query = query.replace('?', formatted_rsids)
    results = conn.execute(query).fetchall()
    conn.close()
    response = create_response_model(Variants, results)
    return response

@app.get("/coloc/ld_block", response_model=List[Coloc])
async def list_coloc(ld_block: str = Query(None, description="Block identifier to filter results")):
    """Retrieve all the coloc results for the LD block"""
    conn = duckdb.connect(DB_PROCESSED_PATH, read_only=True)
    query = """
    SELECT * 
    FROM coloc
    WHERE id IN (
        SELECT id 
        FROM coloc
        WHERE ld_block IN (?)
    )"""
    results = conn.execute(query, (ld_block,)).fetchall()
    conn.close()
    response = create_response_model(Coloc, results)
    return response


@app.get("/coloc/variant", response_model=List[Coloc])
async def list_coloc(variant: str = Query(None, description="Block identifier to filter results")):
    """Retrieve all the coloc results for a variant in chr:pos_a1_a2 format"""
    conn = duckdb.connect(DB_PROCESSED_PATH, read_only=True)
    query = """
    SELECT * 
    FROM coloc
    WHERE id IN (
        SELECT id 
        FROM coloc
        WHERE candidate_snp IN (?)
    )"""
    results = conn.execute(query, (variant,)).fetchall()
    conn.close()
    response = create_response_model(Coloc, results)
    return response

@app.get("/coloc/genomicrange", response_model=List[Coloc])
async def list_coloc(genomicrange: str = Query(None, description="Genomic range identifier to filter results")):
    """Retrieve all the coloc results in a genomic range given in chr:start-end format"""
    conn = duckdb.connect(DB_PROCESSED_PATH, read_only=True)

    chrom, position = genomicrange.split(":")
    p1, p2 = position.split("-")
    p1, p2 = int(p1), int(p2)

    query = """
    SELECT * 
    FROM coloc
    WHERE id IN (
        SELECT id 
        FROM coloc
        WHERE chr = (?) AND bp BETWEEN (?) AND (?)
    )"""
    results = conn.execute(query, (chrom, p1, p2)).fetchall()
    conn.close()
    response = create_response_model(Coloc, results)
    return response

class Ld(BaseModel):
    lead: str
    variant: str
    r: float
    ld_block: str

@app.post("/ldmatrix", response_model=List[Ld])
async def list_ldmatrix(variants: List[str]):
    """Retrieve the LD matrix for the given variants"""
    conn = duckdb.connect(DB_PROCESSED_PATH, read_only=True)
    query = """
    SELECT * FROM 
        (FROM ld
        WHERE lead IN (?)
        )
        WHERE variant IN (?) AND variant > lead
        """
    formatted_variants = ','.join(f"'{variant}'" for variant in variants)
    query = query.replace('?', formatted_variants)
    results = conn.execute(query).fetchall()
    conn.close()
    response = create_response_model(Ld, results)
    return response

@app.post("/ldproxy", response_model=List[Ld])
async def list_ldmatrix(variants: List[str]):
    """Retrieve the LD proxies for a given set of variants in varid format"""
    conn = duckdb.connect(DB_PROCESSED_PATH, read_only=True)
    query = """
    SELECT * FROM ld
    WHERE variant IN (?) AND abs(r2) > 0.894"""
    formatted_variants = ','.join(f"'{variant}'" for variant in variants)
    query = query.replace('?', formatted_variants)
    print(query)
    results = conn.execute(query).fetchall()
    conn.close()
    response = create_response_model(Ld, results)
    return response


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    conn = duckdb.connect(DB_PROCESSED_PATH, read_only=True)
    conn.execute("SELECT 1").fetchone()
    conn.close()
    conn = duckdb.connect(DB_ASSOCS_PATH, read_only=True)
    conn.execute("SELECT 1").fetchone()
    conn.close()
    return {"status": "healthy"}

