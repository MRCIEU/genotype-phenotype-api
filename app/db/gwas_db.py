from typing import List
import duckdb
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.models.schemas import Coloc, GwasStatus, ProcessGwasRequest, StudyExtraction, UploadColoc, UploadStudyExtraction

settings = get_settings()

class GwasDBClient:
    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True
    )
    def connect(self) -> duckdb.DuckDBPyConnection:
        """Connect to DuckDB with retries"""
        try:
            conn = duckdb.connect(settings.GWAS_UPLOAD_DB_PATH)
            conn.execute("SELECT 1").fetchone()
            return conn
        except Exception as e:
            print(f"Failed to connect to DuckDB: {e}")
            raise

    def get_gwases(self):
        conn = self.connect()
        try:
            result = conn.execute("SELECT * FROM gwas_upload").fetchall()
            return result
        finally:
            conn.close()

    def get_gwas_by_guid(self, guid: str):
        conn = self.connect()
        try:
            result = conn.execute(f"SELECT * FROM gwas_upload WHERE guid = '{guid}'").fetchone()
            return result
        finally:
            conn.close()

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
                result = conn.execute(f"""
                    INSERT INTO study_extractions ({study_fields_str})
                    VALUES ({study_placeholders})
                    RETURNING *
                """, values).fetchone()
                results.append(result)
            conn.commit()
        finally:
            conn.close()
        return results

    def populate_colocs(self, colocs: List[UploadColoc]):
        conn = self.connect()
        try:
            coloc_fields = list(UploadColoc.model_fields.keys())
            coloc_fields_str = ", ".join(coloc_fields)
            coloc_placeholders = ", ".join(["?" for _ in coloc_fields])
            for coloc in colocs:
                values = [getattr(coloc, field) for field in coloc_fields]
                conn.execute(f"""
                    INSERT INTO colocalisations ({coloc_fields_str})
                    VALUES ({coloc_placeholders})
                """, values)
            conn.commit()
        finally:
            conn.close()

    def update_gwas_status(self, guid: str, status: GwasStatus):
        conn = self.connect()
        try:
            conn.execute(f"UPDATE gwas_upload SET status = '{status.value}' WHERE guid = '{guid}'")
        finally:
            conn.close()
