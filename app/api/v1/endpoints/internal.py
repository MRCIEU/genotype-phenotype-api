import traceback
from fastapi import APIRouter, HTTPException, Request

from app.logging_config import get_logger, time_endpoint
from app.rate_limiting import limiter, DEFAULT_RATE_LIMIT
from app.services.studies_service import StudiesService
from app.services.associations_service import AssociationsService

logger = get_logger(__name__)
router = APIRouter()


@router.post("/clear-cache/all", response_model=dict, include_in_schema=False)
@time_endpoint
@limiter.limit(DEFAULT_RATE_LIMIT)
async def clear_cache(request: Request):
    try:
        studies_service = StudiesService()
        studies_service.clear_cache()
        associations_service = AssociationsService()
        associations_service.clear_cache()
        return {"message": "All caches cleared"}
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in clear_cache: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/clear-cache/studies", response_model=dict, include_in_schema=False)
@time_endpoint
@limiter.limit(DEFAULT_RATE_LIMIT)
async def clear_cache_studies(request: Request):
    try:
        studies_service = StudiesService()
        studies_service.clear_cache()
        return {"message": "Studies cache cleared"}
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in clear_cache_studies: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rate-limiter", response_model=dict, include_in_schema=False)
@limiter.limit("3/minute")
async def rate_limiter(request: Request):
    """For testing rate limiting. Should block more than 2 calls per minute."""
    return {"success": True}
