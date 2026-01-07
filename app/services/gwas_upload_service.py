from app.db.gwas_db import GwasDBClient
from app.models.schemas import (
    GwasUpload,
    UpdateGwasRequest,
    GwasStatus,
    LdBlock,
    Variant,
    UploadStudyExtraction,
    UploadColocGroup,
    UploadColocPair,
    StudyExtraction,
    convert_duckdb_to_pydantic_model,
)
from app.db.studies_db import StudiesDBClient
from app.logging_config import get_logger
import sentry_sdk

logger = get_logger(__name__)


class GwasUploadService:
    def __init__(self):
        self.gwas_upload_db = GwasDBClient()
        self.studies_db = StudiesDBClient()

    def update_gwas_success(self, gwas: GwasUpload, update_gwas_request: UpdateGwasRequest):
        gwas.status = GwasStatus.COMPLETED
        # gwas.updated_at = datetime.now()
        ld_blocks = [study.ld_block for study in update_gwas_request.study_extractions]

        existing_ld_blocks = self.studies_db.get_ld_blocks_by_ld_block(ld_blocks)
        existing_ld_blocks = convert_duckdb_to_pydantic_model(LdBlock, existing_ld_blocks)

        known_snps = [coloc.snp for coloc in update_gwas_request.coloc_groups] + [
            study.snp for study in update_gwas_request.study_extractions
        ]
        known_snps = list(set(known_snps))
        known_snps = self.studies_db.get_variants_by_snp_strings(known_snps)
        known_snps = convert_duckdb_to_pydantic_model(Variant, known_snps)

        study_extractions_snps = [study_extractions.snp for study_extractions in update_gwas_request.study_extractions]
        study_extractions_snps = self.studies_db.get_variants_by_snp_strings(study_extractions_snps)
        study_extractions_snps = convert_duckdb_to_pydantic_model(Variant, study_extractions_snps)

        upload_study_extractions = []
        for i, study in enumerate(update_gwas_request.study_extractions):
            upload_study_extractions.append(
                UploadStudyExtraction(
                    gwas_upload_id=gwas.id,
                    snp=study.snp,
                    unique_study_id=study.unique_study_id,
                    study=study.study,
                    file=study.file,
                    chr=study.chr,
                    bp=study.bp,
                    min_p=study.min_p,
                    ld_block=study.ld_block,
                    snp_id=study_extractions_snps[i].id if study_extractions_snps[i] else None,
                    ld_block_id=existing_ld_blocks[i].id if existing_ld_blocks[i] else None,
                )
            )

        self.gwas_upload_db.populate_study_extractions(upload_study_extractions)

        unique_study_ids = [coloc_pair.unique_study_id_a for coloc_pair in update_gwas_request.coloc_pairs] + [
            coloc_pair.unique_study_id_b for coloc_pair in update_gwas_request.coloc_pairs
        ]
        unique_study_ids = list(set(unique_study_ids))

        existing_study_extractions = self.studies_db.get_study_extractions_by_unique_study_id(unique_study_ids)
        existing_study_extractions = convert_duckdb_to_pydantic_model(StudyExtraction, existing_study_extractions)
        existing_study_extractions = [study for study in existing_study_extractions if study is not None]

        upload_study_id_map = {study.unique_study_id: study for study in upload_study_extractions}
        existing_study_id_map = {study.unique_study_id: study for study in existing_study_extractions}
        snp_map = {snp.snp: snp for snp in known_snps}
        ld_block_map = {ld_block.ld_block: ld_block.id for ld_block in existing_ld_blocks}

        upload_coloc_groups = []
        for i, coloc in enumerate(update_gwas_request.coloc_groups):
            upload_coloc_group = UploadColocGroup(
                gwas_upload_id=gwas.id,
                coloc_group_id=coloc.coloc_group_id,
                snp_id=snp_map.get(coloc.snp).id if snp_map.get(coloc.snp) else None,
                ld_block_id=ld_block_map.get(coloc.ld_block) if ld_block_map.get(coloc.ld_block) else None,
                h4_connectedness=coloc.h4_connectedness,
                h3_connectedness=coloc.h3_connectedness,
            )

            mapped_study_extraction = None

            if coloc.unique_study_id in upload_study_id_map:
                mapped_study_extraction = upload_study_id_map.get(coloc.unique_study_id)
                upload_coloc_group.study_extraction_id = mapped_study_extraction.id
            elif coloc.unique_study_id in existing_study_id_map:
                mapped_study_extraction = existing_study_id_map.get(coloc.unique_study_id)
                upload_coloc_group.existing_study_extraction_id = mapped_study_extraction.id
            else:
                raise ValueError(f"Study extraction not found for unique study id: {coloc.unique_study_id}")

            upload_coloc_group.ld_block_id = (
                ld_block_map.get(mapped_study_extraction.ld_block)
                if ld_block_map.get(mapped_study_extraction.ld_block)
                else None
            )
            upload_coloc_groups.append(upload_coloc_group)

        upload_coloc_pairs = []
        for i, coloc_pair in enumerate(update_gwas_request.coloc_pairs):
            upload_coloc_pair = UploadColocPair(
                gwas_upload_id=gwas.id,
                ld_block_id=ld_block_map.get(coloc_pair.ld_block) if ld_block_map.get(coloc_pair.ld_block) else None,
                h3=coloc_pair.h3,
                h4=coloc_pair.h4,
                false_positive=coloc_pair.false_positive,
                false_negative=coloc_pair.false_negative,
                ignore=coloc_pair.ignore
            )

            if coloc_pair.unique_study_id_a in upload_study_id_map:
                upload_coloc_pair.study_extraction_id_a = upload_study_id_map.get(coloc_pair.unique_study_id_a).id
            elif coloc_pair.unique_study_id_a in existing_study_id_map:
                upload_coloc_pair.existing_study_extraction_id_a = existing_study_id_map.get(
                    coloc_pair.unique_study_id_a
                ).id
            else:
                raise ValueError(f"Study extraction A not found for unique study id: {coloc_pair.unique_study_id_a}")

            if coloc_pair.unique_study_id_b in upload_study_id_map:
                upload_coloc_pair.study_extraction_id_b = upload_study_id_map.get(coloc_pair.unique_study_id_b).id
            elif coloc_pair.unique_study_id_b in existing_study_id_map:
                upload_coloc_pair.existing_study_extraction_id_b = existing_study_id_map.get(
                    coloc_pair.unique_study_id_b
                ).id
            else:
                raise ValueError(f"Study extraction B not found for unique study id: {coloc_pair.unique_study_id_b}")

            upload_coloc_pairs.append(upload_coloc_pair)

        self.gwas_upload_db.populate_coloc_groups(upload_coloc_groups)
        self.gwas_upload_db.populate_coloc_pairs(upload_coloc_pairs)
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
            "GWAS processing failed for {guid}: {reason}",
            guid=gwas.guid,
            reason=update_gwas_request.failure_reason,
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
