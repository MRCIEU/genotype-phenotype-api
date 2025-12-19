from fastapi import APIRouter, HTTPException, UploadFile, Request, Form
import traceback
import uuid
import os
import hashlib
import sentry_sdk
import json

from app.config import get_settings
from app.db.studies_db import StudiesDBClient
from app.db.gwas_db import GwasDBClient
from app.db.redis import RedisClient
from app.logging_config import get_logger, time_endpoint
from app.models.schemas import (
    ExtendedStudyExtraction,
    ExtendedUploadColocGroup,
    GwasUpload,
    ProcessGwasRequest,
    GwasStatus,
    StudyDataType,
    UploadTraitResponse,
    UpdateGwasRequest,
    UploadStudyExtraction,
    convert_duckdb_to_pydantic_model,
)
from app.rate_limiting import limiter, DEFAULT_RATE_LIMIT
from app.services.gwas_upload_service import GwasUploadService

settings = get_settings()
router = APIRouter()

logger = get_logger(__name__)


@router.post("", response_model=GwasUpload)
@time_endpoint
@limiter.limit(DEFAULT_RATE_LIMIT)
async def upload_gwas(request: Request, request_body_str: str = Form(..., alias="request"), file: UploadFile = None):
    try:
        # Parse the request body from form data (JSON string)
        # The ProcessGwasRequest model validator handles json.loads() internally
        request_body = ProcessGwasRequest.model_validate(request_body_str)
        
        # redis = RedisClient()
        # is_allowed, recent_uploads = redis.update_user_upload(request_body.email)
        # if not is_allowed:
        #     raise HTTPException(
        #         status_code=429,
        #         detail=f"Too many upload attempts (limit 100/day). Current uploads in last 24h: {recent_uploads}"
        #     )

        sha256_hash = hashlib.sha256()
        file_path = os.path.join(settings.GWAS_DIR, f"{file.filename}")
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        with open(file_path, "wb") as buffer:
            while chunk := file.file.read(8192):
                buffer.write(chunk)
                sha256_hash.update(chunk)

        hash_bytes = sha256_hash.digest()[:16]
        file_guid = str(uuid.UUID(bytes=hash_bytes))

        os.makedirs(os.path.join(settings.GWAS_DIR, file_guid), exist_ok=True)
        file_location = os.path.join(settings.GWAS_DIR, file_guid, file.filename)
        os.rename(file_path, file_location)

        db = GwasDBClient()
        gwas = db.get_gwas_by_guid(file_guid)
        if gwas is not None:
            gwas = convert_duckdb_to_pydantic_model(GwasUpload, gwas)
            if gwas.status == GwasStatus.COMPLETED:
                logger.info(f"GWAS already exists: {file_guid}")
                return gwas
            else:
                db.delete_gwas_upload(file_guid)

        request_body.guid = file_guid
        request_body.status = GwasStatus.PROCESSING

        db = GwasDBClient()
        gwas = db.create_gwas_upload(request_body)
        gwas = convert_duckdb_to_pydantic_model(GwasUpload, gwas)

        redis_json = {
            "file_location": file_location,
            "metadata": request_body.model_dump(mode="json"),
        }

        redis = RedisClient()
        redis.add_to_queue(redis.process_gwas_queue, redis_json)

        return gwas
    except HTTPException as e:
        raise e
    except Exception as e:
        # Clean up file if there's an error
        if "file_path" in locals() and os.path.exists(file_path):
            os.remove(file_path)
        logger.error(f"Error: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{guid}")
@limiter.limit(DEFAULT_RATE_LIMIT)
async def update_gwas(
    request: Request,
    guid: str,
    update_gwas_request: UpdateGwasRequest,
):
    try:
        gwas_upload_db = GwasDBClient()
        studies_db = StudiesDBClient()
        gwas_upload_service = GwasUploadService()
        # email_service = EmailService()

        gwas = gwas_upload_db.get_gwas_by_guid(guid)
        if gwas is None:
            raise HTTPException(status_code=404, detail=f"Uploaded GWAS with GUID {guid} not found")
        gwas = convert_duckdb_to_pydantic_model(GwasUpload, gwas)

        if not update_gwas_request.success:
            updated_gwas = gwas_upload_service.update_gwas_failure(gwas, update_gwas_request)
            # await email_service.send_failure_email(gwas.email, guid)
            return updated_gwas

        updated_gwas = gwas_upload_service.update_gwas_success(gwas, update_gwas_request)
        # await email_service.send_results_email(gwas.email, guid)

        return updated_gwas
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{guid}", response_model=UploadTraitResponse)
@time_endpoint
@limiter.limit(DEFAULT_RATE_LIMIT)
async def get_gwas(request: Request, guid: str):
    try:
        studies_db = StudiesDBClient()
        gwas_upload_db = GwasDBClient()
        gwas = gwas_upload_db.get_gwas_by_guid(guid)
        if gwas is None:
            raise HTTPException(status_code=404, detail="GWAS not found")

        gwas = convert_duckdb_to_pydantic_model(GwasUpload, gwas)

        if gwas.status != GwasStatus.COMPLETED:
            return UploadTraitResponse(
                trait=gwas,
                study_extractions=None,
                upload_study_extractions=None,
                colocs=None,
            )

        colocalisations = gwas_upload_db.get_colocs_by_gwas_upload_id(gwas.id)
        colocalisations = convert_duckdb_to_pydantic_model(ExtendedUploadColocGroup, colocalisations)

        upload_study_extractions = gwas_upload_db.get_study_extractions_by_gwas_upload_id(gwas.id)
        upload_study_extractions = convert_duckdb_to_pydantic_model(UploadStudyExtraction, upload_study_extractions)

        existing_study_extraction_ids = [
            coloc.existing_study_extraction_id
            for coloc in colocalisations
            if coloc.existing_study_extraction_id is not None
        ]
        existing_study_extractions = studies_db.get_study_extractions_by_id(existing_study_extraction_ids)
        existing_study_extractions = convert_duckdb_to_pydantic_model(
            ExtendedStudyExtraction, existing_study_extractions
        )

        for coloc in colocalisations:
            if coloc.existing_study_extraction_id is not None:
                existing_study_extraction = next(
                    (se for se in existing_study_extractions if se.id == coloc.existing_study_extraction_id),
                    None,
                )

                coloc.trait_name = existing_study_extraction.trait_name
                coloc.trait_category = existing_study_extraction.trait_category
                coloc.data_type = existing_study_extraction.data_type
                coloc.tissue = existing_study_extraction.tissue
                coloc.cis_trans = existing_study_extraction.cis_trans
            else:
                coloc.trait_name = gwas.name
                coloc.data_type = StudyDataType.phenotype.name
                coloc.tissue = None
                coloc.cis_trans = None

        return UploadTraitResponse(
            gwas=gwas,
            study_extractions=existing_study_extractions,
            upload_study_extractions=upload_study_extractions,
            coloc_groups=colocalisations,
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in get_gwas: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))
