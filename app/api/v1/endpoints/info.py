import traceback
from fastapi import APIRouter, HTTPException
from app.db.studies_db import StudiesDBClient
from app.models.schemas import (
    ContactRequest,
    GPMapMetadata,
    GetStudySourcesResponse,
    StudySource,
    convert_duckdb_to_pydantic_model,
)

from app.services.studies_service import StudiesService
from app.logging_config import get_logger, time_endpoint
from app.services.email_service import EmailService
from app.config import get_settings

settings = get_settings()
logger = get_logger(__name__)
router = APIRouter()

@router.get("/version", response_model=str)
@time_endpoint
async def get_version():
    return settings.VERSION

@router.get("/study_sources", response_model=GetStudySourcesResponse)
@time_endpoint
async def get_study_sources() -> GetStudySourcesResponse:
    try:
        studies_db = StudiesDBClient()
        sources = studies_db.get_study_sources()
        sources = convert_duckdb_to_pydantic_model(StudySource, sources)
        return GetStudySourcesResponse(sources=sources)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in get_study_sources: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=traceback.format_exc())


@router.get("/gpmap_metadata", response_model=GPMapMetadata)
@time_endpoint
async def get_gpmap_metadata():
    try:
        studies_service = StudiesService()
        metadata = studies_service.get_gpmap_metadata()
        return metadata
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in get_study_metadata: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/contact")
@time_endpoint
async def contact(request: ContactRequest):
    try:
        email_service = EmailService()
        await email_service.send_contact_email(request.email, request.reason, request.message)
    except HTTPException as e:
        logger.error(f"Error in contact: {e}\n{traceback.format_exc()}")
        raise e
    except Exception as e:
        logger.error(f"Error in contact: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))
