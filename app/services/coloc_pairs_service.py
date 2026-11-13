from functools import lru_cache
from typing import List
import numpy as np
from app.logging_config import get_logger
from app.models.schemas import (
    ColocPairMetadata,
    convert_duckdb_to_pydantic_model,
    convert_duckdb_tuples_to_dicts,
)
from app.db.coloc_pairs_db import ColocPairsDBClient
from app.db.utils import concatenate_numpy_columns

logger = get_logger(__name__)


class ColocPairsService:
    def __init__(self):
        self.coloc_pairs_db = ColocPairsDBClient()

    @lru_cache(maxsize=1)
    def get_coloc_pairs_metadata(self):
        metadata = self.coloc_pairs_db.get_coloc_pairs_metadata()
        metadata = convert_duckdb_to_pydantic_model(ColocPairMetadata, metadata)
        return metadata

    def get_coloc_pairs_by_variant_ids(
        self,
        variant_ids: List[int],
        h3_threshold: float = 0.0,
        h4_threshold: float = 0.8,
    ) -> List[dict]:
        """Get coloc pairs that have an variant_id (part of a coloc group)."""
        if not variant_ids:
            return []
        pair_rows, pair_columns = self.coloc_pairs_db.get_coloc_pairs_by_variant_ids(
            variant_ids, h3_threshold=h3_threshold, h4_threshold=h4_threshold
        )
        return convert_duckdb_tuples_to_dicts(pair_rows, pair_columns)

    def get_coloc_pairs_full(
        self,
        variant_ids: List[int],
        h3_threshold: float = 0.0,
        h4_threshold: float = 0.8,
    ) -> List[dict]:
        """
        Get coloc pairs from both coloc groups (variant_id) and non-coloc-group pairs
        (variant_id null). Combines results and adds in_coloc_group column (True for
        coloc group pairs, False for others).
        """
        coloc_in_group = self.get_coloc_pairs_by_variant_ids(
            variant_ids, h3_threshold=h3_threshold, h4_threshold=h4_threshold
        )
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

    def get_coloc_pairs_full_rows(
        self,
        variant_ids: List[int],
        h3_threshold: float = 0.0,
        h4_threshold: float = 0.8,
    ) -> tuple[List[str], List[tuple]]:
        """
        Same pairs as get_coloc_pairs_full, but returned as (column_names, row tuples) to avoid
        building a dict per row for large responses.
        """
        if not variant_ids:
            return [], []
        in_group_rows, columns = self.coloc_pairs_db.get_coloc_pairs_by_variant_ids(
            variant_ids, h3_threshold=h3_threshold, h4_threshold=h4_threshold
        )
        if not in_group_rows:
            return [], []

        a_index = columns.index("study_extraction_a_id")
        b_index = columns.index("study_extraction_b_id")
        study_extraction_ids = set()
        for row in in_group_rows:
            if row[a_index] is not None:
                study_extraction_ids.add(row[a_index])
            if row[b_index] is not None:
                study_extraction_ids.add(row[b_index])

        not_in_group_rows = []
        if study_extraction_ids:
            not_in_group_rows, _ = self.coloc_pairs_db.get_coloc_pairs_by_study_extraction_ids(
                list(study_extraction_ids)
            )

        rows = [row + (True,) for row in in_group_rows] + [row + (False,) for row in not_in_group_rows]
        return columns + ["in_coloc_group"], rows

    def get_coloc_pairs_full_columns(
        self,
        variant_ids: List[int],
        h3_threshold: float = 0.0,
        h4_threshold: float = 0.8,
    ) -> tuple[List[str], dict]:
        """
        Same pairs as get_coloc_pairs_full, but returned as (column_names, {column_name: array}).
        """
        if not variant_ids:
            return [], {}
        in_group, columns = self.coloc_pairs_db.get_coloc_pairs_by_variant_ids(
            variant_ids, h3_threshold=h3_threshold, h4_threshold=h4_threshold, columnar=True
        )
        if not columns or len(in_group[columns[0]]) == 0:
            return [], {}

        in_group["in_coloc_group"] = np.ones(len(in_group[columns[0]]), dtype=bool)
        parts = [in_group]

        study_extraction_ids = np.union1d(in_group["study_extraction_a_id"], in_group["study_extraction_b_id"])
        if len(study_extraction_ids) > 0:
            not_in_group, _ = self.coloc_pairs_db.get_coloc_pairs_by_study_extraction_ids(
                study_extraction_ids.tolist(), columnar=True
            )
            not_in_group["in_coloc_group"] = np.zeros(len(not_in_group[columns[0]]), dtype=bool)
            parts.append(not_in_group)

        column_names = columns + ["in_coloc_group"]
        return column_names, concatenate_numpy_columns(parts, column_names)

    def get_coloc_pairs_by_study_extraction_ids(
        self,
        study_extraction_ids: List[int],
        h4_threshold: float = 0.8,
    ) -> List[dict]:
        """
        Get coloc pairs that are not part of a coloc group (variant_id IS NULL),
        filtered by study extraction ids. Returns pairs where either
        study_extraction_a_id or study_extraction_b_id is in the list.
        """
        if not study_extraction_ids:
            return []
        logger.info(f"Getting coloc pairs (variant_id null) for {len(study_extraction_ids)} study extraction ids")
        pair_rows, pair_columns = self.coloc_pairs_db.get_coloc_pairs_by_study_extraction_ids(
            study_extraction_ids, h4_threshold=h4_threshold
        )
        return convert_duckdb_tuples_to_dicts(pair_rows, pair_columns)
