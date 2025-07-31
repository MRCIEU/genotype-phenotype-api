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

    def _fetch_coloc_pairs(self, condition: str):
        query = f"""
            SELECT * FROM coloc_pairs WHERE {condition}
        """
        return self.coloc_pairs_conn.execute(query).fetchall()

    @log_performance
    def get_coloc_pairs_for_study_extraction_matches(
        self,
        study_extraction_ids: List[int],
        h3_threshold: float = 0.0,
        h4_threshold: float = 0.8,
    ):
        if not study_extraction_ids:
            return []

        formatted_study_extraction_ids = ",".join(f"{study_id}" for study_id in study_extraction_ids)

        # Most performant approach: Use IN clauses to find all pairs where both IDs are in our list
        return self._fetch_coloc_pairs(f"""
            study_extraction_a_id IN ({formatted_study_extraction_ids}) 
            AND study_extraction_b_id IN ({formatted_study_extraction_ids})
            AND h4 >= {h4_threshold} AND h3 >= {h3_threshold}
        """)
