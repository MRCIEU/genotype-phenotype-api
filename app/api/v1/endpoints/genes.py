from fastapi import APIRouter, HTTPException, Path
from app.db.studies_db import StudiesDBClient
from app.models.schemas import * 
from typing import List

from app.services.cache_service import DBCacheService
from app.logging_config import get_logger, time_endpoint

logger = get_logger(__name__)

router = APIRouter()

@router.get("/{symbol}", response_model=GeneResponse)
@time_endpoint
async def get_gene(symbol: str = Path(..., description="Gene Symbol")) -> GeneResponse:
    try:
        cache_service = DBCacheService()
        tissues = cache_service.get_tissues()

        db = StudiesDBClient()
        gene = db.get_gene(symbol)

        if gene is None:
            raise HTTPException(status_code=404, detail=f"Gene {symbol} not found")
        gene = convert_duckdb_to_pydantic_model(Gene, gene)

        genes = cache_service.get_gene_ranges()

        genes_in_region = [g for g in genes
                          if g.chr == gene.chr
                          and g.min_bp <= gene.min_bp+1000000 and g.max_bp >= gene.max_bp-1000000
                          and g.symbol != symbol
                          ]
        gene.genes_in_region = genes_in_region

        study_extractions = db.get_study_extractions_in_region(gene.chr, gene.min_bp, gene.max_bp, symbol)
        if study_extractions is not None:
            study_extractions = convert_duckdb_to_pydantic_model(ExtendedStudyExtraction, study_extractions)
            study_extraction_ids = [s.id for s in study_extractions]

        region_colocs = db.get_all_colocs_for_study_extraction_ids(study_extraction_ids)
        gene_colocs = db.get_all_colocs_for_gene(symbol)
        colocs = region_colocs + gene_colocs
        if colocs is not None:
            colocs = convert_duckdb_to_pydantic_model(Coloc, colocs)
            study_extraction_ids = [coloc.study_extraction_id for coloc in colocs]
            filtered_studies = [s for s in study_extractions if s.id not in study_extraction_ids]

            snp_ids = [coloc.snp_id for coloc in colocs]
            variants = db.get_variants(snp_ids=snp_ids)
            variants = convert_duckdb_to_pydantic_model(Variant, variants)
        else:
            variants = []
            filtered_studies = []

        study_rare_results = db.get_rare_results_for_study_extraction_ids(study_extraction_ids)
        gene_rare_results = db.get_rare_results_for_gene(symbol)
        rare_results = study_rare_results + gene_rare_results
        # TODO: Remove this once we have fixed the rare results in the pipeline
        rare_results = [r for r in rare_results if r[2] is not None]
        if rare_results is not None:
            rare_results = convert_duckdb_to_pydantic_model(RareResult, rare_results)

        return GeneResponse(tissues=tissues, gene=gene, colocs=colocs, variants=variants, study_extractions=filtered_studies, rare_results=rare_results)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in get_gene: {e}")
        raise HTTPException(status_code=500, detail=str(e))