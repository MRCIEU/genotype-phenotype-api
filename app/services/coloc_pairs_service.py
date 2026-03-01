from functools import lru_cache
from typing import List
from app.logging_config import get_logger
from app.models.schemas import (
    ColocPairMetadata,
    convert_duckdb_to_pydantic_model,
    convert_duckdb_tuples_to_dicts,
)
from app.db.coloc_pairs_db import ColocPairsDBClient

logger = get_logger(__name__)


class ColocPairsService:
    def __init__(self):
        self.coloc_pairs_db = ColocPairsDBClient()

    @lru_cache(maxsize=1)
    def get_coloc_pairs_metadata(self):
        metadata = self.coloc_pairs_db.get_coloc_pairs_metadata()
        metadata = convert_duckdb_to_pydantic_model(ColocPairMetadata, metadata)
        return metadata

    def get_coloc_pairs_by_snp_ids(
        self,
        snp_ids: List[int],
        h3_threshold: float = 0.0,
        h4_threshold: float = 0.8,
    ) -> List[dict]:
        """Get coloc pairs that have an snp_id (part of a coloc group)."""
        if not snp_ids:
            return []
        pair_rows, pair_columns = self.coloc_pairs_db.get_coloc_pairs_by_snp_ids(
            snp_ids, h3_threshold=h3_threshold, h4_threshold=h4_threshold
        )
        return convert_duckdb_tuples_to_dicts(pair_rows, pair_columns)

    def get_coloc_pairs_full(
        self,
        snp_ids: List[int],
        h3_threshold: float = 0.0,
        h4_threshold: float = 0.8,
    ) -> List[dict]:
        """
        Get coloc pairs from both coloc groups (snp_id) and non-coloc-group pairs
        (snp_id null). Combines results and adds in_coloc_group column (True for
        coloc group pairs, False for others).
        """
        coloc_in_group = self.get_coloc_pairs_by_snp_ids(snp_ids, h3_threshold=h3_threshold, h4_threshold=h4_threshold)
        for row in coloc_in_group:
            row["in_coloc_group"] = True

        study_extraction_ids = set()
        for row in coloc_in_group:
            if row.get("study_extraction_a_id") is not None:
                study_extraction_ids.add(row["study_extraction_a_id"])
            if row.get("study_extraction_b_id") is not None:
                study_extraction_ids.add(row["study_extraction_b_id"])

        coloc_not_in_group = []
        if study_extraction_ids:
            coloc_not_in_group = self.get_coloc_pairs_by_study_extraction_ids(list(study_extraction_ids))
            for row in coloc_not_in_group:
                row["in_coloc_group"] = False

        return coloc_in_group + coloc_not_in_group

    def get_coloc_pairs_by_study_extraction_ids(
        self,
        study_extraction_ids: List[int],
        h4_threshold: float = 0.8,
    ) -> List[dict]:
        """
        Get coloc pairs that are not part of a coloc group (snp_id IS NULL),
        filtered by study extraction ids. Returns pairs where either
        study_extraction_a_id or study_extraction_b_id is in the list.
        """
        if not study_extraction_ids:
            return []
        logger.info(f"Getting coloc pairs (snp_id null) for {len(study_extraction_ids)} study extraction ids")
        pair_rows, pair_columns = self.coloc_pairs_db.get_coloc_pairs_by_study_extraction_ids(
            study_extraction_ids, h4_threshold=h4_threshold
        )
        return convert_duckdb_tuples_to_dicts(pair_rows, pair_columns)
