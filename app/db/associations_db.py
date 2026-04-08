from app.config import get_settings
from functools import lru_cache
from typing import List, Tuple
import duckdb

from app.db.utils import log_performance

settings = get_settings()


@lru_cache()
def get_associations_db_connection():
    connection = duckdb.connect(settings.ASSOCIATIONS_DB_PATH, read_only=True)
    connection.execute("PRAGMA memory_limit='4GB'")
    return connection


class AssociationsDBClient:
    def __init__(self):
        self.associations_conn = get_associations_db_connection()

    # TODO: keeping this for when we need to use the associations_full database.
    @log_performance
    def get_associations_metadata(self):
        query = "SELECT * FROM associations_metadata"
        return self.associations_conn.execute(query).fetchall()

    @log_performance
    def get_associations_by_table_name(
        self,
        table_name: str,
        snp_study_pairs: List[Tuple[int, int]],
    ) -> Tuple[List[tuple], List[str]]:
        if not snp_study_pairs:
            return [], []

        all_variant_ids = [pair[0] for pair in snp_study_pairs]
        all_study_ids = [pair[1] for pair in snp_study_pairs]

        query = f"""
            SELECT * FROM {table_name} WHERE variant_id IN (SELECT * FROM UNNEST(?)) AND study_id IN (SELECT * FROM UNNEST(?))
        """
        cursor = self.associations_conn.execute(query, [all_variant_ids, all_study_ids])
        rows = cursor.fetchall()
        columns = [d[0] for d in cursor.description]
        return rows, columns

    @log_performance
    def get_associations_by_snp_study_pairs(self, snp_study_pairs: List[Tuple[int, int]]):
        if not snp_study_pairs:
            return [], []

        all_variant_ids = [pair[0] for pair in snp_study_pairs]
        all_study_ids = [pair[1] for pair in snp_study_pairs]

        query = """
            SELECT * FROM associations WHERE variant_id IN (SELECT * FROM UNNEST(?)) AND study_id IN (SELECT * FROM UNNEST(?))
        """
        cursor = self.associations_conn.execute(query, [all_variant_ids, all_study_ids])
        rows = cursor.fetchall()
        columns = [d[0] for d in cursor.description]
        return rows, columns
