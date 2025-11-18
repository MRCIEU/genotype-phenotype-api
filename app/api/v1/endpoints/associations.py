from fastapi import APIRouter, HTTPException, Query
from typing import List
from app.logging_config import get_logger, time_endpoint
from app.services.associations_service import AssociationsService

logger = get_logger(__name__)
router = APIRouter()


@router.get("", response_model=dict)
@time_endpoint
async def get_associations(
    study_ids: List[int] = Query(None, description="List of study_ids to filter results"),
    snp_ids: List[int] = Query(None, description="List of snp_ids to filter results"),
) -> dict:
    association_service = AssociationsService()
    if study_ids is None or study_ids == [] or snp_ids is None or snp_ids == []:
        raise HTTPException(status_code=400, detail="Need at least one study_id and one snp_id to get associations")

    associations = association_service.get_associations_by_study_ids(snp_ids=snp_ids, study_ids=study_ids)
    return {"associations": associations}
