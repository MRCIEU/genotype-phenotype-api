from fastapi import APIRouter, HTTPException
from app.models.schemas import GPMapMetadata, convert_duckdb_to_pydantic_model

from app.services.cache_service import DBCacheService
from app.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()

@router.get("/gpmap_metadata", response_model=GPMapMetadata)
async def get_gpmap_metadata():
    try:
        cache_service = DBCacheService()
        metadata = cache_service.get_gpmap_metadata()
        return metadata
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in get_study_metadata: {e}")
        raise HTTPException(status_code=500, detail=str(e))
