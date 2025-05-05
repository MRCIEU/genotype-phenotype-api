from app.config import get_settings
from functools import lru_cache, wraps
from typing import List, Tuple
import duckdb
import time
import logging

from app.models.schemas import StudyDataTypes, VariantTypes

settings = get_settings()

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def log_performance(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            end_time = time.time()
            execution_time = (end_time - start_time) * 1000
            logger.debug(f"{func.__name__} took {execution_time:.2f}ms to execute")
    return wrapper

@lru_cache()
def get_gpm_db_connection():
    return duckdb.connect(settings.STUDIES_DB_PATH, read_only=True)

class StudiesDBClient:
    def __init__(self):
        self.studies_conn = get_gpm_db_connection()

    def get_trait(self, trait_id: str):
        query = f"SELECT * FROM traits WHERE id = '{trait_id}'"
        return self.studies_conn.execute(query).fetchone()
    
    @log_performance
    def get_study_metadata(self):
        query = """
            SELECT data_type, variant_type, COUNT(*) as count
            FROM studies
            GROUP BY data_type, variant_type
            ORDER BY data_type, variant_type
        """

        return self.studies_conn.execute(query).fetchall()

    def get_studies(self, limit: int = None):
        if (limit is None):
            query = "SELECT * FROM studies"
        else:
            query = f"SELECT * FROM studies LIMIT {limit}"
        
        return self.studies_conn.execute(query).fetchall()

    @log_performance
    def get_study(self, study_id: str):
        query = f"SELECT * FROM studies WHERE id = '{study_id}'"
        return self.studies_conn.execute(query).fetchone()
    
    @log_performance
    def get_studies_by_trait_id(self, trait_id: str):
        query = f"SELECT * FROM studies WHERE trait_id = '{trait_id}'"
        return self.studies_conn.execute(query).fetchall()

    @log_performance
    def get_studies_by_id(self, study_ids: List[int]):
        formatted_ids = ','.join(
            f"({i}, {id if id is not None else 'NULL'})" 
            for i, id in enumerate(study_ids)
        )
        query = f"""
            WITH input_studies AS (
                SELECT * FROM (VALUES {formatted_ids}) as t(row_num, id)
            )
            SELECT studies.*
            FROM input_studies
            LEFT JOIN studies ON COALESCE(input_studies.id, -1) = COALESCE(studies.id, -1)
            ORDER BY input_studies.row_num
        """
        return self.studies_conn.execute(query).fetchall()

    def _fetch_colocs(self, condition: str):
        # TODO: Remove this once we filter colocs when creating the db
        query = f"""
            SELECT colocalisations.*, traits.id as trait_id, traits.trait_name, studies.data_type, studies.tissue 
            FROM colocalisations 
            JOIN studies ON colocalisations.study_id = studies.id
            JOIN traits ON studies.trait_id = traits.id
            WHERE colocalisations.coloc_group_id IN (SELECT DISTINCT coloc_group_id FROM colocalisations WHERE {condition})
            AND colocalisations.posterior_prob IS NOT NULL AND colocalisations.posterior_prob > 0.5
        """
        return self.studies_conn.execute(query).fetchall()

    @log_performance
    def get_colocs_for_variant(self, snp_id: int):
        return self._fetch_colocs(f"snp_id = {snp_id}")

    @log_performance
    def get_colocs_for_variants(self, snp_ids: List[int]):
        formatted_snp_ids = ','.join(f"{snp_id}" for snp_id in snp_ids)
        return self._fetch_colocs(f"snp_id IN ({formatted_snp_ids})")

    @log_performance
    def get_all_colocs_for_gene(self, symbol: str):
        return self._fetch_colocs(f"known_gene = '{symbol}' AND cis_trans = 'cis'")

    @log_performance
    def get_all_colocs_for_ld_block(self, ld_block_id: int):
        return self._fetch_colocs(f"ld_block_id = {ld_block_id}")

    @log_performance
    def get_all_colocs_for_study(self, study_id: str):
        return self._fetch_colocs(f"study_id = '{study_id}'")
    
    @log_performance
    def get_all_colocs_for_study_extraction_ids(self, study_extraction_ids: List[int]):
        formatted_ids = ','.join(f"{id}" for id in study_extraction_ids)
        return self._fetch_colocs(f"study_extraction_id IN ({formatted_ids})")
    
    def _fetch_rare_results(self, condition: str):
        query = f"""
            SELECT rare_results.*, traits.id as trait_id, traits.trait_name, studies.data_type, studies.tissue
            FROM rare_results
            JOIN studies ON rare_results.study_id = studies.id
            JOIN traits ON studies.trait_id = traits.id
            WHERE rare_results.rare_result_group_id IN (SELECT DISTINCT rare_result_group_id FROM rare_results WHERE {condition})
        """
        return self.studies_conn.execute(query).fetchall()

    @log_performance
    def get_rare_results_for_gene(self, symbol: str):
        return self._fetch_rare_results(f"known_gene = '{symbol}'")
    
    @log_performance
    def get_rare_results_for_study_extraction_ids(self, study_extraction_ids: List[int]):
        formatted_ids = ','.join(f"{id}" for id in study_extraction_ids)
        return self._fetch_rare_results(f"study_extraction_id IN ({formatted_ids})")
    
    @log_performance
    def get_rare_results_for_variants(self, snp_ids: List[int]):
        formatted_ids = ','.join(f"{snp_id}" for snp_id in snp_ids)
        return self._fetch_rare_results(f"snp_id IN ({formatted_ids})")
    
    @log_performance
    def get_rare_results_for_study_ids(self, study_ids: List[int]):
        formatted_ids = ','.join(f"{id}" for id in study_ids)
        return self._fetch_rare_results(f"study_id IN ({formatted_ids})")

    @log_performance
    def get_trait_names_for_search(self):
        return self.studies_conn.execute(f"""
            SELECT traits.id, traits.trait_name
            FROM traits
            JOIN studies ON traits.id = studies.trait_id 
            WHERE traits.data_type = '{StudyDataTypes.PHENOTYPE.value}' AND studies.variant_type = '{VariantTypes.COMMON.value}'
        """).fetchall()

    @log_performance
    def get_gene_names(self):
        return self.studies_conn.execute(
            "SELECT DISTINCT known_gene FROM study_extractions"
        ).fetchall()

    @log_performance
    def get_study_extractions_for_study(self, study_id: str):
        query = f"""
            SELECT study_extractions.*, traits.id as trait_id, traits.trait_name, studies.data_type, studies.tissue
            FROM study_extractions 
            JOIN studies ON study_extractions.study_id = studies.id
            JOIN traits ON studies.trait_id = traits.id
            WHERE study_extractions.study_id = '{study_id}'
        """
        return self.studies_conn.execute(query).fetchall()

    @log_performance
    def get_study_extractions(self, unique_study_id: str = None):
        if unique_study_id:
            query = f"""
                SELECT * FROM study_extractions WHERE unique_study_id = '{unique_study_id}'
            """
        else:
            query = f"""
                SELECT * FROM study_extractions
            """
        return self.studies_conn.execute(query).fetchall()

    @log_performance
    def get_study_extractions_by_id(self, ids: List[int]):
        formatted_ids = ','.join(f"{id}" for id in ids)
        query = f"""
            SELECT study_extractions.*, traits.id as trait_id, traits.trait_name, studies.data_type, studies.tissue
            FROM study_extractions
            JOIN studies ON study_extractions.study_id = studies.id
            JOIN traits ON studies.trait_id = traits.id
            WHERE study_extractions.id IN ({formatted_ids})
        """
        return self.studies_conn.execute(query).fetchall()

    @log_performance
    def get_study_extractions_by_unique_study_id(self, unique_study_ids: List[str]):
        values_list = ", ".join([f"({i}, '{v}')" for i, v in enumerate(unique_study_ids)])
        query = f"""
            WITH input_studies AS (
                SELECT * FROM (VALUES {values_list}) as t(row_num, unique_study_id)
            )
            SELECT study_extractions.*
            FROM input_studies 
            LEFT JOIN study_extractions ON input_studies.unique_study_id = study_extractions.unique_study_id
            ORDER BY input_studies.row_num
        """
        return self.studies_conn.execute(query).fetchall()

    @log_performance
    def get_study_extractions_in_region(self, chr: str, bp_start: int, bp_end: int, symbol: str):
        return self.studies_conn.execute(
            """SELECT study_extractions.*, traits.id as trait_id, traits.trait_name, studies.data_type, studies.tissue
            FROM study_extractions 
            JOIN studies ON study_extractions.study_id = studies.id
            JOIN traits ON studies.trait_id = traits.id
            WHERE (study_extractions.chr = ? AND study_extractions.bp BETWEEN ? AND ?)
               OR (study_extractions.known_gene = ? AND study_extractions.cis_trans = 'cis')
            """,
            (chr, bp_start, bp_end, symbol)
        ).fetchall()

    @log_performance
    def get_ld_block(self, ld_block_id: int):
        query = f"SELECT * FROM ld_blocks WHERE id = {ld_block_id}"
        return self.studies_conn.execute(query).fetchone()

    @log_performance
    def get_ld_blocks_by_ld_block(self, ld_blocks: List[str]):
        values_list = ", ".join([f"({i}, '{v}')" for i, v in enumerate(ld_blocks)])
        query = f"""
            WITH input_blocks AS (
                SELECT * FROM (VALUES {values_list}) as t(row_num, ld_block)
            )
            SELECT ld_blocks.* 
            FROM input_blocks 
            LEFT JOIN ld_blocks ON input_blocks.ld_block = ld_blocks.ld_block
            ORDER BY input_blocks.row_num
        """
        return self.studies_conn.execute(query).fetchall()

    @log_performance
    def get_gene(self, symbol: str):
        query = f"""
        SELECT DISTINCT 
            ANY_VALUE(snp_annotations.symbol) as symbol, 
            ANY_VALUE(snp_annotations.chr) as chr, 
            MIN(snp_annotations.bp) as min_bp, 
            MAX(snp_annotations.bp) as max_bp
        FROM snp_annotations 
        JOIN study_extractions ON snp_annotations.symbol = study_extractions.known_gene
        WHERE snp_annotations.symbol = '{symbol}'
        GROUP BY snp_annotations.symbol
        """
        return self.studies_conn.execute(query).fetchone()

    @log_performance
    def get_variant(self, snp_id: int):
        query = f"SELECT * FROM snp_annotations WHERE id = {snp_id}"
        return self.studies_conn.execute(query).fetchone()
    
    @log_performance
    def get_gene_ranges(self):
        query = f"""
        SELECT DISTINCT 
            ANY_VALUE(snp_annotations.symbol) as symbol, 
            ANY_VALUE(snp_annotations.chr) as chr, 
            MIN(snp_annotations.bp) as min_bp, 
            MAX(snp_annotations.bp) as max_bp
        FROM snp_annotations 
        JOIN study_extractions ON snp_annotations.symbol = study_extractions.known_gene
        WHERE snp_annotations.symbol IS NOT NULL 
        GROUP BY snp_annotations.symbol
        """
        return self.studies_conn.execute(query).fetchall()

    @log_performance
    def get_variants(self, snp_ids: List[int] = None, variants: List[str] = None, variant_prefixes: List[str] = None, rsids: List[str] = None, grange: List[str] = None):
        if not snp_ids and not variants and not variant_prefixes and not rsids and not grange:
            return []

        query = "SELECT * FROM snp_annotations WHERE "
        if snp_ids:
            formatted_snp_ids = ','.join(f"{snp_id}" for snp_id in snp_ids)
            query += f"id IN ({formatted_snp_ids})"
        elif rsids:
            formatted_rsids = ','.join(f"'{rsid}'" for rsid in rsids)
            query += f"rsid IN ({formatted_rsids})"
        elif grange:
            chr, position = grange.split(":")
            start_bp, end_bp = position.split("-")
            start_bp, end_bp = int(start_bp), int(end_bp)
            query += f"""chr = {chr} AND bp BETWEEN {start_bp} AND {end_bp}"""
        elif variants:
            formatted_variants = ','.join(f"'{variant}'" for variant in variants)
            query += f"snp IN ({formatted_variants})"
        elif variant_prefixes:
            formatted_variant_prefixes = ','.join(f"'{variant_prefix}'" for variant_prefix in variant_prefixes)
            query += f"SPLIT_PART(snp, '_', 1) IN ({formatted_variant_prefixes})"

        return self.studies_conn.execute(query).fetchall()

    @log_performance
    def get_tissues(self):
        return self.studies_conn.execute("SELECT DISTINCT tissue FROM studies WHERE tissue IS NOT NULL").fetchall()

    @log_performance
    def get_variants_by_snp_strings(self, variants: List[str]):
        values_list = ", ".join([f"({i}, '{v}')" for i, v in enumerate(variants)])
        query = f"""
            WITH input_variants AS (
                SELECT * FROM (VALUES {values_list}) as t(row_num, variant)
            )
            SELECT snp_annotations.* 
            FROM input_variants 
            LEFT JOIN snp_annotations ON input_variants.variant = snp_annotations.snp 
            ORDER BY input_variants.row_num
        """
        
        return self.studies_conn.execute(query).fetchall()
    
    @log_performance
    def get_snp_ids_by_snps(self, snps: List[str]):
        formatted_snps = ','.join(f"'{snp}'" for snp in snps)
        query = f"SELECT id FROM snp_annotations WHERE id IN ({formatted_snps})"
        return self.studies_conn.execute(query).fetchall()
    
    @log_performance
    def get_coloc_metadata(self):
        query = """
            SELECT MAX(coloc_group_id) as count FROM colocalisations 
        """
        coloc_groups = self.studies_conn.execute(query).fetchone()

        query = """
            SELECT COUNT(DISTINCT snp_id) as count
            FROM colocalisations
        """
        unique_snps = self.studies_conn.execute(query).fetchone()
        return coloc_groups[0], unique_snps[0]
    