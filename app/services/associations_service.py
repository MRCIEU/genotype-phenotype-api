from functools import wraps
from typing import List

from app.db.associations_db import AssociationsDBClient
from app.db.associations_full_db import AssociationsFullDBClient
from app.db.redis import RedisClient
from app.db.studies_db import StudiesDBClient
from app.logging_config import get_logger
from app.services.redis_decorator import redis_cache
from app.services.studies_service import StudiesService
from app.models.schemas import (
    AssociationMetadata,
    ColocGroup,
    RareResult,
    Study,
    Trait,
    VariantType,
    convert_duckdb_to_pydantic_model,
    convert_duckdb_tuples_to_dicts,
    ExtendedStudyExtraction,
)

logger = get_logger(__name__)


def associations_redis_cache(min_size: int = 100, expire: int = 0, prefix: str = "associations_cache"):
    """
    Conditional wrapper that applies redis_cache only when colocs size >= min_size.

    Args:
        min_size: Minimum size of colocs list to trigger caching (default: 100)
        expire: Cache expiration time in seconds (default: 0 = never expire)
        prefix: Key prefix for Redis cache keys
    """

    def decorator(func):
        @wraps(func)
        def wrapper(self, colocs=None, *args, **kwargs):
            should_cache = colocs is not None and len(colocs) >= min_size
            kwargs_with_cache = kwargs.copy()
            if len(args) > 1:
                study_id = args[1]
                kwargs_with_cache["cache_id"] = f"{study_id}"

            if should_cache:
                logger.debug(f"Using cache for {func.__name__} - colocs size {len(colocs)} >= {min_size}")
                return redis_cache(expire=expire, prefix=prefix)(func)(self, colocs, *args, **kwargs_with_cache)
            else:
                logger.debug(
                    f"Skipping cache for {func.__name__} - colocs size {len(colocs) if colocs else 0} < {min_size}"
                )
                return func(self, colocs, *args, **kwargs)

        return wrapper

    return decorator


