from app.config import get_settings
from functools import lru_cache
from typing import List
import duckdb

from app.db.utils import log_performance

settings = get_settings()

@lru_cache()
def get_gpm_db_connection():
    return duckdb.connect(settings.LD_DB_PATH, read_only=True)

class LdDBClient:
    def __init__(self):
        self.ld_conn = get_gpm_db_connection()

    @log_performance
    def get_ld_proxies(self, snp_ids: List[int]):
        formatted_snp_ids = ','.join(f"{snp_id}" for snp_id in snp_ids)
        query = f"""
            SELECT * FROM ld
            WHERE (lead_snp_id IN ({formatted_snp_ids}) OR variant_snp_id IN ({formatted_snp_ids}))
            AND abs(r) > 0.894
        """
        return self.ld_conn.execute(query).fetchall()
    
    @log_performance
    def get_ld_matrix(self, snp_ids: List[int]):
        formatted_snp_ids = ','.join(f"{snp_id}" for snp_id in snp_ids)
        query = f"""
            SELECT * FROM 
                (SELECT * FROM ld WHERE lead_snp_id IN ({formatted_snp_ids}))
                WHERE variant_snp_id IN ({formatted_snp_ids}) AND variant_snp_id > lead_snp_id
        """
        return self.ld_conn.execute(query).fetchall()
