from typing import List
import duckdb
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

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
        try:
            result = conn.execute(f"SELECT * FROM coloc_groups WHERE gwas_upload_id = {gwas_upload_id}").fetchall()
            return result
        finally:
            conn.close()

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
            conn.execute(f"DELETE FROM gwas_upload WHERE guid = '{guid}'")
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
    def update_gwas_status(self, guid: str, status: GwasStatus):
        conn = self.connect()
        try:
            conn.execute(f"UPDATE gwas_upload SET status = '{status.value}' WHERE guid = '{guid}'")
            # conn.execute(f"UPDATE gwas_upload SET status = '{status.value}', updated_at = CURRENT_TIMESTAMP WHERE guid = '{guid}'")
            conn.commit()

            result = conn.execute(f"SELECT * FROM gwas_upload WHERE guid = '{guid}'")
            return result.fetchone()
        finally:
            conn.close()
