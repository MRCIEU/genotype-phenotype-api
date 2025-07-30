from app.config import get_settings
from functools import lru_cache
from typing import List
import duckdb

from app.db.utils import log_performance

settings = get_settings()

@lru_cache()
def get_coloc_pairs_db_connection():
    return duckdb.connect(settings.COLOC_PAIRS_DB_PATH, read_only=True)

class ColocPairsDBClient:
    def __init__(self):
        self.coloc_pairs_conn = get_coloc_pairs_db_connection()

    def _fetch_coloc_pairs(self, condition: str):
        query = f"""
            SELECT * FROM coloc_pairs WHERE {condition}
        """
        return self.coloc_pairs_conn.execute(query).fetchall()
    
    @log_performance
    def get_all_coloc_pairs_for_study(self, study_id: int, h3_threshold: float = 0.0, h4_threshold: float = 0.8):
        return self._fetch_coloc_pairs(f"""
            (study_extraction_a_id = {study_id} OR study_extraction_b_id = {study_id})
            AND h4 >= {h4_threshold} AND h3 >= {h3_threshold}
        """)
    
    @log_performance
    def get_all_coloc_pairs_for_snp(self, snp_id: int, h3_threshold: float = 0.0, h4_threshold: float = 0.8):
        return self._fetch_coloc_pairs(f"""
            snp_id = {snp_id} AND h4 >= {h4_threshold} AND h3 >= {h3_threshold}
        """)

    @log_performance
    def get_all_coloc_pairs_for_snps(self, snp_ids: List[int], h3_threshold: float = 0.0, h4_threshold: float = 0.8):
        formatted_snp_ids = ','.join(f"{snp_id}" for snp_id in snp_ids)
        return self._fetch_coloc_pairs(f"""
            snp_id IN ({formatted_snp_ids}) AND h4 >= {h4_threshold} AND h3 >= {h3_threshold}
        """)
    

        