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
        raise Exception("associations_full_db is not currently used")
        if not snp_study_pairs:
            return [], []

        placeholders = ",".join(["?" for _ in snp_study_pairs])
        all_snp_ids = [pair[0] for pair in snp_study_pairs]
        all_study_ids = [pair[1] for pair in snp_study_pairs]

        query = f"""
            SELECT * FROM {table_name} WHERE snp_id IN ({placeholders}) AND study_id IN ({placeholders})
        """
        cursor = self.associations_conn.execute(query, all_snp_ids + all_study_ids)
        rows = cursor.fetchall()
        columns = [d[0] for d in cursor.description]
        return rows, columns
