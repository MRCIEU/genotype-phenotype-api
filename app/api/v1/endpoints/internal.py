import traceback
from fastapi import APIRouter, HTTPException
from app.logging_config import get_logger, time_endpoint
from app.services.studies_service import StudiesService
from app.services.associations_service import AssociationsService

logger = get_logger(__name__)
router = APIRouter()


@router.post("/clear-cache", response_model=dict, include_in_schema=False)
@time_endpoint
async def clear_cache():
    try:
        studies_service = StudiesService()
        studies_service.clear_cache()
        associations_service = AssociationsService()
        associations_service.clear_cache()
        return {"message": "Cache cleared"}
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in clear_cache: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))
