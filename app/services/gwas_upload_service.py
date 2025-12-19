from app.db.gwas_db import GwasDBClient
from app.models.schemas import (
    GwasUpload,
    UpdateGwasRequest,
    GwasStatus,
    LdBlock,
    Variant,
    UploadStudyExtraction,
    StudyExtraction,
    convert_duckdb_to_pydantic_model,
)
from datetime import datetime
from app.db.studies_db import StudiesDBClient
from app.logging_config import get_logger
import sentry_sdk

logger = get_logger(__name__)

class GwasUploadService():
    def __init__(self):
        self.gwas_upload_db = GwasDBClient()
        self.studies_db = StudiesDBClient()

    def update_gwas_success(self, gwas: GwasUpload, update_gwas_request: UpdateGwasRequest):
        gwas.status = GwasStatus.COMPLETED
        gwas.updated_at = datetime.now()
        ld_blocks = [study.ld_block for study in update_gwas_request.study_extractions]

        existing_ld_blocks = self.studies_db.get_ld_blocks_by_ld_block(ld_blocks)
        existing_ld_blocks = convert_duckdb_to_pydantic_model(LdBlock, existing_ld_blocks)

        coloc_snps = [coloc.snp for coloc in update_gwas_request.coloc_groups]
        coloc_snps = self.studies_db.get_variants_by_snp_strings(coloc_snps)
        coloc_snps = convert_duckdb_to_pydantic_model(Variant, coloc_snps)

        study_extractions_snps = [study_extractions.snp for study_extractions in update_gwas_request.study_extractions]
        study_extractions_snps = self.studies_db.get_variants_by_snp_strings(study_extractions_snps)
        study_extractions_snps = convert_duckdb_to_pydantic_model(Variant, study_extractions_snps)

        upload_study_extractions = []
        for i, study in enumerate(update_gwas_request.study_extractions):
            upload_study_extractions.append(UploadStudyExtraction(
                gwas_upload_id=gwas.id,
                snp_id=study_extractions_snps[i].id if study_extractions_snps[i] else None,
                ld_block_id=existing_ld_blocks[i].id if existing_ld_blocks[i] else None,
            ))

        study_extractions = self.gwas_upload_db.populate_study_extractions(upload_study_extractions)

        upload_study_id_map = {study.unique_study_id: study for study in study_extractions}
        existing_study_id_map = {study.unique_study_id: study for study in existing_study_extractions}

        unique_study_ids = [coloc.existing_study_extraction_a + coloc.existing_study_extraction_b for coloc in update_gwas_request.coloc_groups]
        existing_study_extractions = self.studies_db.get_study_extractions_by_unique_study_id(unique_study_ids)
        existing_study_extractions = convert_duckdb_to_pydantic_model(StudyExtraction, existing_study_extractions)

        upload_coloc_groups = []
        for i, coloc in enumerate(update_gwas_request.coloc_groups):
            upload_coloc_group = UploadColocGroup(
                gwas_upload_id=gwas.id,
                coloc_group_id=coloc.coloc_group_id,
                snp_id=coloc_snps[i].id if coloc_snps[i] else None,
                ld_block_id=existing_ld_blocks[i].id if existing_ld_blocks[i] else None,
            )

            mapped_study_extraction = None

            if coloc.unique_study_id in upload_study_id_map:
                mapped_study_extraction = upload_study_id_map.get(coloc.unique_study_id)
                upload_coloc_group.study_extraction_id = mapped_study_extraction.id
            else:
                mapped_study_extraction = existing_study_id_map.get(coloc.unique_study_id)
                upload_coloc_group.existing_study_extraction_id = mapped_study_extraction.id

            upload_coloc_group.ld_block_id = mapped_study_extraction.ld_block_id
            upload_coloc_groups.append(upload_coloc_group)
        
        for i, coloc_pair in enumerate(update_gwas_request.coloc_pairs):
            upload_coloc_pair = UploadColocPair(
                gwas_upload_id=gwas.id,
                ld_block_id=existing_ld_blocks[i].id if existing_ld_blocks[i] else None,
            )

            if coloc_pair.unique_study_id_a in upload_study_id_map and coloc_pair.unique_study_id_b in upload_study_id_map:
                upload_study_extraction_a = upload_study_id_map.get(coloc_pair.unique_study_id_a)
                upload_study_extraction_b = upload_study_id_map.get(coloc_pair.unique_study_id_b)
                coloc_pair.study_extraction_a_id = upload_study_extraction_a.id
                coloc_pair.study_extraction_b_id = upload_study_extraction_b.id
            else:
                upload_coloc_pair.existing_study_extraction_a_id = existing_study_id_map.get(coloc_pair.unique_study_id_a).id
                upload_coloc_pair.existing_study_extraction_b_id = existing_study_id_map.get(coloc_pair.unique_study_id_b).id

        self.gwas_upload_db.populate_colocs(update_gwas_request.coloc_groups)
        updated_gwas = self.gwas_upload_db.update_gwas_status(gwas.guid, GwasStatus.COMPLETED)
        updated_gwas = convert_duckdb_to_pydantic_model(GwasUpload, updated_gwas)
        return updated_gwas
      
    def update_gwas_failure(self, gwas: GwasUpload, update_gwas_request: UpdateGwasRequest):
        error_context = {
            "guid": gwas.guid,
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
        updated_gwas = self.gwas_upload_db.update_gwas_status(gwas.guid, GwasStatus.FAILED)
        updated_gwas = convert_duckdb_to_pydantic_model(GwasUpload, updated_gwas)

        return updated_gwas