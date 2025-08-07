from fastapi import APIRouter, HTTPException, UploadFile
import traceback
import uuid
import os
import hashlib
import sentry_sdk

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
    StudyExtraction,
    TraitResponse,
    UpdateGwasRequest,
    UploadStudyExtraction,
    convert_duckdb_to_pydantic_model,
)

settings = get_settings()
router = APIRouter()

logger = get_logger(__name__)


@router.post("", response_model=GwasUpload)
@time_endpoint
async def upload_gwas(request: ProcessGwasRequest, file: UploadFile):
    try:
        # redis = RedisClient()
        # is_allowed, recent_uploads = redis.update_user_upload(request.email)
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
        # TODO: change this to FAILED once we are done testing
        if gwas is not None:
            gwas = convert_duckdb_to_pydantic_model(GwasUpload, gwas)
            if gwas.status == GwasStatus.COMPLETED:
                logger.info(f"GWAS already exists: {file_guid}")
                return gwas
            else:
                db.delete_gwas_upload(file_guid)

        request.guid = file_guid
        request.status = GwasStatus.PROCESSING

        db = GwasDBClient()
        gwas = db.create_gwas_upload(request)
        gwas = convert_duckdb_to_pydantic_model(GwasUpload, gwas)

        redis_json = {
            "file_location": file_location,
            "metadata": request.model_dump(mode="json"),
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
async def update_gwas(
    guid: str,
    update_gwas_request: UpdateGwasRequest,
):
    try:
        gwas_upload_db = GwasDBClient()
        studies_db = StudiesDBClient()

        gwas = gwas_upload_db.get_gwas_by_guid(guid)
        if gwas is None:
            raise HTTPException(status_code=404, detail=f"Uploaded GWAS with GUID {guid} not found")
        gwas = convert_duckdb_to_pydantic_model(GwasUpload, gwas)

        if not update_gwas_request.success:
            error_context = {
                "guid": guid,
                "failure_reason": update_gwas_request.failure_reason,
                "user_email": gwas.email if hasattr(gwas, "email") else "unknown",
            }

            logger.error(
                f"GWAS processing failed: {update_gwas_request.failure_reason}",
                extra=error_context,
            )

            sentry_sdk.set_context("gwas_upload", error_context)
            sentry_sdk.capture_message(
                f"GWAS processing failed: {update_gwas_request.failure_reason}",
                level="error",
            )

            gwas.status = GwasStatus.FAILED
            gwas.failure_reason = update_gwas_request.failure_reason
            updated_gwas = gwas_upload_db.update_gwas_status(guid, GwasStatus.FAILED)
            updated_gwas = convert_duckdb_to_pydantic_model(GwasUpload, updated_gwas)
            # email_service = EmailService()
            # await email_service.send_failure_email(gwas.email, guid)
            return updated_gwas

        ld_blocks = [study.ld_block for study in update_gwas_request.study_extractions]
        existing_ld_blocks = studies_db.get_ld_blocks_by_ld_block(ld_blocks)

        coloc_snps = [coloc.snp_id for coloc in update_gwas_request.coloc_groups]
        coloc_snps = studies_db.get_variants_by_snp_strings(coloc_snps)

        study_extractions_snps = [study_extractions.snp for study_extractions in update_gwas_request.study_extractions]
        study_extractions_snps = studies_db.get_variants_by_snp_strings(study_extractions_snps)

        for i, study in enumerate(update_gwas_request.study_extractions):
            study.gwas_upload_id = gwas.id
            study.snp_id = study_extractions_snps[i][0] if study_extractions_snps[i] else None
            study.ld_block_id = existing_ld_blocks[i][0] if existing_ld_blocks[i] else None

        study_extractions = gwas_upload_db.populate_study_extractions(update_gwas_request.study_extractions)
        study_extractions = convert_duckdb_to_pydantic_model(UploadStudyExtraction, study_extractions)

        study_id_map = {study.unique_study_id: study for study in update_gwas_request.study_extractions}

        unique_study_ids = [coloc.unique_study_id for coloc in update_gwas_request.coloc_results]
        existing_study_extractions = studies_db.get_study_extractions_by_unique_study_id(unique_study_ids)
        existing_study_extractions = convert_duckdb_to_pydantic_model(StudyExtraction, existing_study_extractions)
        for i, coloc in enumerate(update_gwas_request.coloc_results):
            coloc.gwas_upload_id = gwas.id
            coloc.snp_id = coloc_snps[i][0] if coloc_snps[i] else None

            if coloc.unique_study_id in study_id_map:
                upload_study_extraction = study_id_map.get(coloc.unique_study_id)
                coloc.upload_study_extraction_id = upload_study_extraction.id
                coloc.chr = upload_study_extraction.chr
                coloc.bp = upload_study_extraction.bp
                coloc.min_p = upload_study_extraction.min_p
                coloc.ld_block = upload_study_extraction.ld_block
            else:
                coloc.existing_study_extraction_id = existing_study_extractions[i].id
                coloc.study_id = existing_study_extractions[i].study_id
                coloc.chr = existing_study_extractions[i].chr
                coloc.bp = existing_study_extractions[i].bp
                coloc.min_p = existing_study_extractions[i].min_p
                coloc.ld_block = existing_study_extractions[i].ld_block
                coloc.gene = existing_study_extractions[i].gene
                coloc.gene_id = existing_study_extractions[i].gene_id

        gwas_upload_db.populate_colocs(update_gwas_request.coloc_results)
        updated_gwas = gwas_upload_db.update_gwas_status(guid, GwasStatus.COMPLETED)
        updated_gwas = convert_duckdb_to_pydantic_model(GwasUpload, updated_gwas)

        # email_service = EmailService()
        # await email_service.send_results_email(gwas.email, guid)

        return updated_gwas
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{guid}", response_model=TraitResponse)
@time_endpoint
async def get_gwas(guid: str):
    try:
        studies_db = StudiesDBClient()
        gwas_upload_db = GwasDBClient()
        gwas = gwas_upload_db.get_gwas_by_guid(guid)
        if gwas is None:
            raise HTTPException(status_code=404, detail="GWAS not found")

        gwas = convert_duckdb_to_pydantic_model(GwasUpload, gwas)

        if gwas.status != GwasStatus.COMPLETED:
            return TraitResponse(
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

        return TraitResponse(
            trait=gwas,
            study_extractions=existing_study_extractions,
            upload_study_extractions=upload_study_extractions,
            colocs=colocalisations,
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in get_gwas: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))
