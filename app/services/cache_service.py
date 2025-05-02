from functools import lru_cache
from app.models.schemas import Gene, SearchTerm, Singleton, convert_duckdb_to_pydantic_model
from app.db.studies_db import StudiesDBClient
from typing import List

class DBCacheService(metaclass=Singleton):
    def __init__(self):
        self.db = StudiesDBClient()

    @lru_cache(maxsize=1)
    def get_search_terms(self) -> List[SearchTerm]:
        """
        Retrieve study names for search from DuckDB with caching.
        Returns:
            List of tuples containing (study_name, trait)
        """

        genes = self.db.get_gene_names()
        gene_search_terms = [
            SearchTerm(type="gene", name=gene[0], type_id=gene[0])
            for gene in genes if gene[0] is not None
        ]

        trait_search_terms = self.db.get_trait_names_for_search()
        trait_search_terms = [
            SearchTerm(type="study", name=term[1], type_id=term[0])
            for term in trait_search_terms if term[1] is not None
        ]

        return gene_search_terms + trait_search_terms

    @lru_cache(maxsize=1)
    def get_gene_names(self) -> List[SearchTerm]:
        """
        Retrieve genes from DuckDB with caching.
        Returns:
            List of tuples containing (gene_name, chromosome)
        """
        genes = self.db.get_gene_names()
        return [SearchTerm(type="gene", name=gene[0], type_id=gene[0]) for gene in genes]

    @lru_cache(maxsize=1)
    def get_gene_ranges(self) -> List[Gene]:
        """
        Retrieve gene ranges for a given chromosome from DuckDB with caching.
        Returns:
            List of GeneRange models containing gene information
        """
        result = self.db.get_gene_ranges()
        return convert_duckdb_to_pydantic_model(Gene, result)

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
    
    #TODO: not used yet, maybe create a study-metadata endpoint for general knowledge about the studies?
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
        self.get_tissues.cache_clear()
        self.get_search_terms.cache_clear()