from app.config import get_settings
from functools import lru_cache
from typing import List
import duckdb

from app.db.utils import log_performance

settings = get_settings()


@lru_cache()
def get_gpm_db_connection():
    connection = duckdb.connect(settings.LD_DB_PATH, read_only=True)
    connection.execute("PRAGMA memory_limit='4GB'")
    return connection


class LdDBClient:
    def __init__(self):
        self.ld_conn = get_gpm_db_connection()

    @log_performance
    def get_ld_proxies(self, snp_ids: List[int]):
        placeholders = ",".join(["?"] * len(snp_ids))
        query = f"""
            SELECT * FROM ld
            WHERE (lead_snp_id IN ({placeholders}) OR variant_snp_id IN ({placeholders})) AND abs(r) > 0.894
        """
        return self.ld_conn.execute(query, snp_ids + snp_ids).fetchall()

    @log_performance
    def get_ld_matrix(self, snp_ids: List[int]):
        placeholders = ",".join(["?"] * len(snp_ids))
        query = f"""
            SELECT * FROM 
                (SELECT * FROM ld WHERE lead_snp_id IN ({placeholders}))
                WHERE variant_snp_id IN ({placeholders})
        """
        return self.ld_conn.execute(query, snp_ids + snp_ids).fetchall()
