from typing import List
import duckdb
from functools import lru_cache
from app.config import get_settings
from functools import lru_cache

from app.models.schemas import ProccessGwasRequest
settings = get_settings()
# 
@lru_cache()
def get_gpm_db_connection():
    return duckdb.connect(settings.GPM_DB_PATH, read_only=True)

class DuckDBClient:
    def __init__(self):
        self.gpm_conn = get_gpm_db_connection()

    def upload_gwas(self, gwas_request: ProccessGwasRequest):
        conn = duckdb.connect(settings.GWAS_UPLOAD_DB_PATH)

        # conn.execute("INSERT INTO gwas_upload VALUES (?, ?, ?, ?, ?, ?, ?)", gwas_data)
        conn.close()

    def get_studies(self, limit: int = None):
        if (limit is None):
            query = "SELECT * FROM studies"
        else:
            query = f"SELECT * FROM studies LIMIT {limit}"
            query = f"SHOW TABLES"
        
        return self.gpm_conn.execute(query).fetchall()

    def get_study(self, study_id: str):
        query = f"SELECT * FROM studies WHERE id = '{study_id}'"
        return self.gpm_conn.execute(query).fetchone()

    def _fetch_colocs(self, condition: str):
        # TODO: Remove this once we filter colocs when creating the db
        query = f"""
            SELECT colocalisations.*, studies.trait, studies.data_type, studies.tissue 
            FROM colocalisations 
            JOIN studies ON colocalisations.study_id = studies.id
            WHERE colocalisations.coloc_group_id IN (SELECT DISTINCT coloc_group_id FROM colocalisations WHERE {condition})
            AND colocalisations.posterior_prob IS NOT NULL AND colocalisations.posterior_prob > 0.5
        """
        return self.gpm_conn.execute(query).fetchall()

    def get_colocs_for_variant(self, snp_id: int):
        return self._fetch_colocs(f"snp_id = {snp_id}")

    def get_all_colocs_for_gene(self, symbol: str):
        return self._fetch_colocs(f"known_gene = '{symbol}' AND cis_trans = 'cis'")

    def get_all_colocs_for_ld_block(self, ld_block_id: int):
        return self._fetch_colocs(f"ld_block_id = {ld_block_id}")

    def get_all_colocs_for_study(self, study_id: str):
        return self._fetch_colocs(f"study_id = '{study_id}'")

    def get_study_names_for_search(self):
        return self.gpm_conn.execute(
            "SELECT id, trait FROM studies WHERE data_type = 'phenotype'"
        ).fetchall()

    def get_gene_names(self):
        return self.gpm_conn.execute(
            "SELECT DISTINCT known_gene FROM study_extractions"
        ).fetchall()

    def get_study_extractions_for_study(self, study_id: str):
        query = f"""
            SELECT study_extractions.*, studies.trait, studies.data_type, studies.tissue
            FROM study_extractions 
            JOIN studies ON study_extractions.study = studies.id
            WHERE study_extractions.study = '{study_id}'
        """
        return self.gpm_conn.execute(query).fetchall()

    def get_study_extractions_in_region(self, chr: str, bp_start: int, bp_end: int, symbol: str):
        return self.gpm_conn.execute(
            """SELECT study_extractions.*, studies.trait, studies.data_type, studies.tissue
            FROM study_extractions 
            JOIN studies ON study_extractions.study_id = studies.id
            WHERE (study_extractions.chr = ? AND study_extractions.bp BETWEEN ? AND ?)
               OR (study_extractions.known_gene = ? AND study_extractions.cis_trans = 'cis')
            """,
            (chr, bp_start, bp_end, symbol)
        ).fetchall()

    def get_ld_block(self, ld_block_id: int):
        query = f"SELECT * FROM ld_blocks WHERE id = {ld_block_id}"
        return self.gpm_conn.execute(query).fetchone()

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
        return self.gpm_conn.execute(query).fetchone()

    def get_variant(self, snp_id: int):
        query = f"SELECT * FROM snp_annotations WHERE id = {snp_id}"
        return self.gpm_conn.execute(query).fetchone()

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
        return self.gpm_conn.execute(query).fetchall()

    def get_ld_proxies(self, snp_ids: List[int]):
        formatted_snp_ids = ','.join(f"{snp_id}" for snp_id in snp_ids)
        query = f"""
            SELECT * FROM ld
            WHERE variant_snp_id IN ({formatted_snp_ids})
            AND abs(r) > 0.894
        """
        return self.gpm_conn.execute(query).fetchall()

    def get_ld_matrix(self, snp_ids: List[int]):
        formatted_snp_ids = ','.join(f"{snp_id}" for snp_id in snp_ids)
        query = f"""
            SELECT * FROM 
                (SELECT * FROM ld WHERE lead IN ({formatted_snp_ids}))
                WHERE variant IN ({formatted_snp_ids}) AND variant > lead
        """
        return self.gpm_conn.execute(query).fetchall()

    def get_variants(self, snp_ids: List[int] = None, rsids: List[str] = None, grange: List[str] = None):
        if not snp_ids and not rsids and not grange:
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

        return self.gpm_conn.execute(query).fetchall()

    def get_tissues(self):
        return self.gpm_conn.execute("SELECT DISTINCT tissue FROM studies WHERE tissue IS NOT NULL").fetchall()

    def get_snp_ids_by_variants(self, variants: List[str]):
        formatted_variants = ','.join(f"'{variant}'" for variant in variants)
        query = f"SELECT id FROM snp_annotations WHERE rsid IN ({formatted_variants})"
        return self.gpm_conn.execute(query).fetchall()

    def get_associations_for_variant_and_studies(self, snp_id: int, study_ids: List[int]):
        formatted_study_ids = ','.join(f"{study_id}" for study_id in study_ids)
        query = f"""
            SELECT * FROM assocs 
            WHERE study_id IN ({formatted_study_ids}) AND snp_id = {snp_id}
        """
        return self.gpm_conn.execute(query).fetchall()

    def get_associations(self, snp_ids: List[int], study_ids: List[int], p_value_threshold: float):
        if not snp_ids and not study_ids:
            return []

        query = "SELECT * FROM assocs WHERE 1=1"
        if snp_ids:
            formatted_snp_ids = ','.join(f"{snp_id}" for snp_id in snp_ids)
            query += f" AND snp_id IN ({formatted_snp_ids})"
        
        if study_ids:
            formatted_study_ids = ','.join(f"{study_id}" for study_id in study_ids)
            query += f" AND study_id IN ({formatted_study_ids})"

        if p_value_threshold is not None:
            query += f" AND p <= {p_value_threshold}"
        
        return self.gpm_conn.execute(query).fetchall()
        