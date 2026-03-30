from app.models.schemas import (
    BasicTraitResponse,
    ExtendedGene,
    ExtendedStudyExtraction,
    GetTraitsResponse,
    GPMapMetadata,
    GetGenesResponse,
    SearchTerm,
    SearchTerms,
    Singleton,
    Study,
    StudyDataType,
    UploadColocPair,
    VariantType,
    convert_duckdb_to_pydantic_model,
)
from app.db.studies_db import StudiesDBClient
from app.db.redis import RedisClient
from typing import Callable, List, Optional, TypeVar
from app.logging_config import get_logger

from app.services.redis_decorator import redis_cache

T = TypeVar("T")

logger = get_logger(__name__)

studies_db_cache_prefix = "studies_db_cache"


class StudiesService(metaclass=Singleton):
    def __init__(self):
        self.db = StudiesDBClient()
        self.redis_client = RedisClient()

    @staticmethod
    def deduplicate_by_key(items: List[T], key_fn: Callable[[T], object]) -> List[T]:
        """Deduplicate items by key, preserving first occurrence order."""
        seen = {}
        result = []
        for item in items:
            key = key_fn(item)
            if key not in seen:
                seen[key] = True
                result.append(item)
        return result

    @staticmethod
    def study_extraction_ids_from_coloc_pairs(coloc_pairs: Optional[List[dict]]) -> List[int]:
        if not coloc_pairs:
            return []
        ids: set[int] = set()
        for row in coloc_pairs:
            for key in ("study_extraction_a_id", "study_extraction_b_id"):
                v = row.get(key)
                if v is not None:
                    ids.add(int(v))
        return list(ids)

    def merge_study_extractions_for_coloc_pairs(
        self,
        study_extractions: List[ExtendedStudyExtraction],
        coloc_pairs: Optional[List[dict]],
    ) -> List[ExtendedStudyExtraction]:
        """
        Append study_extractions referenced by coloc pair rows but missing from study_extractions.
        Deduplicates ids before querying studies DB.
        """
        if not coloc_pairs:
            return study_extractions
        pair_ids = self.study_extraction_ids_from_coloc_pairs(coloc_pairs)
        if not pair_ids:
            return study_extractions
        have = {e.id for e in study_extractions}
        missing = list({i for i in pair_ids if i not in have})
        if not missing:
            return study_extractions
        rows = self.db.get_study_extractions_by_id(missing)
        if not rows:
            return study_extractions
        extra = convert_duckdb_to_pydantic_model(ExtendedStudyExtraction, rows)
        if not isinstance(extra, list):
            extra = [extra]
        merged = list(study_extractions) + extra
        return StudiesService.deduplicate_by_key(merged, lambda e: e.id)

    @staticmethod
    def existing_study_extraction_ids_from_upload_coloc_pairs(
        coloc_pairs: Optional[List[UploadColocPair]],
    ) -> List[int]:
        if not coloc_pairs:
            return []
        ids: set[int] = set()
        for p in coloc_pairs:
            for eid in (p.existing_study_extraction_id_a, p.existing_study_extraction_id_b):
                if eid is not None:
                    ids.add(int(eid))
        return list(ids)

    def merge_study_extractions_for_upload_coloc_pairs(
        self,
        study_extractions: Optional[List[ExtendedStudyExtraction]],
        coloc_pairs: Optional[List[UploadColocPair]],
    ) -> List[ExtendedStudyExtraction]:
        """Like merge_study_extractions_for_coloc_pairs, for GWAS upload pair rows (studies DB ids)."""
        if not coloc_pairs:
            base: list[ExtendedStudyExtraction] = list(study_extractions or [])
            return base
        pair_ids = self.existing_study_extraction_ids_from_upload_coloc_pairs(coloc_pairs)
        if not pair_ids:
            return list(study_extractions or [])
        have = {e.id for e in (study_extractions or [])}
        missing = list({i for i in pair_ids if i not in have})
        if not missing:
            return list(study_extractions or [])
        rows = self.db.get_study_extractions_by_id(missing)
        if not rows:
            return list(study_extractions or [])
        extra = convert_duckdb_to_pydantic_model(ExtendedStudyExtraction, rows)
        if not isinstance(extra, list):
            extra = [extra]
        merged = list(study_extractions or []) + extra
        return StudiesService.deduplicate_by_key(merged, lambda e: e.id)

    @redis_cache(prefix=studies_db_cache_prefix, model_class=SearchTerms)
    def get_search_terms(self) -> SearchTerms:
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
                sample_size=None,
                ancestry=None,
                num_study_extractions=num_extractions_per_gene.get(gene[0], 0),
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
                sample_size=term[2],
                ancestry=term[3],
                num_study_extractions=num_extractions_per_study.get(term[0], 0),
                num_coloc_groups=num_coloc_groups_per_trait.get(term[0], 0),
                num_coloc_studies=num_coloc_studies_per_trait.get(term[0], 0),
                num_rare_results=num_rare_results_per_study.get(term[0], 0),
            )
            for term in trait_search_terms
            if term[1] is not None
        ]

        return SearchTerms(search_terms=gene_search_terms + trait_search_terms)

    @redis_cache(prefix=studies_db_cache_prefix, model_class=GetTraitsResponse)
    def get_traits(self) -> GetTraitsResponse:
        """
        Retrieve traits from DuckDB with caching.
        Returns:
            GetTraitsResponse instance
        """
        traits = self.db.get_traits()
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
        traits = [
            BasicTraitResponse(
                id=trait[0],
                data_type=trait[1],
                trait=trait[2],
                trait_name=trait[3],
                trait_category=trait[4],
                variant_type=trait[5],
                sample_size=trait[6],
                category=trait[7],
                ancestry=trait[8],
                heritability=trait[9],
                heritability_se=trait[10],
                num_study_extractions=num_extractions_per_study.get(trait[0], 0),
                num_coloc_groups=num_coloc_groups_per_trait.get(trait[0], 0),
                num_coloc_studies=num_coloc_studies_per_trait.get(trait[0], 0),
                num_rare_results=num_rare_results_per_study.get(trait[0], 0),
            )
            for trait in traits
        ]
        return GetTraitsResponse(traits=traits)

    @redis_cache(prefix=studies_db_cache_prefix, model_class=GetGenesResponse)
    def get_genes(self) -> GetGenesResponse:
        """
        Retrieve genes from DuckDB with caching.
        Returns:
            List of Gene instances
        """
        genes = self.db.get_genes()

        num_coloc_groups_per_gene = self.db.get_num_coloc_groups_per_gene()
        num_coloc_groups_per_gene = {
            gene_id: num_coloc_groups for gene_id, num_coloc_groups in num_coloc_groups_per_gene
        }

        num_coloc_studies_per_gene = self.db.get_num_coloc_studies_per_gene()
        num_coloc_studies_per_gene = {
            gene_id: num_coloc_studies for gene_id, num_coloc_studies in num_coloc_studies_per_gene
        }

        num_rare_results_per_gene = self.db.get_num_rare_results_per_gene()
        num_rare_results_per_gene = {
            gene_id: num_rare_results for gene_id, num_rare_results in num_rare_results_per_gene
        }

        num_extractions_per_gene = self.db.get_num_study_extractions_per_gene()
        num_extractions_per_gene = {gene_id: num_extractions for gene_id, num_extractions in num_extractions_per_gene}

        genes = [
            ExtendedGene(
                id=gene[0],
                ensembl_id=gene[1],
                gene=gene[2],
                description=gene[3],
                gene_biotype=gene[4],
                chr=gene[5],
                start=gene[6],
                stop=gene[7],
                strand=gene[8],
                source=gene[9],
                distinct_trait_categories=gene[10],
                distinct_protein_coding_genes=gene[11],
                num_study_extractions=num_extractions_per_gene.get(gene[0], 0),
                num_coloc_groups=num_coloc_groups_per_gene.get(gene[0], 0),
                num_coloc_studies=num_coloc_studies_per_gene.get(gene[0], 0),
                num_rare_results=num_rare_results_per_gene.get(gene[0], 0),
            )
            for gene in genes
        ]
        return GetGenesResponse(genes=genes)

    @redis_cache(prefix=studies_db_cache_prefix, model_class=SearchTerm)
    def get_gene_names(self) -> List[SearchTerm]:
        """
        Retrieve genes from DuckDB with caching.
        Returns:
            List of tuples containing (gene_name, chromosome)
        """
        genes = self.db.get_gene_names()
        return [SearchTerm(type="gene", name=gene[0], type_id=gene[0]) for gene in genes]

    @redis_cache(prefix=studies_db_cache_prefix)
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

    @redis_cache(prefix=studies_db_cache_prefix, model_class=GPMapMetadata)
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

        return GPMapMetadata(
            num_common_studies=num_common_studies,
            num_rare_studies=num_rare_studies,
            num_molecular_studies=num_molecular_studies,
            num_coloc_groups=coloc_groups,
            num_causal_variants=unique_snps,
        )

    def clear_cache(self):
        """Clear studies Redis cache entries (use with caution)"""
        try:
            keys = self.redis_client.redis.keys(f"{studies_db_cache_prefix}:*")
            if keys:
                self.redis_client.redis.delete(*keys)
                logger.info(f"Cleared {len(keys)} cache keys")
            else:
                logger.info("No cache keys found to clear")
        except Exception as e:
            logger.error(f"Failed to clear studies Redis cache: {e}")

    def get_studies_by_trait_ids(self, trait_ids: List[int | str]) -> List[Study]:
        """
        Retrieve studies by trait IDs from DuckDB.
        Returns:
            List of Study instances
        """
        studies = self.db.get_studies_by_trait_ids(trait_ids)

        study_models = convert_duckdb_to_pydantic_model(Study, studies)

        for study in study_models:
            if study and study.url and study.url.startswith("https://opengwas.io"):
                # Concat url with /datasets/ and the study_name
                full_url = f"{study.url.rstrip('/')}/datasets/{study.study_name}"
                study.url = self._replace_first_two_dashes_with_underscores(full_url)

        return study_models

    def _replace_first_two_dashes_with_underscores(self, x: str):
        if not x:
            return x
        dash_positions = [i for i, char in enumerate(x) if char == "-"]

        if len(dash_positions) <= 2:
            return x

        # Keep the first two dashes, replace the rest with '_'
        result = list(x)
        for i in range(2, len(dash_positions)):
            pos = dash_positions[i]
            result[pos] = "_"

        return "".join(result)
