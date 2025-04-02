import duckdb

from app.config import get_settings
from app.models.schemas import GwasStatus, ProcessGwasRequest

settings = get_settings()

class GwasDBClient:

    def get_gwas(self, guid: str) -> GwasStatus:
        conn = duckdb.connect(settings.GWAS_UPLOAD_DB_PATH)
        result = conn.execute(f"SELECT * FROM gwas_upload WHERE guid = '{guid}'").fetchone()
        conn.close()
        return result

    def upload_gwas(self, guid: str, gwas_request: ProcessGwasRequest):
        conn = duckdb.connect(settings.GWAS_UPLOAD_DB_PATH)
        status = GwasStatus.PROCESSING

        conn.execute(f"""INSERT INTO gwas_upload VALUES (
            '{guid}',
            '{gwas_request.trait_name}',
            '{gwas_request.sample_size}',
            0.00015,
            '{gwas_request.ancestry}',
            '{gwas_request.study_type}',
            '{gwas_request.is_published}',
            '{gwas_request.doi}',
            '{gwas_request.permanent}'
        )""")
        conn.close()

    def update_gwas_status(self, guid: str, status: GwasStatus):
        conn = duckdb.connect(settings.GWAS_UPLOAD_DB_PATH)
        conn.execute(f"UPDATE gwas_upload SET status = '{status}' WHERE guid = '{guid}'")
        conn.close()
