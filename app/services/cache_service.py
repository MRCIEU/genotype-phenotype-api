from functools import lru_cache
from app.models.schemas import GPMapMetadata, Gene, SearchTerm, Singleton, StudyDataTypes, VariantTypes, convert_duckdb_to_pydantic_model
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
    def get_genes(self) -> List[Gene]:
        """
        Retrieve genes from DuckDB with caching.
        Returns:
            List of Gene instances
        """
        genes = self.db.get_genes()
        return convert_duckdb_to_pydantic_model(Gene, genes)

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
    def get_gpmap_metadata(self) -> GPMapMetadata:
        """
        Retrieve study metadata from DuckDB with caching, grouped by data_type and variant_type.
        Returns:
            Dictionary with nested structure: {data_type: {variant_type: count}}
        """
        num_common_studies = 0
        num_rare_studies = 0
        num_molecular_studies = 0

        coloc_groups, unique_snps = self.db.get_coloc_metadata()
        common_studies = self.db.get_study_metadata()

        for study in common_studies:
            if study[0] == StudyDataTypes.PHENOTYPE.value and study[1] == VariantTypes.COMMON.value:
                num_common_studies += study[2]
            elif study[0] == StudyDataTypes.PHENOTYPE.value and study[1] == VariantTypes.RARE_EXOME.value:
                num_rare_studies += study[2]
            elif study[0] != StudyDataTypes.PHENOTYPE.value:
                num_molecular_studies += study[2]

        gpmap_metadata = GPMapMetadata(
            num_common_studies=num_common_studies,
            num_rare_studies=num_rare_studies,
            num_molecular_studies=num_molecular_studies,
            num_coloc_groups=coloc_groups,
            num_causal_variants=unique_snps,
        )
        return gpmap_metadata

    def clear_cache(self):
        """Clear the LRU cache for gene ranges"""
        self.get_gpmap_metadata.cache_clear()
        self.get_gene_info.cache_clear()
        self.get_gene_names.cache_clear()
        self.get_tissues.cache_clear()
        self.get_search_terms.cache_clear()