from functools import lru_cache
from typing import List, Tuple
from app.db.associations_db import AssociationsDBClient
from app.logging_config import get_logger
from app.models.schemas import (
    Association,
    AssociationMetadata,
    ColocGroup,
    RareResult,
    Variant,
    convert_duckdb_to_pydantic_model,
)

logger = get_logger(__name__)


class AssociationsService:
    def __init__(self):
        self.associations_db = AssociationsDBClient()
        self.associations_metadata = self.get_associations_metadata()
        self.metadata_to_pairs = {metadata.associations_table_name: [] for metadata in self.associations_metadata}
    
    @lru_cache(maxsize=1)
    def get_associations_metadata(self):
        metadata = self.associations_db.get_associations_metadata()
        metadata = convert_duckdb_to_pydantic_model(AssociationMetadata, metadata)
        return metadata
    
    def split_association_query_by_metadata(self, snp_study_pairs: List[Tuple[int, int]]):
        metadata_to_pairs = self.metadata_to_pairs.copy()
        
        for pair in snp_study_pairs:
            for metadata in self.associations_metadata:
                if metadata.start_snp_id <= pair[0] <= metadata.stop_snp_id:
                    metadata_to_pairs[metadata.associations_table_name].append(pair)
        return metadata_to_pairs

    def get_associations(
        self,
        colocs: List[ColocGroup] = [],
        rare_results: List[RareResult] = [],
    ):
        colocs = colocs or []
        rare_results = rare_results or []

        snp_study_pairs = (
            [(coloc.snp_id, coloc.study_id) for coloc in colocs]
            + [(r.snp_id, r.study_id) for r in rare_results]
        )
        logger.info(f"Getting associations for {len(snp_study_pairs)} SNP-study pairs")

        snp_study_pairs_by_table = self.split_association_query_by_metadata(snp_study_pairs)
        all_associations = []
        for table_name, pairs in list(snp_study_pairs_by_table.items()):
            if len(pairs) > 0:
                associations = self.associations_db.get_associations_by_table_name(table_name, pairs)
                associations = convert_duckdb_to_pydantic_model(Association, associations)
                all_associations.extend(associations)
        return all_associations


    def flip_association_data_to_effect_allele(self, variants: List[Variant]):
        # TODO: Do we do it via flipped or via eaf?  I think we do it via flipped for consistency?
        for variant in variants:
            if variant.flipped:
                for association in variant.associations:
                    if association.eaf > 0.5:
                        association.beta = -association.beta
                        association.eaf = 1 - association.eaf
