from app.config import get_settings
from functools import lru_cache
from typing import Iterable, List, Tuple
import duckdb

from app.db.utils import log_performance

settings = get_settings()


@lru_cache()
def get_associations_full_db_connection():
    connection = duckdb.connect(settings.ASSOCIATIONS_FULL_DB_PATH, read_only=True)
    connection.execute("PRAGMA memory_limit='4GB'")
    return connection


@lru_cache(maxsize=200)
def _get_cached_study_ids_for_table(table_name: str) -> frozenset[int]:
    connection = get_associations_full_db_connection()
    query = f"SELECT DISTINCT study_id FROM {table_name}"
    rows = connection.execute(query).fetchall()
    return frozenset(row[0] for row in rows)


def clear_table_study_ids_cache() -> None:
    _get_cached_study_ids_for_table.cache_clear()


class AssociationsFullDBClient:
    def __init__(self):
        self.associations_conn = get_associations_full_db_connection()

    @log_performance
    def get_associations_metadata(self):
        query = "SELECT * FROM associations_metadata"
        return self.associations_conn.execute(query).fetchall()

    def get_study_ids_for_table_name(self, table_name: str) -> frozenset[int]:
        return _get_cached_study_ids_for_table(table_name)

    def filter_study_ids_for_table(self, table_name: str, study_ids: Iterable[int]) -> list[int]:
        table_study_ids = self.get_study_ids_for_table_name(table_name)
        return [study_id for study_id in study_ids if study_id in table_study_ids]

    @log_performance
    def get_associations_by_table_name(
        self,
        table_name: str,
        variant_ids: List[int],
        study_ids: List[int],
    ) -> Tuple[List[tuple], List[str]]:
        if not variant_ids or not study_ids:
            return [], []

        query = f"""
            SELECT * FROM {table_name} WHERE variant_id IN (SELECT * FROM UNNEST(?)) AND study_id IN (SELECT * FROM UNNEST(?))
        """
        cursor = self.associations_conn.execute(query, [variant_ids, study_ids])
        rows = cursor.fetchall()
        columns = [d[0] for d in cursor.description]
        return rows, columns
