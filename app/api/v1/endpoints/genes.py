from fastapi import APIRouter, HTTPException, Path
from app.db.studies_db import StudiesDBClient
from app.models.schemas import * 
from typing import List

from app.services.cache_service import CacheService

router = APIRouter()

@router.get("/{symbol}", response_model=GeneResponse)
async def get_gene(symbol: str = Path(..., description="Gene Symbol")) -> GeneResponse:
    try:
        cache_service = CacheService()
        tissues = cache_service.get_tissues()

        db = StudiesDBClient()
        gene = db.get_gene(symbol)

        if gene is None:
            raise HTTPException(status_code=404, detail=f"Gene {symbol} not found")
        gene = convert_duckdb_to_pydantic_model(Gene, gene)

        genes = cache_service.get_gene_ranges()
        genes = convert_duckdb_to_pydantic_model(Gene, genes)

        genes_in_region = [g for g in genes
                          if g.chr == gene.chr
                          and g.min_bp <= gene.min_bp+1000000 and g.max_bp >= gene.max_bp-1000000
                          and g.symbol != symbol
                          ]
        gene.genes_in_region = genes_in_region

        studies = db.get_study_extractions_in_region(gene.chr, gene.min_bp, gene.max_bp, symbol)

        if studies is not None:
            studies = convert_duckdb_to_pydantic_model(ExtendedStudyExtraction, studies)

        colocs = db.get_all_colocs_for_gene(symbol)
        if colocs is not None:
            colocs = convert_duckdb_to_pydantic_model(Coloc, colocs)
            study_extraction_ids = [coloc.study_extraction_id for coloc in colocs]
            filtered_studies = [s for s in studies if s.id not in study_extraction_ids]

            snp_ids = [coloc.snp_id for coloc in colocs]
            variants = db.get_variants(snp_ids=snp_ids)
            variants = convert_duckdb_to_pydantic_model(Variant, variants)
        else:
            variants = []
            filtered_studies = []

        return GeneResponse(tissues=tissues, gene=gene, colocs=colocs, variants=variants, study_extractions=filtered_studies)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))