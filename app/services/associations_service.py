from functools import lru_cache, wraps
from typing import List, Tuple
from app.db.associations_db import AssociationsDBClient
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


def conditional_redis_cache(min_size: int = 100, expire: int = 0, prefix: str = "associations_cache"):
    """
    Conditional wrapper that applies redis_cache only when colocs size >= min_size.

    Args:
        min_size: Minimum size of colocs list to trigger caching (default: 100)
        expire: Cache expiration time in seconds (default: 0 = never expire)
        prefix: Key prefix for Redis cache keys
    """

    def decorator(func):
        cached_func = redis_cache(expire=expire, prefix=prefix)(func)

        @wraps(func)
        def wrapper(self, colocs=None, *args, **kwargs):
            should_cache = colocs is not None and len(colocs) >= min_size

            if should_cache:
                logger.debug(f"Using cache for {func.__name__} - colocs size {len(colocs)} >= {min_size}")
                return cached_func(self, colocs, *args, **kwargs)
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
        self.redis_client = RedisClient()
        self.cache_prefix = "associations_cache"

    @lru_cache(maxsize=1)
    def get_associations_metadata(self):
        metadata = self.associations_db.get_associations_metadata()
        metadata = convert_duckdb_to_pydantic_model(AssociationMetadata, metadata)
        return metadata

    def split_association_query_by_metadata(self, snp_study_pairs: List[Tuple[int, int]]):
        associations_metadata = self.get_associations_metadata()
        metadata_to_pairs = {metadata.associations_table_name: [] for metadata in associations_metadata}

        for pair in snp_study_pairs:
            for metadata in associations_metadata:
                if metadata.start_snp_id <= pair[0] <= metadata.stop_snp_id:
                    metadata_to_pairs[metadata.associations_table_name].append(pair)
        return metadata_to_pairs

    @conditional_redis_cache(min_size=1)
    def get_associations(
        self,
        colocs: List[ColocGroup] = [],
        rare_results: List[RareResult] = [],
    ):
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
                associations, columns = self.associations_db.get_associations_by_table_name(table_name, pairs)
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
