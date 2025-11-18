import traceback
from fastapi import APIRouter, HTTPException, Request
from app.models.schemas import GenePleiotropy, SnpPleiotropy, convert_duckdb_to_pydantic_model
from app.db.studies_db import StudiesDBClient
from app.models.schemas import (
    GenePleiotropyResponse,
    SnpPleiotropyResponse,
)
from app.rate_limiting import limiter, DEFAULT_RATE_LIMIT
from app.logging_config import get_logger, time_endpoint
from app.config import get_settings

settings = get_settings()
logger = get_logger(__name__)
router = APIRouter()


@router.get("/genes", response_model=GenePleiotropyResponse)
@time_endpoint
@limiter.limit(DEFAULT_RATE_LIMIT)
async def get_genes_pleiotropy(request: Request) -> GenePleiotropyResponse:
    try:
        studies_db = StudiesDBClient()
        genes_pleiotropy = studies_db.get_gene_pleiotropy_scores()
        genes_pleiotropy = convert_duckdb_to_pydantic_model(GenePleiotropy, genes_pleiotropy)
        return GenePleiotropyResponse(genes=genes_pleiotropy)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in get_study_sources: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=traceback.format_exc())


@router.get("/snps", response_model=SnpPleiotropyResponse)
@time_endpoint
@limiter.limit(DEFAULT_RATE_LIMIT)
async def get_snps_pleiotropy(request: Request) -> SnpPleiotropyResponse:
    try:
        studies_db = StudiesDBClient()
        snps_pleiotropy = studies_db.get_snp_pleiotropy_scores()
        snps_pleiotropy = convert_duckdb_to_pydantic_model(SnpPleiotropy, snps_pleiotropy)
        return SnpPleiotropyResponse(snps=snps_pleiotropy)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in get_study_metadata: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))
