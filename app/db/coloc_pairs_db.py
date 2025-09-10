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
    connection.execute("PRAGMA memory_limit='8GB'")
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
        study_extraction_a_ids: List[int],
        study_extraction_b_ids: List[int],
        h3_threshold: float = 0.0,
        h4_threshold: float = 0.8,
    ):
        if not study_extraction_a_ids or not study_extraction_b_ids:
            return []

        study_extraction_a_placeholders = ",".join(["?" for _ in study_extraction_a_ids])
        study_extraction_b_placeholders = ",".join(["?" for _ in study_extraction_b_ids])

        query = f"""
            SELECT * FROM {table_name}
            WHERE study_extraction_a_id IN ({study_extraction_a_placeholders})
                AND study_extraction_b_id IN ({study_extraction_b_placeholders})
                AND h3 >= ?
                AND h4 >= ?
                AND spurious = FALSE
        """
        return self.coloc_pairs_conn.execute(
            query, study_extraction_a_ids + study_extraction_b_ids + [h3_threshold, h4_threshold]
        ).fetchall()

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
