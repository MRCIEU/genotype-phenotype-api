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
    return duckdb.connect(settings.COLOC_PAIRS_DB_PATH, read_only=True)


class ColocPairsDBClient:
    def __init__(self):
        self.coloc_pairs_conn = get_coloc_pairs_db_connection()

    @log_performance
    def get_coloc_pairs_for_study_extraction_matches(
        self,
        study_extraction_ids: List[int],
        h3_threshold: float = 0.0,
        h4_threshold: float = 0.8,
    ):
        if not study_extraction_ids:
            return []
        placeholders = ",".join(["?" for _ in study_extraction_ids])

        query = f"""
            SELECT * FROM coloc_pairs
            WHERE study_extraction_a_id IN ({placeholders})
                AND study_extraction_b_id IN ({placeholders})
                AND h4 >= ?
                AND h3 >= ?
                AND spurious = FALSE
        """

        params = study_extraction_ids + study_extraction_ids + [h4_threshold, h3_threshold]
        return self.coloc_pairs_conn.execute(query, params).fetchall()
