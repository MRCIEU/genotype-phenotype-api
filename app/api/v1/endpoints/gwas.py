from fastapi import APIRouter, HTTPException
from app.db.redis import RedisClient
from app.models.schemas import ProccessGwasRequest, ProcessGwasResponse, StudyResponse
import uuid
import os
from app.config import get_settings

settings = get_settings()
router = APIRouter()

@router.post("/", response_model=ProcessGwasResponse)
async def upload_gwas(gwas_request: ProccessGwasRequest):
    try:
        redis = RedisClient()
        gwas_request.guid = str(uuid.uuid4())

        # get existing processed gwases, if the file hash is already in the database, return the existing guid
        existing_gwas = os.path.join(settings.GWAS_DIR, gwas_request.gwas_file_hash)
        if os.path.exists(existing_gwas):
            return ProcessGwasResponse(guid=existing_gwas, processed=True)

        gwas_request_json = gwas_request.model_dump_json()

        redis.add_to_queue(redis.process_gwas_queue, gwas_request_json)
        return ProcessGwasResponse(guid=gwas_request.guid, processed=False)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{guid}", response_model=StudyResponse)
async def get_gwas(guid: str):
    try:
        redis = RedisClient()
        gwas = redis.get_from_queue(redis.process_gwas_queue, guid)
        return gwas
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
