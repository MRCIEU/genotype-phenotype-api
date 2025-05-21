from app.config import get_settings
from functools import lru_cache
from typing import List
import duckdb

from app.db.utils import log_performance

settings = get_settings()

@lru_cache()
def get_associations_db_connection():
    return duckdb.connect(settings.ASSOCIATIONS_DB_PATH, read_only=True)

class AssociationsDBClient:
    def __init__(self):
        self.associations_conn = get_associations_db_connection()

    @log_performance
    def get_associations_for_variant_and_studies(self, snp_id: int, study_ids: List[int]):
        if not study_ids or not snp_id:
            return []
        
        formatted_study_ids = ','.join(f"{study_id}" for study_id in study_ids)
        query = f"""
            SELECT * FROM associations 
            WHERE study_id IN ({formatted_study_ids}) AND snp_id = {snp_id}
        """
        return self.associations_conn.execute(query).fetchall()

    @log_performance
    def get_associations(self, snp_ids: List[int] = None, study_ids: List[int] = None, p_value_threshold: float = 1):
        if not snp_ids and not study_ids:
            return []

        query = "SELECT * FROM associations WHERE 1=1"
        if snp_ids:
            formatted_snp_ids = ','.join(f"{snp_id}" for snp_id in snp_ids)
            query += f" AND snp_id IN ({formatted_snp_ids})"
        
        if study_ids:
            formatted_study_ids = ','.join(f"{study_id}" for study_id in study_ids)
            query += f" AND study_id IN ({formatted_study_ids})"

        if p_value_threshold is not None:
            query += f" AND p <= {p_value_threshold}"
        
        return self.associations_conn.execute(query).fetchall()
        