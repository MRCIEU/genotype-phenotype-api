from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from app.db.redis import RedisClient
from app.models.schemas import ProcessGwasResponse, StudyResponse, ProccessGwasRequest
import uuid
import os
from app.config import get_settings
import shutil
import json
from typing import Annotated

settings = get_settings()
router = APIRouter()

# @router.post("/", response_model=ProcessGwasResponse)
# async def upload_gwas(
#     file: UploadFile = File(...),
#     metadata: Annotated[ProccessGwasRequest, Form()] = Form(...),
# ):
#     try:
#         # Parse metadata if it's a string, or use directly if already parsed
#         if isinstance(metadata, str):
#             metadata_dict = json.loads(metadata)
#             metadata = ProccessGwasRequest(**metadata_dict)
        
#         redis = RedisClient()
#         guid = str(uuid.uuid4())
        
#         # Create directory if it doesn't exist
#         os.makedirs(settings.GWAS_DIR, exist_ok=True)
        
#         # Save file to disk
#         file_path = os.path.join(settings.GWAS_DIR, f"{guid}.gwas")
#         with open(file_path, "wb") as buffer:
#             shutil.copyfileobj(file.file, buffer)
        
#         # Close the file
#         await file.close()

#         # Add to processing queue
#         request_json = {
#             "guid": guid,
#             "file_path": file_path,
#             "file_name": file.filename,
#             "metadata": metadata.model_dump()  # Convert Pydantic model to dict
#         }
#         redis.add_to_queue(redis.process_gwas_queue, request_json)
        
#         return ProcessGwasResponse(guid=guid, processed=False)
        
#     except json.JSONDecodeError:
#         if 'file_path' in locals() and os.path.exists(file_path):
#             os.remove(file_path)
#         raise HTTPException(status_code=400, detail="Invalid JSON in metadata")
#     except Exception as e:
#         # Clean up file if there's an error
#         if 'file_path' in locals() and os.path.exists(file_path):
#             os.remove(file_path)
#         raise HTTPException(status_code=500, detail=str(e))

# @router.get("/{guid}", response_model=StudyResponse)
# async def get_gwas(guid: str):
#     try:
#         redis = RedisClient()
#         gwas = redis.get_from_queue(redis.process_gwas_queue, guid)
#         return gwas
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
