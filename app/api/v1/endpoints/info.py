from fastapi import APIRouter, HTTPException, Request, Response
from app.db.ld_db import LdDBClient
from app.db.studies_db import StudiesDBClient
from app.models.schemas import Coloc, ExtendedVariant, Ld, SearchTerm, Variant, VariantResponse, VariantSearchResponse, convert_duckdb_to_pydantic_model
from typing import List

from app.services.cache_service import CacheService
from app.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()

@router.get("/study_metadata", response_model=StudyMetadata)
async def get_study_metadata():
    try:
        cache_service = CacheService()
        study_metadata = cache_service.get_study_metadata()
        return study_metadata
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in get_study_metadata: {e}")
        raise HTTPException(status_code=500, detail=str(e))
