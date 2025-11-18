import traceback
from fastapi import APIRouter, HTTPException, Query, Request

from app.db.ld_db import LdDBClient
from app.db.studies_db import StudiesDBClient
from app.models.schemas import Ld, Lds, Variant, convert_duckdb_to_pydantic_model
from typing import List
from app.logging_config import get_logger, time_endpoint
from app.rate_limiting import limiter, DEFAULT_RATE_LIMIT

logger = get_logger(__name__)
router = APIRouter()


@router.get("/matrix", response_model=Lds)
@time_endpoint
@limiter.limit(DEFAULT_RATE_LIMIT)
async def get_matrix(
    request: Request,
    variants: List[str] = Query(None, description="List of variants to filter results"),
    snp_ids: List[int] = Query(None, description="List of snp_ids to filter results"),
):
    try:
        ld_db = LdDBClient()
        studies_db = StudiesDBClient()
        if variants:
            snp_annotations = studies_db.get_variants(variant_prefixes=variants)
            snp_annotations = convert_duckdb_to_pydantic_model(Variant, snp_annotations)
            snp_ids = [snp_annotation.id for snp_annotation in snp_annotations]

        if not snp_ids:
            raise HTTPException(status_code=400, detail="No SNPs found provided in the request")

        ld_matrix = ld_db.get_ld_matrix(snp_ids)
        if ld_matrix is None or len(ld_matrix) == 0:
            raise HTTPException(status_code=404, detail=f"LD matrix for variants {variants} not found")

        response = convert_duckdb_to_pydantic_model(Ld, ld_matrix)
        response = Lds(lds=response)
        return response

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in get_matrix: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/proxies", response_model=Lds)
@time_endpoint
@limiter.limit(DEFAULT_RATE_LIMIT)
async def get_proxies(
    request: Request,
    variants: List[str] = Query(None, description="List of variants to filter results"),
    snp_ids: List[int] = Query(None, description="List of snp_ids to filter results"),
):
    try:
        ld_db = LdDBClient()
        studies_db = StudiesDBClient()
        if variants:
            snp_annotations = studies_db.get_variants(variant_prefixes=variants)
            snp_annotations = convert_duckdb_to_pydantic_model(Variant, snp_annotations)
            snp_ids = [snp_annotation.id for snp_annotation in snp_annotations]

        ld_proxies = ld_db.get_ld_proxies(snp_ids)
        if ld_proxies is None:
            raise HTTPException(status_code=404, detail=f"LD proxies for snp_ids {snp_ids} not found")

        response = convert_duckdb_to_pydantic_model(Ld, ld_proxies)
        response = Lds(lds=response)
        return response

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in get_proxies: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))
