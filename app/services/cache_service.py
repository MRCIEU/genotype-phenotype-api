from functools import lru_cache
from typing import List, Tuple

from app.db.duckdb import DuckDBClient

class CacheService:
    def __init__(self):
        self.db = DuckDBClient()

    @lru_cache(maxsize=1)
    def get_study_names_for_search(self) -> List[Tuple[str, str]]:
        """
        Retrieve study names for search from DuckDB with caching.
        Returns:
            List of tuples containing (study_name, trait)
        """
        return self.db.get_study_names_for_search()

    @lru_cache(maxsize=1)
    def get_gene_names(self) -> List[Tuple[str, str]]:
        """
        Retrieve genes from DuckDB with caching.
        Returns:
            List of tuples containing (gene_name, chromosome)
        """
        return self.db.get_gene_names()

    @lru_cache(maxsize=1)
    def get_gene_ranges(self) -> List[Tuple[str, int, int, int]]:
        """
        Retrieve gene ranges for a given chromosome from DuckDB with caching.
        Returns:
            List of tuples containing (gene_name, chr, start_position, end_position)
        """
        return self.db.get_gene_ranges()

    @lru_cache(maxsize=1)
    def get_tissues(self, ) -> List[str]:
        """
        Retrieve variants from DuckDB with caching.
        Returns:
            List of Variant instances
        """
        tissues = self.db.get_tissues()
        tissues =[tissue[0] for tissue in tissues]
        return sorted(tissues)

    def clear_cache(self):
        """Clear the LRU cache for gene ranges"""
        self.get_gene_ranges.cache_clear()
        self.get_gene_names.cache_clear()
        self.get_study_names_for_search.cache_clear()
        self.get_tissues.cache_clear()