from fastapi import APIRouter, HTTPException, Path
from app.db.duckdb import DuckDBClient
from app.models.schemas import * 
from typing import List

from app.services.cache_service import CacheService

router = APIRouter()

@router.get("/{symbol}", response_model=GeneResponse)
async def get_gene(symbol: str = Path(..., description="Gene Symbol")) -> GeneResponse:
    try:
        cache_service = CacheService()
        tissues = cache_service.get_tissues()

        db = DuckDBClient()
        gene = db.get_gene(symbol)
        gene = convert_duckdb_to_pydantic_model(Gene, gene)

        genes = cache_service.get_gene_ranges()
        genes = convert_duckdb_to_pydantic_model(Gene, genes)

        genes_in_region = [g for g in genes
                          if g.chr == gene.chr
                          and g.min_bp <= gene.min_bp+1000000 and g.max_bp >= gene.max_bp-1000000
                          and g.symbol != symbol
                          ]
        gene.genes_in_region = genes_in_region

        colocs = db.get_all_colocs_for_gene(symbol)
        colocs = convert_duckdb_to_pydantic_model(Coloc, colocs)

        studies = db.get_study_extractions_in_region(gene.chr, gene.min_bp, gene.max_bp, symbol)
        studies = convert_duckdb_to_pydantic_model(StudyExtaction, studies)

        variant_ids = [coloc.candidate_snp for coloc in colocs]
        variants = db.get_variants(variants=variant_ids)
        variants = convert_duckdb_to_pydantic_model(Variant, variants)

        return GeneResponse(tissues=tissues, gene=gene, colocs=colocs, variants=variants, study_extractions=studies)
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))