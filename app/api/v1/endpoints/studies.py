from fastapi import APIRouter, HTTPException, Path
from app.db.duckdb import DuckDBClient
from app.models.schemas import Coloc, Study, StudyResponse, convert_duckdb_to_pydantic_model
from typing import List

router = APIRouter()

@router.get("/", response_model=List[Study])
async def get_studies() -> List[Study]:
    try:
        db = DuckDBClient()
        studies = db.get_studies()
        studies = convert_duckdb_to_pydantic_model(Study, studies)
        return studies
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{study_id}", response_model=StudyResponse)
async def get_study(study_id: str = Path(..., description="Study ID")) -> StudyResponse:
    try:
        db = DuckDBClient()
        study = db.get_study(study_id)
        if study is None:
            raise HTTPException(status_code=400, detail=f"Study {study_id} not found")
        colocs = db.get_all_colocs_for_study(study_id)

        study = convert_duckdb_to_pydantic_model(Study, study)
        colocs = convert_duckdb_to_pydantic_model(Coloc, colocs)

        return StudyResponse(study=study, colocs=colocs)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))