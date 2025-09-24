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

    def split_coloc_pair_query_by_metadata(self, study_extraction_ids: List[int]):
        coloc_pairs_metadata = self.get_coloc_pairs_metadata()
        metadata_to_pairs = {metadata.coloc_pairs_table_name: [] for metadata in coloc_pairs_metadata}

        for id in study_extraction_ids:
            for metadata in coloc_pairs_metadata:
                if metadata.start_id <= id <= metadata.stop_id:
                    metadata_to_pairs[metadata.coloc_pairs_table_name].append(id)
        return metadata_to_pairs

    def get_coloc_pairs(
        self,
        study_extraction_ids: List[int],
        h4_threshold: float = 0.8,
        h3_threshold: float = 0.0,
    ):
        study_extraction_ids = study_extraction_ids or []

        logger.info(f"Getting coloc pairs for {len(study_extraction_ids)} study extraction ids")

        study_extraction_ids_by_table = self.split_coloc_pair_query_by_metadata(study_extraction_ids)
        all_coloc_pairs = []
        for table_name, ids in list(study_extraction_ids_by_table.items()):
            if len(ids) > 0:
                coloc_pair_rows, coloc_pair_columns = self.coloc_pairs_db.get_coloc_pairs_by_table_name(
                    table_name, ids, study_extraction_ids, h3_threshold, h4_threshold
                )
                coloc_pairs = convert_duckdb_tuples_to_dicts(coloc_pair_rows, coloc_pair_columns)
                all_coloc_pairs.extend(coloc_pairs)

        return all_coloc_pairs