class AssociationsService:
    def __init__(self):
        self.associations_db = AssociationsDBClient()
        self.associations_full_db = AssociationsFullDBClient()
        self.redis_client = RedisClient()
        self.cache_prefix = "associations_cache"
        self.full_cache_prefix = "associations_full_cache"

    @associations_redis_cache(min_size=4000, prefix="associations_cache")
    def get_associations(
        self,
        colocs: List[ColocGroup] = [],
        rare_results: List[RareResult] = [],
        study_extractions: List[ExtendedStudyExtraction] = [],
    ):
        snp_study_pairs = (
            [(coloc.variant_id, coloc.study_id) for coloc in colocs]
            + [(r.variant_id, r.study_id) for r in rare_results]
            + [(se.variant_id, se.study_id) for se in study_extractions]
        )
        associations, columns = self.associations_db.get_associations_by_snp_study_pairs(snp_study_pairs)
        associations = convert_duckdb_tuples_to_dicts(associations, columns)
        return associations

    def get_associations_by_variant_ids_and_study_ids(self, variant_ids: List[int], study_ids: List[int]):
        snp_study_pairs = [(variant_id, study_id) for variant_id in variant_ids for study_id in study_ids]
        associations, columns = self.associations_db.get_associations_by_snp_study_pairs(snp_study_pairs)
        associations = convert_duckdb_tuples_to_dicts(associations, columns)
        return associations

    def get_associations_full_metadata(self):
        metadata = self.associations_full_db.get_associations_metadata()
        metadata = convert_duckdb_to_pydantic_model(AssociationMetadata, metadata)
        return metadata

    def split_variant_ids_by_metadata(self, variant_ids: List[int]):
        associations_metadata = self.get_associations_full_metadata()
        metadata_to_variants = {metadata.associations_table_name: [] for metadata in associations_metadata}

        for variant_id in variant_ids:
            for metadata in associations_metadata:
                if metadata.start_variant_id <= variant_id <= metadata.stop_variant_id:
                    metadata_to_variants[metadata.associations_table_name].append(variant_id)
                    break
        return metadata_to_variants

    def _fetch_associations_full_for_variant_ids_and_study_ids(
        self,
        variant_ids: List[int],
        study_ids: List[int],
    ) -> list[dict]:
        if not variant_ids:
            return []

        study_ids_set = set(study_ids)
        variants_by_table = self.split_variant_ids_by_metadata(variant_ids)
        all_associations = []
        for table_name, table_variant_ids in variants_by_table.items():
            if not table_variant_ids:
                continue
            associations, columns = self.associations_full_db.get_associations_by_table_name_and_variant_ids(
                table_name, table_variant_ids
            )
            associations = convert_duckdb_tuples_to_dicts(associations, columns)
            all_associations.extend(associations)

        logger.info(
            f"Fetched {len(all_associations)} full association rows for {len(variant_ids)} variants"
        )

        filtered_associations = [
            association for association in all_associations if association["study_id"] in study_ids_set
        ]
        logger.info(
            f"Returning {len(filtered_associations)} full association rows "
            f"after filtering to {len(study_ids_set)} studies"
        )
        return filtered_associations

    def get_associations_full(self, trait_id: int) -> list[dict] | None:
        studies_db = StudiesDBClient()
        if studies_db.get_trait(trait_id) is None:
            return None
        return self._get_associations_full_cached(trait_id=trait_id, cache_id=str(trait_id))

    @redis_cache(expire=0, prefix="associations_full_cache")
    def _get_associations_full_cached(self, trait_id: int, cache_id: str = None):
        studies_db = StudiesDBClient()
        studies_service = StudiesService()

        trait = convert_duckdb_to_pydantic_model(Trait, studies_db.get_trait(trait_id))
        studies = studies_service.get_studies_by_trait_ids([trait.id])

        common_study = None
        rare_study = None
        for study in studies:
            if study.variant_type == VariantType.common.value:
                common_study = study
            else:
                rare_study = study

        study_ids = [study.id for study in [common_study, rare_study] if study is not None]
        trait_study_ids = set(study_ids)

        rare_results = []
        if rare_study is not None:
            rare_results_data = studies_db.get_rare_results_for_study_id(rare_study.id)
            if rare_results_data:
                rare_results = convert_duckdb_to_pydantic_model(RareResult, rare_results_data)

        colocs = []
        study_extractions = []
        if study_ids:
            colocs_data = studies_db.get_all_colocs_for_study_ids(study_ids)
            if colocs_data:
                colocs = convert_duckdb_to_pydantic_model(ColocGroup, colocs_data)

            study_extractions_data = studies_db.get_study_extractions_for_studies(study_ids)
            if study_extractions_data:
                study_extractions = convert_duckdb_to_pydantic_model(ExtendedStudyExtraction, study_extractions_data)

        variant_ids = {coloc.variant_id for coloc in colocs}
        for rare_result in rare_results:
            variant_ids.add(rare_result.variant_id)
        for study_extraction in study_extractions:
            variant_ids.add(study_extraction.variant_id)

        study_ids_set = {coloc.study_id for coloc in colocs} | trait_study_ids

        if not variant_ids or not study_ids_set:
            return []

        linked_studies_data = studies_db.get_studies_by_id(list(study_ids_set))
        linked_studies = convert_duckdb_to_pydantic_model(Study, linked_studies_data)
        if not isinstance(linked_studies, list):
            linked_studies = [linked_studies] if linked_studies else []
        linked_trait_ids = {study.trait_id for study in linked_studies if study.trait_id is not None}

        variant_ids_list = sorted(variant_ids)
        study_ids_list = sorted(study_ids_set)

        logger.info(
            f"Getting full associations for trait {trait_id}: "
            f"{len(linked_trait_ids)} linked trait ids, "
            f"{len(variant_ids_list)} variant ids, "
            f"{len(study_ids_list)} study ids"
        )
        associations = self._fetch_associations_full_for_variant_ids_and_study_ids(
            variant_ids_list, study_ids_list
        )
        logger.info(f"Returning {len(associations)} full associations for trait {trait_id}")
        return associations

    def clear_cache(self):
        """Clear associations Redis cache entries (use with caution)"""
        try:
            cleared = 0
            for prefix in (self.cache_prefix, self.full_cache_prefix):
                keys = self.redis_client.redis.keys(f"{prefix}:*")
                if keys:
                    self.redis_client.redis.delete(*keys)
                    cleared += len(keys)
            if cleared:
                logger.info(f"Cleared {cleared} associations cache keys")
            else:
                logger.info("No associations cache keys found to clear")
        except Exception as e:
            logger.error(f"Failed to clear associations Redis cache: {e}")
