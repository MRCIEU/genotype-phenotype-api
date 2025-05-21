import traceback
from fastapi import APIRouter, HTTPException, Path
from app.db.studies_db import StudiesDBClient
from app.models.schemas import Coloc, Study, ExtendedStudyExtraction, TraitResponse, convert_duckdb_to_pydantic_model
from typing import List
from app.logging_config import get_logger, time_endpoint

logger = get_logger(__name__)
router = APIRouter()

@router.get("/", response_model=List[Study])
@time_endpoint
async def get_studies() -> List[Study]:
    try:
        db = StudiesDBClient()
        studies = db.get_studies()
        studies = convert_duckdb_to_pydantic_model(Study, studies)
        return studies
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in get_studies: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{study_id}", response_model=TraitResponse)
@time_endpoint
async def get_study(study_id: str = Path(..., description="Study ID")) -> TraitResponse:
    try:
        db = StudiesDBClient()
        study = db.get_study(study_id)
        if study is None:
            raise HTTPException(status_code=400, detail=f"Study {study_id} not found")
        colocs = db.get_all_colocs_for_study(study_id)

        study = convert_duckdb_to_pydantic_model(Study, study)
        study_extractions = db.get_study_extractions_for_study(study_id)
        study_extractions = convert_duckdb_to_pydantic_model(ExtendedStudyExtraction, study_extractions)

        if colocs is not None:
            colocs = convert_duckdb_to_pydantic_model(Coloc, colocs)
            study_extraction_ids = [coloc.study_extraction_id for coloc in colocs]
            filtered_studies = [s for s in study_extractions if s.id not in study_extraction_ids]
        else:
            filtered_studies = study_extractions

        return TraitResponse(trait=study, colocs=colocs, study_extractions=filtered_studies)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in get_study: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=traceback.format_exc())