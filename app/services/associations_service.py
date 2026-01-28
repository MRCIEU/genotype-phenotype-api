from functools import lru_cache, wraps
from typing import List, Tuple
from app.db.associations_db import AssociationsDBClient
from app.db.associations_full_db import AssociationsFullDBClient
from app.db.redis import RedisClient
from app.logging_config import get_logger
from app.services.redis_decorator import redis_cache
from app.models.schemas import (
    AssociationMetadata,
    ColocGroup,
    RareResult,
    convert_duckdb_to_pydantic_model,
    convert_duckdb_tuples_to_dicts,
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

    def get_associations(self, colocs: List[ColocGroup] = [], rare_results: List[RareResult] = []):
        snp_study_pairs = [(coloc.snp_id, coloc.study_id) for coloc in colocs] + [
            (r.snp_id, r.study_id) for r in rare_results
        ]
        associations, columns = self.associations_db.get_associations_by_snp_study_pairs(snp_study_pairs)
        associations = convert_duckdb_tuples_to_dicts(associations, columns)
        return associations

    def get_associations_by_snp_ids_and_study_ids(self, snp_ids: List[int], study_ids: List[int]):
        snp_study_pairs = [(snp_id, study_id) for snp_id in snp_ids for study_id in study_ids]
        associations, columns = self.associations_db.get_associations_by_snp_study_pairs(snp_study_pairs)
        associations = convert_duckdb_tuples_to_dicts(associations, columns)
        return associations

    @lru_cache(maxsize=1)
    def get_associations_full_metadata(self):
        raise Exception("associations_full_db is not currently used")
        metadata = self.associations_full_db.get_associations_metadata()
        metadata = convert_duckdb_to_pydantic_model(AssociationMetadata, metadata)
        return metadata

    def split_association_query_by_metadata(self, snp_study_pairs: List[Tuple[int, int]]):
        raise Exception("associations_full_db is not currently used")
        associations_metadata = self.get_associations_full_metadata()
        metadata_to_pairs = {metadata.associations_table_name: [] for metadata in associations_metadata}

        for pair in snp_study_pairs:
            for metadata in associations_metadata:
                if metadata.start_snp_id <= pair[0] <= metadata.stop_snp_id:
                    metadata_to_pairs[metadata.associations_table_name].append(pair)
        return metadata_to_pairs

    @associations_redis_cache(min_size=10000)
    def get_associations_full(self, colocs: List[ColocGroup] = [], rare_results: List[RareResult] = []):
        raise Exception("associations_full_db is not currently used")
        colocs = colocs or []
        rare_results = rare_results or []

        snp_study_pairs = [(coloc.snp_id, coloc.study_id) for coloc in colocs] + [
            (r.snp_id, r.study_id) for r in rare_results
        ]
        logger.info(f"Getting associations for {len(snp_study_pairs)} SNP-study pairs")

        snp_study_pairs_by_table = self.split_association_query_by_metadata(snp_study_pairs)
        all_associations = []
        for table_name, pairs in list(snp_study_pairs_by_table.items()):
            if len(pairs) > 0:
                associations, columns = self.associations_full_db.get_associations_by_table_name(table_name, pairs)
                associations = convert_duckdb_tuples_to_dicts(associations, columns)
                all_associations.extend(associations)

        # Filter associations to only include those that match the original snp_study_pairs
        filtered_associations = []
        snp_study_pairs_set = set(snp_study_pairs)
        for association in all_associations:
            if (association["snp_id"], association["study_id"]) in snp_study_pairs_set:
                filtered_associations.append(association)

        logger.info(f"Returning {len(filtered_associations)} associations for {len(snp_study_pairs)}")
        return filtered_associations

    def get_associations_full_by_study_ids(self, snp_ids: List[int], study_ids: List[int]):
        raise Exception("associations_full_db is not currently used")

        snp_study_pairs = [(snp_id, study_id) for snp_id in snp_ids for study_id in study_ids]
        snp_study_pairs_by_table = self.split_association_query_by_metadata(snp_study_pairs)
        all_associations = []
        for table_name, pairs in list(snp_study_pairs_by_table.items()):
            if len(pairs) > 0:
                associations, columns = self.associations_full_db.get_associations_by_table_name(table_name, pairs)
                associations = convert_duckdb_tuples_to_dicts(associations, columns)
                all_associations.extend(associations)

        logger.info(
            f"Returning {len(all_associations)} associations for {len(snp_ids)} SNPs and {len(study_ids)} studies"
        )
        return all_associations

    def clear_cache(self):
        """Clear associations Redis cache entries (use with caution)"""
        try:
            keys = self.redis_client.redis.keys(f"{self.cache_prefix}:*")
            if keys:
                self.redis_client.redis.delete(*keys)
                logger.info(f"Cleared {len(keys)} cache keys")
            else:
                logger.info("No cache keys found to clear")
        except Exception as e:
            logger.error(f"Failed to clear associations Redis cache: {e}")
