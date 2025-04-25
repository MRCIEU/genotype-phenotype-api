from functools import lru_cache
from typing import List, Tuple
from app.models.schemas import Singleton
from app.db.studies_db import StudiesDBClient


class CacheService(metaclass=Singleton):
    def __init__(self):
        self.db = StudiesDBClient()

    @lru_cache(maxsize=1)
    def get_study_names_for_search(self) -> List[Tuple[str, str]]:
        """
        Retrieve study names for search from DuckDB with caching.
        Returns:
            List of tuples containing (study_name, trait)
        """
        return self.db.get_study_names_for_search()
    
    def get_variant_prefixes(self) -> List[str]:
        """
        Retrieve variant prefixes from DuckDB with caching.
        Returns:
            List of variant prefixes
        """
        return self.db.get_variant_prefixes()

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
    
    @lru_cache(maxsize=1)
    def get_study_metadata(self) -> dict:
        """
        Retrieve study metadata from DuckDB with caching, grouped by data_type and variant_type.
        Returns:
            Dictionary with nested structure: {data_type: {variant_type: count}}
        """
        study_data = self.db.get_study_metadata()
        coloc_metadata, unique_snps = self.db.get_coloc_metadata()
        
        # Create a nested dictionary to group by data_type and variant_type
        grouped_data = {}
        
        for row in study_data:
            data_type = row[0] if row[0] else "unknown"
            variant_type = row[1] if row[1] else "unknown"
            count = row[2]
            
            if data_type not in grouped_data:
                grouped_data[data_type] = {}
            
            grouped_data[data_type][variant_type] = count
        
        return grouped_data

    def clear_cache(self):
        """Clear the LRU cache for gene ranges"""
        self.get_gene_ranges.cache_clear()
        self.get_gene_names.cache_clear()
        self.get_study_names_for_search.cache_clear()
        self.get_tissues.cache_clear()