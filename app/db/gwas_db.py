import duckdb
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.models.schemas import GwasStatus, ProcessGwasRequest

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

    def get_gwas(self, guid: str):
        conn = self.connect()
        try:
            result = conn.execute(f"SELECT * FROM gwas_upload WHERE guid = '{guid}'").fetchone()
            return result
        finally:
            conn.close()

    def upload_gwas(self, gwas_request: ProcessGwasRequest):
        conn = self.connect()
        try:
            result = conn.execute(f"""INSERT INTO gwas_upload (
                guid,
                name,
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
                '{gwas_request.sample_size}',
                '{gwas_request.ancestry}',
                '{gwas_request.category}',
                '{gwas_request.is_published}',
                '{gwas_request.doi}',
                '{gwas_request.should_be_added}',
                '{gwas_request.status.value}'
            ) RETURNING *""").fetchone()
            conn.commit()
            print('committed')
            return result
        finally:
            conn.close()

    def update_gwas_status(self, guid: str, status: GwasStatus):
        conn = duckdb.connect(settings.GWAS_UPLOAD_DB_PATH)
        conn.execute(f"UPDATE gwas_upload SET status = '{status}' WHERE guid = '{guid}'")
        conn.close()
