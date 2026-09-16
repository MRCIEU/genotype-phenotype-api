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
    connection.execute("PRAGMA memory_limit='2GB'")
    return connection


class ColocPairsDBClient:
    def __init__(self):
        self.coloc_pairs_conn = get_coloc_pairs_db_connection().cursor()

    @log_performance
    def get_coloc_pairs_metadata(self):
        query = "SELECT * FROM coloc_pairs_metadata"
        return self.coloc_pairs_conn.execute(query).fetchall()

    @log_performance
    def get_coloc_pairs_by_table_name(
        self,
        table_name: str,
        variant_ids: List[int],
        h3_threshold: float = 0.0,
        h4_threshold: float = 0.8,
    ):
        if not variant_ids:
            return []

        query = f"""
            SELECT * FROM {table_name}
            WHERE variant_id IN (SELECT * FROM UNNEST(?))
                AND h3 >= ?
                AND h4 >= ?
                AND false_positive = FALSE
        """
        cursor = self.coloc_pairs_conn.execute(query, [variant_ids, h3_threshold, h4_threshold])
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

        query = """
            SELECT * FROM coloc_pairs
            WHERE study_extraction_a_id IN (SELECT * FROM UNNEST(?))
                AND study_extraction_b_id IN (SELECT * FROM UNNEST(?))
                AND h4 >= ?
                AND h3 >= ?
                AND false_positive = FALSE
        """
        params = [study_extraction_ids, study_extraction_ids, h4_threshold, h3_threshold]
        return self.coloc_pairs_conn.execute(query, params).fetchall()

    @log_performance
    def get_coloc_pairs_by_variant_ids(
        self,
        variant_ids: List[int],
        h3_threshold: float = 0.0,
        h4_threshold: float = 0.8,
    ):
        if not variant_ids:
            return [], []

        query = """
            SELECT * FROM coloc_pairs
            WHERE variant_id IN (SELECT * FROM UNNEST(?))
                AND h3 >= ?
                AND h4 >= ?
                AND false_positive = FALSE
        """
        cursor = self.coloc_pairs_conn.execute(query, [variant_ids, h3_threshold, h4_threshold])
        rows = cursor.fetchall()
        columns = [d[0] for d in cursor.description] if cursor.description else []
        return rows, columns

    @log_performance
    def get_coloc_pairs_by_study_extraction_ids(
        self,
        study_extraction_ids: List[int],
        h4_threshold: float = 0.8,
    ):
        """
        Get coloc pairs that are not part of a coloc group (variant_id IS NULL),
        filtered by study extraction ids. Returns pairs where either
        study_extraction_a_id or study_extraction_b_id is in the list.
        """
        if not study_extraction_ids:
            return [], []

        query = """
            SELECT * FROM coloc_pairs
            WHERE variant_id IS NULL
                AND h4 >= ?
                AND (study_extraction_a_id IN (SELECT * FROM UNNEST(?))
                    OR study_extraction_b_id IN (SELECT * FROM UNNEST(?)))
                AND false_positive = FALSE
        """
        params = [h4_threshold, study_extraction_ids, study_extraction_ids]
        cursor = self.coloc_pairs_conn.execute(query, params)
        rows = cursor.fetchall()
        columns = [d[0] for d in cursor.description] if cursor.description else []
        return rows, columns
