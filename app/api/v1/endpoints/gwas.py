import shutil
from fastapi import APIRouter, HTTPException, Form, UploadFile, File, Depends
import uuid
import os
import hashlib

from app.config import get_settings
from app.db.duckdb import DuckDBClient
from app.db.gwas_db import GwasDBClient
from app.db.redis import RedisClient
from app.models.schemas import GwasUpload, StudyResponse, ProcessGwasRequest, GwasState, GwasStatus, convert_duckdb_to_pydantic_model

settings = get_settings()
router = APIRouter()

@router.post("/", response_model=GwasUpload)
async def upload_gwas(
    request: ProcessGwasRequest,
    file: UploadFile
):
    try:
        print(request)
        sha256_hash = hashlib.sha256()
        file_path = os.path.join(settings.GWAS_DIR, f"{file.filename}")
        
        with open(file_path, "wb") as buffer:
            while chunk := file.file.read(8192):
                buffer.write(chunk)
                sha256_hash.update(chunk)
        
        hash_bytes = sha256_hash.digest()[:16]
        file_guid = str(uuid.UUID(bytes=hash_bytes))

        os.makedirs(os.path.join(settings.GWAS_DIR, file_guid), exist_ok=True)
        os.rename(file_path, os.path.join(settings.GWAS_DIR, file_guid, file.filename))

        db = GwasDBClient()
        gwas = db.get_gwas(file_guid)
        if gwas is not None:
            print("GWAS already exists")
            gwas = convert_duckdb_to_pydantic_model(GwasUpload, gwas)
            return gwas
        
        request.guid = file_guid
        request.status = GwasStatus.PROCESSING

        db = GwasDBClient()
        gwas = db.upload_gwas(request)
        gwas = convert_duckdb_to_pydantic_model(GwasUpload, gwas)

        redis_json = {
            "guid": file_guid,
            "file_path": file_path,
            "metadata": request.model_dump(mode="json")
        }

        redis = RedisClient()
        redis.add_to_queue(redis.process_gwas_queue, redis_json)

        return gwas 
        
    except Exception as e:
        # Clean up file if there's an error
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{guid}")
async def update_gwas(guid: str):
    try:
        db = GwasDBClient()
        db.update_gwas_status(guid, GwasStatus.COMPLETED)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{guid}", response_model=GwasUpload)
async def get_gwas(guid: str):
    try:
        db = GwasDBClient()
        gwas = db.get_gwas(guid)
        if gwas is None:
            raise HTTPException(status_code=404, detail="GWAS not found")

        gwas = gwas + (GwasStatus.PROCESSING,)
        gwas = convert_duckdb_to_pydantic_model(GwasUpload, gwas)
        
        if gwas.status == GwasStatus.COMPLETED:
            #TODO: get gwas data
            return gwas
        else:
            return gwas

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
