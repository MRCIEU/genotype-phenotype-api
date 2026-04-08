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
    def get_ld_proxies(self, variant_ids: List[int], rsquared_threshold: float = 0.8):
        if not variant_ids:
            return []
        query = """
            SELECT * FROM ld
            WHERE (lead_variant_id IN (SELECT * FROM UNNEST(?)) OR proxy_variant_id IN (SELECT * FROM UNNEST(?))) AND r*r >= ?
        """
        return self.ld_conn.execute(query, [variant_ids, variant_ids, rsquared_threshold]).fetchall()

    @log_performance
    def get_ld_matrix(self, variant_ids: List[int]):
        if not variant_ids:
            return []
        query = """
            SELECT * FROM
                (SELECT * FROM ld WHERE lead_variant_id IN (SELECT * FROM UNNEST(?)))
                WHERE proxy_variant_id IN (SELECT * FROM UNNEST(?))
        """
        return self.ld_conn.execute(query, [variant_ids, variant_ids]).fetchall()
