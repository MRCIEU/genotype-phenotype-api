from app.config import get_settings
from functools import lru_cache
from typing import List, Tuple
import duckdb

from app.db.utils import log_performance

settings = get_settings()


@lru_cache()
def get_associations_full_db_connection():
    connection = duckdb.connect(settings.ASSOCIATIONS_FULL_DB_PATH, read_only=True)
    connection.execute("PRAGMA memory_limit='4GB'")
    return connection


class AssociationsFullDBClient:
    def __init__(self):
        self.associations_conn = get_associations_full_db_connection()

    @log_performance
    def get_associations_metadata(self):
        query = "SELECT * FROM associations_metadata"
        return self.associations_conn.execute(query).fetchall()

    @log_performance
    def get_associations_by_table_name_and_variant_ids(
        self,
        table_name: str,
        variant_ids: List[int],
    ) -> Tuple[List[tuple], List[str]]:
        if not variant_ids:
            return [], []

        query = f"""
            SELECT * FROM {table_name} WHERE variant_id IN (SELECT * FROM UNNEST(?))
        """
        cursor = self.associations_conn.execute(query, [variant_ids])
        rows = cursor.fetchall()
        columns = [d[0] for d in cursor.description]
        return rows, columns
