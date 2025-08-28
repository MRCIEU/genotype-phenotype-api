from app.config import get_settings
from functools import lru_cache
from typing import List, Tuple
import duckdb

from app.db.utils import log_performance

settings = get_settings()


@lru_cache()
def get_associations_db_connection():
    return duckdb.connect(settings.ASSOCIATIONS_DB_PATH, read_only=True)


class AssociationsDBClient:
    def __init__(self):
        self.associations_conn = get_associations_db_connection()

    @log_performance
    def get_associations_for_variant_and_studies(self, snp_id: int, study_ids: List[int]):
        if not study_ids or not snp_id:
            return []

        placeholders = ",".join(["?" for _ in study_ids])
        query = f"""
            SELECT * FROM associations 
            WHERE snp_id = ? AND study_id IN ({placeholders})
            LIMIT 100
        """
        params = [snp_id] + study_ids
        return self.associations_conn.execute(query, params).fetchall()

    @log_performance
    def get_associations(
        self,
        snp_ids: List[int] = None,
        study_ids: List[int] = None,
        p_value_threshold: float = 1,
    ):
        if not snp_ids and not study_ids:
            return []

        query = "SELECT * FROM associations WHERE 1=1"
        params = []

        if snp_ids:
            placeholders = ",".join(["?" for _ in snp_ids])
            query += f" AND snp_id IN ({placeholders})"
            params.extend(snp_ids)

        if study_ids:
            placeholders = ",".join(["?" for _ in study_ids])
            query += f" AND study_id IN ({placeholders})"
            params.extend(study_ids)

        if p_value_threshold is not None:
            query += " AND p <= ?"
            params.append(p_value_threshold)
        
        query += " LIMIT 100"

        return self.associations_conn.execute(query, params).fetchall()

    @log_performance
    def get_associations_by_snp_study_pairs(self, snp_study_pairs: List[Tuple[int, int]]):
        if not snp_study_pairs:
            return []

        flattened_pairs = [item for pair in snp_study_pairs for item in pair]
        placeholders = ",".join(["(?, ?)" for _ in snp_study_pairs])

        # TODO: Remove limit once the associations table is updated
        query = f"""
            SELECT * FROM associations WHERE (snp_id, study_id) IN ({placeholders})
            LIMIT 100
        """
        return self.associations_conn.execute(query, flattened_pairs).fetchall()
