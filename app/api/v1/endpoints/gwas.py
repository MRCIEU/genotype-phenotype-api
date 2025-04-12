import shutil
from fastapi import APIRouter, HTTPException, UploadFile
import uuid
import os
import hashlib
from typing import List

from app.config import get_settings
from app.db.studies_db import StudiesDBClient
from app.db.gwas_db import GwasDBClient
from app.db.redis import RedisClient
from app.models.schemas import GwasUpload, GwasUploadResponse, ProcessGwasRequest, GwasStatus, StudyExtraction, UploadColoc, UploadStudyExtraction, convert_duckdb_to_pydantic_model

settings = get_settings()
router = APIRouter()

@router.post("/", response_model=GwasUpload)
async def upload_gwas(
    request: ProcessGwasRequest,
    file: UploadFile
):
    try:
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
            print("GWAS already exists")
            gwas = convert_duckdb_to_pydantic_model(GwasUpload, gwas)
            return gwas
        
        request.guid = file_guid
        request.status = GwasStatus.PROCESSING

        db = GwasDBClient()
        gwas = db.create_gwas_upload(request)
        gwas = convert_duckdb_to_pydantic_model(GwasUpload, gwas)

        redis_json = {
            "file_location": file_location,
            "metadata": request.model_dump(mode="json")
        }

        redis = RedisClient()
        redis.add_to_queue(redis.process_gwas_queue, redis_json)

        return gwas 
    except HTTPException as e:
        raise e
    except Exception as e:
        # Clean up file if there's an error
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{guid}")
async def update_gwas(
    guid: str,
    coloc_results: List[UploadColoc],
    study_extractions: List[UploadStudyExtraction]
):
    try:
        gwas_upload_db = GwasDBClient()
        studies_db = StudiesDBClient()
        
        gwas = gwas_upload_db.get_gwas_by_guid(guid)
        if gwas is None:
            raise HTTPException(status_code=404, detail=f"Uploaded GWAS with GUID {guid} not found")
        gwas = convert_duckdb_to_pydantic_model(GwasUpload, gwas)

        ld_blocks = [study.ld_block for study in study_extractions]
        existing_ld_blocks = studies_db.get_ld_blocks_by_ld_block(ld_blocks)

        coloc_snps = [coloc.candidate_snp for coloc in coloc_results]
        coloc_snps = studies_db.get_variants_by_snp_strings(coloc_snps)

        study_extractions_snps = [study_extractions.snp for study_extractions in study_extractions]
        study_extractions_snps = studies_db.get_variants_by_snp_strings(study_extractions_snps)

        for i, study in enumerate(study_extractions):
            study.gwas_upload_id = gwas.id
            study.snp_id = study_extractions_snps[i][0] if study_extractions_snps[i] else None
            study.ld_block_id = existing_ld_blocks[i][0] if existing_ld_blocks[i] else None

        study_extractions = gwas_upload_db.populate_study_extractions(study_extractions)
        study_extractions = convert_duckdb_to_pydantic_model(UploadStudyExtraction, study_extractions)

        study_id_map = {
            study.unique_study_id: study
            for study in study_extractions
        }

        unique_study_ids = [coloc.unique_study_id for coloc in coloc_results]
        existing_study_extractions = studies_db.get_study_extractions_by_unique_study_id(unique_study_ids)
        existing_study_extractions = convert_duckdb_to_pydantic_model(StudyExtraction, existing_study_extractions)
        for i, coloc in enumerate(coloc_results):
            coloc.gwas_upload_id = gwas.id
            coloc.snp_id = coloc_snps[i][0] if coloc_snps[i] else None

            if (coloc.unique_study_id in study_id_map):
                upload_study_extraction = study_id_map.get(coloc.unique_study_id)
                coloc.upload_study_extraction_id = upload_study_extraction.id
                coloc.chr = upload_study_extraction.chr
                coloc.bp = upload_study_extraction.bp
                coloc.min_p = upload_study_extraction.min_p
                coloc.ld_block = upload_study_extraction.ld_block
                coloc.known_gene = upload_study_extraction.known_gene
            else:
                coloc.existing_study_extraction_id = existing_study_extractions[i].id
                coloc.chr = existing_study_extractions[i].chr
                coloc.bp = existing_study_extractions[i].bp
                coloc.min_p = existing_study_extractions[i].min_p
                coloc.ld_block = existing_study_extractions[i].ld_block
                coloc.known_gene = existing_study_extractions[i].known_gene

        gwas_upload_db.populate_colocs(coloc_results)
        updated_gwas = gwas_upload_db.update_gwas_status(guid, GwasStatus.COMPLETED)
        updated_gwas = convert_duckdb_to_pydantic_model(GwasUpload, updated_gwas)

        # email_service = EmailService()
        # await email_service.send_results_email(gwas.email, guid)

        return updated_gwas
    except HTTPException as e:
        raise e
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{guid}", response_model=GwasUploadResponse)
async def get_gwas(guid: str):
    try:
        studies_db = StudiesDBClient()
        gwas_upload_db = GwasDBClient()
        gwas = gwas_upload_db.get_gwas_by_guid(guid)
        if gwas is None:
            raise HTTPException(status_code=404, detail="GWAS not found")

        gwas = convert_duckdb_to_pydantic_model(GwasUpload, gwas)

        if gwas.status != GwasStatus.COMPLETED:
            return gwas

        colocalisations = gwas_upload_db.get_colocs_by_gwas_upload_id(gwas.id)
        colocalisations = convert_duckdb_to_pydantic_model(UploadColoc, colocalisations)

        upload_study_extractions = gwas_upload_db.get_study_extractions_by_gwas_upload_id(gwas.id)
        upload_study_extractions = convert_duckdb_to_pydantic_model(UploadStudyExtraction, upload_study_extractions)

        existing_study_extraction_ids = [coloc.existing_study_extraction_id for coloc in colocalisations if coloc.existing_study_extraction_id is not None]
        existing_study_extractions = studies_db.get_study_extractions_by_id(existing_study_extraction_ids)
        existing_study_extractions = convert_duckdb_to_pydantic_model(StudyExtraction, existing_study_extractions)

        return GwasUploadResponse(
            gwas=gwas,
            existing_study_extractions=existing_study_extractions,
            upload_study_extractions=upload_study_extractions,
            colocalisations=colocalisations
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))
