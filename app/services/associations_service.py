from typing import List
from app.db.associations_db import AssociationsDBClient
from app.logging_config import get_logger
from app.models.schemas import (
    Association,
    ColocGroup,
    ExtendedStudyExtraction,
    RareResult,
    Variant,
    convert_duckdb_to_pydantic_model,
)

logger = get_logger(__name__)


class AssociationsService:
    def __init__(self):
        self.associations_db = AssociationsDBClient()

    def get_associations(
        self,
        study_extractions: List[ExtendedStudyExtraction] = [],
        colocs: List[ColocGroup] = [],
        rare_results: List[RareResult] = [],
    ):
        study_extractions = study_extractions or []
        colocs = colocs or []
        rare_results = rare_results or []

        snp_study_pairs = (
            [(s.snp_id, s.study_id) for s in study_extractions]
            + [(coloc.snp_id, coloc.study_id) for coloc in colocs]
            + [(r.snp_id, r.study_id) for r in rare_results]
        )
        logger.info(f"Getting associations for {len(snp_study_pairs)} SNP-study pairs")

        associations = self.associations_db.get_associations_by_snp_study_pairs(snp_study_pairs)
        associations = convert_duckdb_to_pydantic_model(Association, associations)

        return associations

    def flip_association_data_to_effect_allele(self, variants: List[Variant]):
        # TODO: Do we do it via flipped or via eaf?  I think we do it via flipped for consistency?
        for variant in variants:
            if variant.flipped:
                for association in variant.associations:
                    if association.eaf > 0.5:
                        association.beta = -association.beta
                        association.eaf = 1 - association.eaf
