from fastapi import APIRouter, HTTPException
from app.db.redis import RedisClient
from app.models.schemas import Study
import uuid

router = APIRouter()

@router.post("/", response_model=dict)
async def upload_gwas(gwas: Study):
    try:
        redis = RedisClient()
        unique_id = str(uuid.uuid4())

        redis.add_to_queue(redis.process_gwas_queue, {"gwas": gwas, "unique_id": unique_id})
        return {"unique_id": unique_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{uuid}", response_model=Study)
async def get_gwas(uuid: str):
    try:
        redis = RedisClient()
        gwas = redis.get_from_queue(redis.process_gwas_queue, uuid)
        return gwas
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
