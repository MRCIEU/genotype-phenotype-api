from app.config import get_settings
from functools import lru_cache
from typing import List
import duckdb
from app.logging_config import get_logger
from app.db.utils import log_performance

logger = get_logger(__name__)


settings = get_settings()


@lru_cache()
def get_coloc_pairs_db_connection():
    connection = duckdb.connect(settings.COLOC_PAIRS_DB_PATH, read_only=True)
    connection.execute("PRAGMA memory_limit='4GB'")
    return connection


class ColocPairsDBClient:
    def __init__(self):
        self.coloc_pairs_conn = get_coloc_pairs_db_connection()

    @log_performance
    def get_coloc_pairs_metadata(self):
        query = "SELECT * FROM coloc_pairs_metadata"
        return self.coloc_pairs_conn.execute(query).fetchall()

    @log_performance
    def get_coloc_pairs_by_table_name(
        self,
        table_name: str,
        snp_ids: List[int],
        h3_threshold: float = 0.0,
        h4_threshold: float = 0.8,
    ):
        if not snp_ids:
            return []

        snp_placeholders = ",".join(["?" for _ in snp_ids])

        query = f"""
            SELECT * FROM {table_name}
            WHERE snp_id IN ({snp_placeholders})
                AND h3 >= ?
                AND h4 >= ?
                AND spurious = FALSE
        """
        cursor = self.coloc_pairs_conn.execute(query, snp_ids + [h3_threshold, h4_threshold])
        rows = cursor.fetchall()
        columns = [d[0] for d in cursor.description] if cursor.description else []
        return rows, columns

    @log_performance
    def get_coloc_pairs_for_study_extraction_matches(
        self,
        study_extraction_ids: List[int],
        h3_threshold: float = 0.0,
        h4_threshold: float = 0.8,
    ):
        if not study_extraction_ids:
            return []

        study_extraction_ids = sorted(study_extraction_ids)

        query = """
            SELECT * FROM coloc_pairs
            WHERE study_extraction_a_id IN (SELECT * FROM UNNEST(?))
                AND study_extraction_b_id IN (SELECT * FROM UNNEST(?))
                AND h4 >= ?
                AND h3 >= ?
                AND spurious = FALSE
        """

        params = [study_extraction_ids, study_extraction_ids, h4_threshold, h3_threshold]
        return self.coloc_pairs_conn.execute(query, params).fetchall()

    @log_performance
    def get_coloc_pairs_by_snp_ids(
        self,
        snp_ids: List[int],
        h3_threshold: float = 0.0,
        h4_threshold: float = 0.8,
    ):
        if not snp_ids:
            return [], []

        placeholders = ",".join(["?"] * len(snp_ids))
        query = f"""
            SELECT * FROM coloc_pairs
            WHERE snp_id IN ({placeholders})
                AND h3 >= ?
                AND h4 >= ?
                AND spurious = FALSE
        """
        cursor = self.coloc_pairs_conn.execute(query, snp_ids + [h3_threshold, h4_threshold])
        rows = cursor.fetchall()
        columns = [d[0] for d in cursor.description] if cursor.description else []
        return rows, columns
