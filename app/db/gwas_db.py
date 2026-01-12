from typing import List, Optional
import duckdb
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential
import json
from app.config import get_settings
from app.models.schemas import (
    GwasStatus,
    ProcessGwasRequest,
    UploadColocGroup,
    UploadColocPair,
    UploadStudyExtraction,
)
from app.db.utils import log_performance

settings = get_settings()


class GwasDBClient:
    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True,
    )
    def connect(self) -> duckdb.DuckDBPyConnection:
        """Connect to DuckDB with retries"""
        try:
            conn = duckdb.connect(settings.GWAS_UPLOAD_DB_PATH)
            conn.execute("SELECT 1").fetchone()
            return conn
        except Exception as e:
            logger.error(f"Failed to connect to DuckDB: {e}")
            raise

    @log_performance
    def get_gwases(self):
        conn = self.connect()
        try:
            result = conn.execute("SELECT * FROM gwas_upload").fetchall()
            return result
        finally:
            conn.close()

    @log_performance
    def get_gwas_by_guid(self, guid: str):
        conn = self.connect()
        try:
            result = conn.execute(f"SELECT * FROM gwas_upload WHERE guid = '{guid}'").fetchone()
            return result
        finally:
            conn.close()

    @log_performance
    def get_coloc_groups_by_gwas_upload_id(self, gwas_upload_id: int):
        conn = self.connect()
        conn.execute(f"ATTACH DATABASE '{settings.STUDIES_DB_PATH}' AS studies_db (READ_ONLY)")

        try:
            upload_result = conn.execute(f"""SELECT coloc_groups.*,
                    studies_db.snp_annotations.chr as chr,
                    studies_db.snp_annotations.bp as bp,
                    study_extractions.min_p as min_p,
                    NULL as cis_trans,
                    study_extractions.ld_block as ld_block,
                    study_extractions.unique_study_id as unique_study_id,
                    study_extractions.study as study,
                    study_extractions.file as file,
                    NULL as svg_file,
                    NULL as file_with_lbfs,
                    studies_db.snp_annotations.display_snp,
                    studies_db.snp_annotations.rsid,
                    NULL as gene,
                    NULL as gene_id,
                    NULL as trait_id,
                    gwas_upload.name as trait_name,
                    NULL as trait_category,
                    gwas_upload.sample_size as sample_size,
                    gwas_upload.category as category,
                    gwas_upload.ancestry as ancestry,
                    NULL as heritability,
                    NULL as heritability_se,
                    NULL as data_type,
                    NULL as tissue,
                    NULL as cell_type,
                    NULL as source_id,
                    NULL as source_name,
                    NULL as source_url
                FROM coloc_groups
                LEFT JOIN study_extractions ON coloc_groups.study_extraction_id = study_extractions.id
                LEFT JOIN studies_db.snp_annotations on coloc_groups.snp_id = studies_db.snp_annotations.id 
                LEFT JOIN gwas_upload on coloc_groups.gwas_upload_id = gwas_upload.id
                WHERE coloc_groups.gwas_upload_id = {gwas_upload_id} and coloc_groups.study_extraction_id is not null""").fetchall()

            existing_result = conn.execute(f"""SELECT cg.*,
                    studies_db.snp_annotations.chr,
                    studies_db.snp_annotations.bp,
                    studies_db.study_extractions.min_p,
                    studies_db.study_extractions.cis_trans,
                    studies_db.study_extractions.ld_block,
                    studies_db.study_extractions.unique_study_id,
                    studies_db.study_extractions.study,
                    studies_db.study_extractions.file,
                    studies_db.study_extractions.svg_file,
                    studies_db.study_extractions.file_with_lbfs,
                    studies_db.snp_annotations.display_snp,
                    studies_db.snp_annotations.rsid,
                    studies_db.gene_annotations.gene,
                    studies_db.gene_annotations.id as gene_id,
                    studies_db.traits.id as trait_id,
                    studies_db.traits.trait_name,
                    studies_db.traits.trait_category,
                    studies_db.studies.sample_size,
                    studies_db.studies.category,
                    studies_db.studies.ancestry,
                    studies_db.studies.heritability,
                    studies_db.studies.heritability_se,
                    studies_db.studies.data_type,
                    studies_db.studies.tissue,
                    studies_db.studies.cell_type,
                    studies_db.study_sources.id as source_id,
                    studies_db.study_sources.name as source_name,
                    studies_db.study_sources.url as source_url
                FROM coloc_groups as cg
                LEFT JOIN studies_db.study_extractions ON cg.existing_study_extraction_id = studies_db.study_extractions.id
                LEFT JOIN studies_db.studies ON studies_db.study_extractions.study_id = studies_db.studies.id
                LEFT JOIN studies_db.snp_annotations on cg.snp_id = studies_db.snp_annotations.id 
                LEFT JOIN studies_db.gene_annotations on studies_db.studies.gene_id = studies_db.gene_annotations.id
                LEFT JOIN studies_db.traits ON studies_db.studies.trait_id = studies_db.traits.id
                LEFT JOIN studies_db.study_sources ON studies_db.studies.source_id = studies_db.study_sources.id
                WHERE cg.gwas_upload_id = {gwas_upload_id} and cg.existing_study_extraction_id is not null""").fetchall()
        finally:
            conn.close()
        return upload_result + existing_result

    @log_performance
    def get_coloc_pairs_by_gwas_upload_id(self, gwas_upload_id: int):
        conn = self.connect()
        try:
            result = conn.execute(f"SELECT * FROM coloc_pairs WHERE gwas_upload_id = {gwas_upload_id}").fetchall()
            return result
        finally:
            conn.close()

    @log_performance
    def get_study_extractions_by_gwas_upload_id(self, gwas_upload_id: int):
        conn = self.connect()
        try:
            result = conn.execute(f"SELECT * FROM study_extractions WHERE gwas_upload_id = {gwas_upload_id}").fetchall()
            return result
        finally:
            conn.close()

    @log_performance
    def create_gwas_upload(self, gwas_request: ProcessGwasRequest):
        upload_metadata = json.dumps(gwas_request.model_dump(mode="json"))
        conn = self.connect()
        try:
            result = conn.execute(f"""INSERT INTO gwas_upload (
                guid,
                name,
                email,
                sample_size,
                ancestry,
                category,
                is_published,
                doi,
                should_be_added,
                upload_metadata,
                status
            ) VALUES (
                '{gwas_request.guid}',
                '{gwas_request.name}',
                '{gwas_request.email}',
                {gwas_request.sample_size},
                '{gwas_request.ancestry}',
                '{gwas_request.category}',
                {gwas_request.is_published},
                '{gwas_request.doi}',
                {gwas_request.should_be_added},
                '{upload_metadata}',
                '{gwas_request.status.value}'
            ) RETURNING *""").fetchone()
            conn.commit()
            return result
        finally:
            conn.close()

    @log_performance
    def delete_gwas_upload(self, guid: str):
        conn = self.connect()
        try:
            conn.execute(
                "DELETE FROM coloc_groups WHERE gwas_upload_id = (SELECT id FROM gwas_upload WHERE guid = ?)", [guid]
            )
            conn.execute(
                "DELETE FROM coloc_pairs WHERE gwas_upload_id = (SELECT id FROM gwas_upload WHERE guid = ?)", [guid]
            )
            conn.execute(
                "DELETE FROM study_extractions WHERE gwas_upload_id = (SELECT id FROM gwas_upload WHERE guid = ?)",
                [guid],
            )
            conn.execute("DELETE FROM gwas_upload WHERE guid = ?", [guid])
            conn.commit()
        finally:
            conn.close()

    @log_performance
    def populate_study_extractions(self, study_extractions: List[UploadStudyExtraction]):
        conn = self.connect()
        results = []
        try:
            study_fields = list(UploadStudyExtraction.model_fields.keys())
            study_fields.remove("id")
            study_fields_str = ", ".join(study_fields)
            study_placeholders = ", ".join(["?" for _ in study_fields])
            for study in study_extractions:
                values = [getattr(study, field) for field in study_fields]
                result = conn.execute(
                    f"""
                    INSERT INTO study_extractions ({study_fields_str})
                    VALUES ({study_placeholders})
                    RETURNING *
                """,
                    values,
                ).fetchone()
                results.append(result)
            conn.commit()
        finally:
            conn.close()
        return results

    @log_performance
    def populate_coloc_groups(self, colocs: List[UploadColocGroup]):
        conn = self.connect()
        try:
            coloc_fields = list(UploadColocGroup.model_fields.keys())
            coloc_fields_str = ", ".join(coloc_fields)
            coloc_placeholders = ", ".join(["?" for _ in coloc_fields])

            for coloc in colocs:
                values = [getattr(coloc, field) for field in coloc_fields]
                conn.execute(
                    f"""
                    INSERT INTO coloc_groups ({coloc_fields_str})
                    VALUES ({coloc_placeholders})
                """,
                    values,
                )
            conn.commit()
        finally:
            conn.close()

    @log_performance
    def populate_coloc_pairs(self, coloc_pairs: List[UploadColocPair]):
        conn = self.connect()
        try:
            coloc_pair_fields = list(UploadColocPair.model_fields.keys())
            coloc_pair_fields_str = ", ".join(coloc_pair_fields)
            coloc_pair_placeholders = ", ".join(["?" for _ in coloc_pair_fields])

            for coloc_pair in coloc_pairs:
                values = [getattr(coloc_pair, field) for field in coloc_pair_fields]
                conn.execute(
                    f"""
                    INSERT INTO coloc_pairs ({coloc_pair_fields_str})
                    VALUES ({coloc_pair_placeholders})
                """,
                    values,
                )
            conn.commit()
        finally:
            conn.close()

    @log_performance
    def update_gwas_status(self, guid: str, status: GwasStatus, failure_reason: Optional[str] = None):
        conn = self.connect()
        try:
            conn.execute(
                "UPDATE gwas_upload SET status = ?, failure_reason = ?, updated_at = CURRENT_TIMESTAMP WHERE guid = ?",
                [status.value, failure_reason, guid],
            )
            conn.commit()

            result = conn.execute(
                "SELECT id, guid, email, name, sample_size, ancestry, category, is_published, doi, should_be_added, upload_metadata, status, failure_reason, created_at, updated_at FROM gwas_upload WHERE guid = ?",
                [guid],
            )
            return result.fetchone()
        finally:
            conn.close()
