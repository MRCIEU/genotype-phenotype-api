from fastapi import FastAPI, HTTPException, Query
import duckdb
from typing import List, Optional
from pydantic import BaseModel
# Get variables from settings.py
from app.settings import DB_PATH, ANALYTICS_KEY
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
    conn = duckdb.connect(DB_PATH, read_only=True)
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
    regional_prob: Optional[int] = None
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
    conn = duckdb.connect(DB_PATH, read_only=True)
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


@app.get("/coloc/ld_block", response_model=List[Coloc])
async def list_coloc(ld_block: str = Query(None, description="Block identifier to filter results")):
    """Retrieve all the coloc results for the LD block"""
    conn = duckdb.connect(DB_PATH, read_only=True)
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
    conn = duckdb.connect(DB_PATH, read_only=True)
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
    conn = duckdb.connect(DB_PATH, read_only=True)

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

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    conn = duckdb.connect(DB_PATH, read_only=True)
    conn.execute("SELECT 1").fetchone()
    conn.close()
    return {"status": "healthy"}

