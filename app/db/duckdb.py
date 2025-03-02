from typing import List
import duckdb
from functools import lru_cache
from app.config import get_settings
from functools import lru_cache
settings = get_settings()

@lru_cache()
def get_studies_db_connection():
    return duckdb.connect(settings.DB_STUDIES_PATH)

@lru_cache()
def get_associations_db_connection():
    return duckdb.connect(settings.DB_ASSOCIATIONS_PATH)

class DuckDBClient:
    def __init__(self):
        self.studies_conn = get_studies_db_connection()
        self.associations_conn = get_associations_db_connection()

    def get_studies(self, limit: int = None):
        if (limit is None):
            query = "SELECT * FROM studies_processed"
        else:
            query = f"SELECT * FROM studies_processed LIMIT {limit}"
        
        return self.studies_conn.execute(query).fetchall()

    def get_study(self, study_id: str):
        query = f"SELECT * FROM studies_processed WHERE study_name = '{study_id}'"
        return self.studies_conn.execute(query).fetchone()

    def _fetch_colocs(self, condition: str):
        # TODO: Remove this once we filter colocs when creating the db
        query = f"""
            SELECT coloc.*, studies_processed.trait, studies_processed.data_type, studies_processed.tissue 
            FROM coloc 
            JOIN studies_processed ON coloc.study = studies_processed.study_name 
            WHERE coloc.id IN (SELECT DISTINCT id FROM coloc WHERE {condition})
            AND coloc.posterior_prob IS NOT NULL AND coloc.posterior_prob > 0.5
        """
        return self.studies_conn.execute(query).fetchall()

    def get_colocs_for_variant(self, variant_id: str):
        return self._fetch_colocs(f"candidate_snp = '{variant_id}'")

    def get_all_colocs_for_gene(self, symbol: str):
        return self._fetch_colocs(f"known_gene = '{symbol}' AND cis_trans = 'cis'")

    def get_all_colocs_for_region(self, region_name: str):
        return self._fetch_colocs(f"ld_block = '{region_name}'")

    def get_all_colocs_for_study(self, study_id: str):
        return self._fetch_colocs(f"study = '{study_id}'")

    def get_study_names_for_search(self):
        return self.studies_conn.execute(
            "SELECT study_name, trait FROM studies_processed WHERE data_type = 'phenotype'"
        ).fetchall()

    def get_gene_names(self):
        return self.studies_conn.execute(
            "SELECT DISTINCT known_gene FROM all_study_blocks"
        ).fetchall()

    def get_study_extractions_for_study(self, study_id: str):
        query = f"""
            SELECT all_study_blocks.*, studies_processed.trait, studies_processed.data_type, studies_processed.tissue
            FROM all_study_blocks 
            JOIN studies_processed ON all_study_blocks.study = studies_processed.study_name 
            WHERE all_study_blocks.study = '{study_id}'
        """
        return self.studies_conn.execute(query).fetchall()

    def get_study_extractions_in_region(self, chr: str, bp_start: int, bp_end: int, symbol: str):
        return self.studies_conn.execute(
            """SELECT all_study_blocks.*, studies_processed.trait, studies_processed.data_type, studies_processed.tissue
            FROM all_study_blocks 
            JOIN studies_processed ON all_study_blocks.study = studies_processed.study_name 
            WHERE (all_study_blocks.chr = ? AND all_study_blocks.bp BETWEEN ? AND ?) OR (all_study_blocks.known_gene = ? AND all_study_blocks.cis_trans = 'cis')
            """,
            (chr, bp_start, bp_end, symbol)
        ).fetchall()

    def get_gene(self, symbol: str):
        query = f"""
        SELECT DISTINCT ANY_VALUE(symbol) as symbol, ANY_VALUE(chr) as chr, MIN(bp) as min_bp, MAX(bp) as max_bp
        FROM variant_annotations 
        WHERE symbol = '{symbol}' 
        GROUP BY symbol
        """
        return self.studies_conn.execute(query).fetchone()

    def get_variant(self, variant_id: str):
        query = f"SELECT * FROM variant_annotations WHERE SNP = '{variant_id}'"
        return self.studies_conn.execute(query).fetchone()

    def get_gene_ranges(self):
        query = f"""
        SELECT DISTINCT ANY_VALUE(symbol) as symbol, ANY_VALUE(chr) as chr, MIN(bp) as min_bp, MAX(bp) as max_bp
        FROM variant_annotations 
        WHERE symbol IS NOT NULL 
        GROUP BY symbol
        """
        return self.studies_conn.execute(query).fetchall()

    def get_ld_proxies(self, variants: List[str]):
        formatted_variants = ','.join(f"'{variant}'" for variant in variants)
        query = f"""
            SELECT * FROM ld
            WHERE variant IN ({formatted_variants})
            AND abs(r) > 0.894
        """
        return self.studies_conn.execute(query).fetchall()

    def get_ld_matrix(self, variants: List[str]):
        formatted_variants = ','.join(f"'{variant}'" for variant in variants)
        query = f"""
            SELECT * FROM 
                (FROM ld WHERE lead IN ({formatted_variants}))
                WHERE variant IN ({formatted_variants}) AND variant > lead
        """
        return self.studies_conn.execute(query).fetchall()

    def get_variants(self, variants: List[str] = None, rsids: List[str] = None, grange: List[str] = None):
        if not variants and not rsids and not grange:
            return []

        query = "SELECT * FROM variant_annotations WHERE "
        if variants:
            formatted_variants = ','.join(f"'{variant}'" for variant in variants)
            query += f"SNP IN ({formatted_variants})"
        elif rsids:
            formatted_rsids = ','.join(f"'{rsid}'" for rsid in rsids)
            query += f"RSID IN ({formatted_rsids})"
        elif grange:
            chr, position = grange.split(":")
            start_bp, end_bp = position.split("-")
            start_bp, end_bp = int(start_bp), int(end_bp)

            query += f"""CHR = {chr} AND BP BETWEEN {start_bp} AND {end_bp}"""

        return self.studies_conn.execute(query).fetchall()

    def get_tissues(self):
        return self.studies_conn.execute("SELECT DISTINCT tissue FROM studies_processed WHERE tissue IS NOT NULL").fetchall()

    def get_associations_for_variant_and_studies(self, variant_id: str, studies: List[str]):
        formatted_studies = ','.join(f"'{study}'" for study in studies)
        query = f"""
            SELECT * FROM assocs 
            WHERE study IN ({formatted_studies}) AND SNP = '{variant_id}'
        """
        return self.associations_conn.execute(query).fetchall()

    def get_associations(self, variants: List[str], studies: List[str], p_value_threshold: float):
        if not variants and not studies:
            return []

        query = "SELECT * FROM assocs WHERE 1=1"
        if variants:
            formatted_variants = ','.join(f"'{variant}'" for variant in variants)
            query += f" AND SNP IN ({formatted_variants})"
        
        if studies:
            formatted_studies = ','.join(f"'{study}'" for study in studies)
            query += f" AND study IN ({formatted_studies})"

        if p_value_threshold is not None:
            query += f" AND P <= {p_value_threshold}"
        
        return self.associations_conn.execute(query).fetchall()
        