import traceback
from fastapi import APIRouter, HTTPException, Query, Request

from app.db.ld_db import LdDBClient
from app.db.studies_db import StudiesDBClient
from app.models.schemas import Ld, Lds, Variant, convert_duckdb_to_pydantic_model
from typing import List
from app.logging_config import get_logger, time_endpoint
from app.rate_limiting import limiter, DEFAULT_RATE_LIMIT
from app.db.utils import run_sync

logger = get_logger(__name__)
router = APIRouter()


@router.get(
    "/matrix",
    response_model=Lds,
    summary="Get LD matrix for variants",
    description="Returns pairwise LD (r²) values between the requested variants.",
)
@time_endpoint
@limiter.limit(DEFAULT_RATE_LIMIT)
async def get_matrix(
    request: Request,
    variants: List[str] = Query(None, description="List of variants to filter results"),
    variant_ids: List[int] = Query(None, description="List of variant_ids to filter results"),
):
    def _run():
        try:
            ld_db = LdDBClient()
            studies_db = StudiesDBClient()
            resolved_variant_ids = variant_ids
            if variants:
                variant_annotations = studies_db.get_variants(variant_prefixes=variants)
                variant_annotations = convert_duckdb_to_pydantic_model(Variant, variant_annotations)
                resolved_variant_ids = [variant_annotation.id for variant_annotation in variant_annotations]

            if not resolved_variant_ids:
                raise HTTPException(status_code=400, detail="No SNPs found provided in the request")
            ld_matrix = ld_db.get_ld_matrix(resolved_variant_ids)
            print(resolved_variant_ids)
            print(ld_matrix)
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

    return await run_sync(_run)


@router.get(
    "/proxies",
    response_model=Lds,
    summary="Get LD proxies for variants",
    description="Returns LD proxy relationships for the requested variants.",
)
@time_endpoint
@limiter.limit(DEFAULT_RATE_LIMIT)
async def get_proxies(
    request: Request,
    variants: List[str] = Query(None, description="List of variants to filter results"),
    variant_ids: List[int] = Query(None, description="List of variant_ids to filter results"),
    rsquared_threshold: float = Query(0.8, description="R squared threshold for LD proxies"),
):
    def _run():
        try:
            if rsquared_threshold < 0.8 or rsquared_threshold > 1:
                raise HTTPException(status_code=400, detail="R squared threshold must be between 0.8 and 1")

            ld_db = LdDBClient()
            studies_db = StudiesDBClient()
            resolved_variant_ids = variant_ids
            if variants:
                variant_annotations = studies_db.get_variants(variant_prefixes=variants)
                variant_annotations = convert_duckdb_to_pydantic_model(Variant, variant_annotations)
                resolved_variant_ids = [variant_annotation.id for variant_annotation in variant_annotations]

            if not resolved_variant_ids:
                raise HTTPException(status_code=400, detail="No SNPs found provided in the request")

            ld_proxies = ld_db.get_ld_proxies(resolved_variant_ids, rsquared_threshold)
            if ld_proxies is None or len(ld_proxies) == 0:
                raise HTTPException(
                    status_code=404, detail=f"LD proxies for variant_ids {resolved_variant_ids} not found"
                )

            response = convert_duckdb_to_pydantic_model(Ld, ld_proxies)
            response = Lds(lds=response)
            return response

        except HTTPException as e:
            raise e
        except Exception as e:
            logger.error(f"Error in get_proxies: {e}\n{traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=str(e))

    return await run_sync(_run)
