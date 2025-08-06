from functools import lru_cache
from app.models.schemas import (
    GPMapMetadata,
    Gene,
    SearchTerm,
    Singleton,
    StudyDataType,
    VariantType,
    convert_duckdb_to_pydantic_model,
)
from app.db.studies_db import StudiesDBClient
from typing import List
from app.logging_config import get_logger

logger = get_logger(__name__)


class DBCacheService(metaclass=Singleton):
    def __init__(self):
        self.db = StudiesDBClient()

    @lru_cache(maxsize=1)
    def get_search_terms(self) -> List[SearchTerm]:
        """
        Retrieve trait and gene names for search from DuckDB with caching.
        Returns:
            List of tuples containing (study_name, trait)
        """

        num_coloc_groups_per_gene = self.db.get_num_coloc_groups_per_gene()
        num_coloc_groups_per_gene = {
            gene_id: num_coloc_groups for gene_id, num_coloc_groups in num_coloc_groups_per_gene
        }

        num_coloc_studies_per_gene = self.db.get_num_coloc_studies_per_gene()
        num_coloc_studies_per_gene = {
            gene_id: num_coloc_studies for gene_id, num_coloc_studies in num_coloc_studies_per_gene
        }

        num_extractions_per_gene = self.db.get_num_study_extractions_per_gene()
        num_extractions_per_gene = {gene_id: num_extractions for gene_id, num_extractions in num_extractions_per_gene}

        num_rare_results_per_gene = self.db.get_num_rare_results_per_gene()
        num_rare_results_per_gene = {
            gene_id: num_rare_results for gene_id, num_rare_results in num_rare_results_per_gene
        }

        genes = self.db.get_gene_names()
        gene_search_terms = [
            SearchTerm(
                type="gene",
                name=gene[0],
                alt_name=gene[1],
                type_id=gene[0],
                num_extractions=num_extractions_per_gene.get(gene[0], 0),
                num_coloc_groups=num_coloc_groups_per_gene.get(gene[0], 0),
                num_coloc_studies=num_coloc_studies_per_gene.get(gene[0], 0),
                num_rare_results=num_rare_results_per_gene.get(gene[0], 0),
            )
            for gene in genes
            if gene[0] is not None
        ]

        num_extractions_per_study = self.db.get_num_study_extractions_per_study()
        num_extractions_per_study = {
            study_id: num_extractions for study_id, num_extractions in num_extractions_per_study
        }

        coloc_groups_per_trait = self.db.get_num_coloc_groups_per_trait()
        num_coloc_groups_per_trait = {
            trait_id: num_coloc_groups for trait_id, num_coloc_groups in coloc_groups_per_trait
        }
        coloc_studies_per_trait = self.db.get_num_coloc_studies_per_trait()
        num_coloc_studies_per_trait = {
            trait_id: num_coloc_studies for trait_id, num_coloc_studies in coloc_studies_per_trait
        }

        num_rare_results_per_study = self.db.get_num_rare_results_per_study()
        num_rare_results_per_study = {
            study_id: num_rare_results for study_id, num_rare_results in num_rare_results_per_study
        }

        trait_search_terms = self.db.get_trait_names_for_search()
        trait_search_terms = [
            SearchTerm(
                type="trait",
                name=term[1],
                alt_name=None,
                type_id=term[0],
                num_extractions=num_extractions_per_study.get(term[0], 0),
                num_coloc_groups=num_coloc_groups_per_trait.get(term[0], 0),
                num_coloc_studies=num_coloc_studies_per_trait.get(term[0], 0),
                num_rare_results=num_rare_results_per_study.get(term[0], 0),
            )
            for term in trait_search_terms
            if term[1] is not None
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
    def get_tissues(
        self,
    ) -> List[str]:
        """
        Retrieve variants from DuckDB with caching.
        Returns:
            List of Variant instances
        """
        tissues = self.db.get_tissues()
        tissues = [tissue[0] for tissue in tissues]
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
            if study[0] == StudyDataType.phenotype.name and study[1] == VariantType.common.name:
                num_common_studies += study[2]
            elif study[0] == StudyDataType.phenotype.name and study[1] == VariantType.rare_exome.name:
                num_rare_studies += study[2]
            elif study[0] != StudyDataType.phenotype.name:
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
