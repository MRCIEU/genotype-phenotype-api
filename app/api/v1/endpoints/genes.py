from fastapi import APIRouter, HTTPException, Path
from app.db.duckdb import DuckDBClient
from app.models.schemas import * 
from typing import List

from app.services.cache_service import CacheService

router = APIRouter()

@router.get("/", response_model=List[Gene])
async def get_genes() -> List[Gene]:
    try:
        cache_service = CacheService()
        genes = cache_service.get_genes()
        genes = convert_duckdb_to_pydantic_model(Gene, genes)
        return genes
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{symbol}", response_model=GeneResponse)
async def get_gene(symbol: str = Path(..., description="Gene Symbol")) -> GeneResponse:
    try:
        db = DuckDBClient()
        gene = db.get_gene(symbol)
        colocs = db.get_all_colocs_for_gene(symbol)
        colocs = convert_duckdb_to_pydantic_model(Coloc, colocs)
        gene = convert_duckdb_to_pydantic_model(Gene, gene)

        studies = db.get_study_extractions_in_region(gene.chr, gene.min_bp, gene.max_bp, symbol)
        studies = convert_duckdb_to_pydantic_model(StudyExtaction, studies)

        variant_ids = [coloc.candidate_snp for coloc in colocs]
        variants = db.get_variants(variants=variant_ids)
        variants = convert_duckdb_to_pydantic_model(Variant, variants)

        return GeneResponse(gene=gene, colocs=colocs, variants=variants, study_extractions=studies)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))