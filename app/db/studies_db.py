from app.config import get_settings
from functools import lru_cache
from typing import List
import duckdb

from app.models.schemas import CisTrans, StudyDataType, VariantType
from app.db.utils import log_performance
from app.logging_config import get_logger

settings = get_settings()
logger = get_logger(__name__)


@lru_cache()
def get_gpm_db_connection():
    connection = duckdb.connect(settings.STUDIES_DB_PATH, read_only=True)
    connection.execute("PRAGMA memory_limit='4GB'")
    return connection


class StudiesDBClient:
    def __init__(self):
        self.studies_conn = get_gpm_db_connection()
        self.common_data_types = [
            f"'{StudyDataType.phenotype.name}'",
            f"'{StudyDataType.cell_trait.name}'",
            f"'{StudyDataType.plasma_protein.name}'",
        ]

    @log_performance
    def get_traits(self, trait_ids: List[int] = None):
        query = f"""
            SELECT traits.*, studies.variant_type, studies.sample_size, studies.category, studies.ancestry, studies.heritability, studies.heritability_se
            FROM traits
            JOIN studies ON traits.id = studies.trait_id
            WHERE traits.data_type IN ({",".join(self.common_data_types)})
        """
        params = []
        if trait_ids:
            query += " AND traits.id IN (SELECT * FROM UNNEST(?))"
            params.append(trait_ids)

        return self.studies_conn.execute(query, params).fetchall()

    @log_performance
    def get_traits_by_ids(self, trait_ids: List[int | str]):
        if not trait_ids:
            return []

        # Split into numeric IDs and string names
        ids = []
        names = []
        for tid in trait_ids:
            if isinstance(tid, int) or (isinstance(tid, str) and tid.isdigit()):
                ids.append(int(tid))
            else:
                names.append(tid)

        conditions = []
        params = []

        if ids:
            conditions.append("id IN (SELECT * FROM UNNEST(?))")
            params.append(ids)

        if names:
            conditions.append("trait IN (SELECT * FROM UNNEST(?))")
            params.append(names)

        if not conditions:
            return []

        query = f"SELECT * FROM traits WHERE {' OR '.join(conditions)}"
        return self.studies_conn.execute(query, params).fetchall()

    @log_performance
    def get_trait(self, trait_id: str | int):
        if isinstance(trait_id, str) and not trait_id.isdigit():
            query = "SELECT * FROM traits WHERE trait = ?"
        else:
            query = "SELECT * FROM traits WHERE id = ?"
        return self.studies_conn.execute(query, [trait_id]).fetchone()

    @log_performance
    def get_study_sources(self):
        query = "SELECT * FROM study_sources"
        return self.studies_conn.execute(query).fetchall()

    @log_performance
    def get_study_metadata(self):
        query = """
            SELECT data_type, variant_type, COUNT(*) as count
            FROM studies
            GROUP BY data_type, variant_type
            ORDER BY data_type, variant_type
        """

        return self.studies_conn.execute(query).fetchall()

    @log_performance
    def get_studies(self, limit: int = None):
        query = "SELECT * FROM studies LIMIT ?"
        return self.studies_conn.execute(query, [limit]).fetchall()

    @log_performance
    def get_study(self, study_id: str):
        query = "SELECT * FROM studies WHERE id = ?"
        return self.studies_conn.execute(query, [study_id]).fetchone()

    @log_performance
    def get_studies_by_trait_ids(self, trait_ids: List[int]):
        if not trait_ids:
            return []

        query = """SELECT studies.*, study_sources.url FROM studies
          JOIN study_sources ON studies.source_id = study_sources.id
          WHERE trait_id IN (SELECT * FROM UNNEST(?))"""
        return self.studies_conn.execute(query, [trait_ids]).fetchall()

    @log_performance
    def get_rare_results_for_study_ids(self, study_ids: List[int]):
        if not study_ids:
            return []
        return self._fetch_rare_results("study_id IN (SELECT * FROM UNNEST(?))", [study_ids])

    @log_performance
    def get_all_colocs_for_study_ids(self, study_ids: List[int]):
        if not study_ids:
            return []
        return self._fetch_colocs("study_id IN (SELECT * FROM UNNEST(?))", [study_ids])

    @log_performance
    def get_studies_by_id(self, study_ids: List[int]):
        if not study_ids:
            return []

        placeholders = ",".join(["(?, ?)" for _ in study_ids])
        query = f"""
            WITH input_studies AS (
                SELECT * FROM (VALUES {placeholders}) as t(row_num, id)
            )
            SELECT studies.*
            FROM input_studies
            LEFT JOIN studies ON COALESCE(input_studies.id, -1) = COALESCE(studies.id, -1)
            ORDER BY input_studies.row_num
        """

        params = []
        for i, study_id in enumerate(study_ids):
            params.extend([i, study_id])

        return self.studies_conn.execute(query, params).fetchall()

    def _fetch_colocs(self, condition: str, params: List = None):
        query = f"""
            SELECT * FROM coloc_groups_wide
            WHERE coloc_group_id IN (
                SELECT DISTINCT coloc_group_id
                FROM coloc_groups_wide
                WHERE {condition}
            );
        """
        if params:
            return self.studies_conn.execute(query, params).fetchall()
        return self.studies_conn.execute(query).fetchall()

    @log_performance
    def get_num_coloc_groups_per_trait(self):
        query = """
            SELECT traits.id, COUNT(DISTINCT coloc_group_id) as num_coloc_groups
                FROM coloc_groups
                JOIN studies ON coloc_groups.study_id = studies.id
                JOIN traits ON studies.trait_id = traits.id
                GROUP BY traits.id
        """
        return self.studies_conn.execute(query).fetchall()

    @log_performance
    def get_num_coloc_studies_per_trait(self):
        query = """
            SELECT 
                traits.id,
                COUNT(DISTINCT other_studies.id) as num_coloc_studies
            FROM traits
            JOIN studies ON traits.id = studies.trait_id
            JOIN coloc_groups ON studies.id = coloc_groups.study_id
            JOIN coloc_groups other_colocs ON coloc_groups.coloc_group_id = other_colocs.coloc_group_id
            JOIN studies other_studies ON other_colocs.study_id = other_studies.id
            GROUP BY traits.id
        """
        return self.studies_conn.execute(query).fetchall()

    @log_performance
    def get_colocs_for_variant(self, snp_id: int):
        return self._fetch_colocs("snp_id = ?", [snp_id])

    @log_performance
    def get_colocs_for_variants(self, snp_ids: List[int]):
        if not snp_ids:
            return []
        return self._fetch_colocs("snp_id IN (SELECT * FROM UNNEST(?))", [snp_ids])

    @log_performance
    def get_all_colocs_for_gene(self, gene_id: int, include_trans: bool = False):
        query = "gene_id = ?"
        if not include_trans:
            query += " AND cis_trans = ?"
            params = [gene_id, CisTrans.cis.value]
        else:
            params = [gene_id]
        return self._fetch_colocs(query, params)

    @log_performance
    def get_all_colocs_for_ld_block(self, ld_block_id: int):
        return self._fetch_colocs("ld_block_id = ?", [ld_block_id])

    @log_performance
    def get_all_colocs_for_study(self, study_id: str):
        return self._fetch_colocs("study_id = ?", [study_id])

    @log_performance
    def get_all_colocs_for_study_extraction_ids(self, study_extraction_ids: List[int]):
        if not study_extraction_ids:
            return []
        return self._fetch_colocs("study_extraction_id IN (SELECT * FROM UNNEST(?))", [study_extraction_ids])

    def _fetch_rare_results(self, condition: str, params: List = None):
        query = f"""
            SELECT * FROM rare_results_wide
            WHERE rare_result_group_id IN (
                SELECT DISTINCT rare_result_group_id
                FROM rare_results_wide
                WHERE {condition}
            )
        """
        if params:
            return self.studies_conn.execute(query, params).fetchall()
        return self.studies_conn.execute(query).fetchall()

    @log_performance
    def get_num_rare_results_per_study(self):
        query = """
            SELECT traits.id, COUNT(DISTINCT rare_result_group_id) as num_rare_results
            FROM rare_results
            JOIN studies ON rare_results.study_id = studies.id
            JOIN traits ON studies.trait_id = traits.id
            GROUP BY traits.id
        """
        return self.studies_conn.execute(query).fetchall()

    @log_performance
    def get_rare_results_for_gene(self, gene_id: int, include_trans: bool = False):
        query = "(gene_id = ? OR situated_gene_id = ?)"
        params = [gene_id, gene_id]

        if not include_trans:
            query += " AND (cis_trans = ? OR cis_trans IS NULL)"
            params.append(CisTrans.cis.value)

        return self._fetch_rare_results(query, params)

    @log_performance
    def get_rare_results_for_study_extraction_ids(self, study_extraction_ids: List[int]):
        if not study_extraction_ids:
            return []

        return self._fetch_rare_results("study_extraction_id IN (SELECT * FROM UNNEST(?))", [study_extraction_ids])

    @log_performance
    def get_rare_results_for_variants(self, snp_ids: List[int]):
        if not snp_ids:
            return []
        return self._fetch_rare_results("snp_id IN (SELECT * FROM UNNEST(?))", [snp_ids])

    @log_performance
    def get_rare_results_for_study_id(self, study_id: int):
        if not study_id:
            return []

        return self._fetch_rare_results("study_id = ?", [study_id])

    @log_performance
    def get_rare_results_for_ld_block(self, ld_block_id: int):
        return self._fetch_rare_results("ld_block_id = ?", [ld_block_id])

    @log_performance
    def get_trait_names_for_search(self):
        return self.studies_conn.execute(f"""
            SELECT traits.id, traits.trait_name, studies.sample_size
            FROM traits
            JOIN studies ON traits.id = studies.trait_id 
            WHERE traits.data_type IN ({",".join(self.common_data_types)}) AND studies.variant_type = '{VariantType.common.name}'
        """).fetchall()

    @log_performance
    def get_gene(self, symbol: str = None, id: int = None):
        query = """SELECT gene_annotations.*,
            gene_pleiotropy.distinct_trait_categories, gene_pleiotropy.distinct_protein_coding_genes
            FROM gene_annotations
            LEFT JOIN gene_pleiotropy ON gene_annotations.id = gene_pleiotropy.gene_id"""
        if symbol:
            query += " WHERE gene_annotations.gene = ?"
            data = [symbol]
        elif id:
            query += " WHERE gene_annotations.id = ?"
            data = [id]
        else:
            raise ValueError("Either gene or id must be provided")

        return self.studies_conn.execute(query, data).fetchone()

    @log_performance
    def get_variant(self, snp_id: int):
        query = """SELECT
            snp_annotations.*,
            snp_pleiotropy.distinct_trait_categories, snp_pleiotropy.distinct_protein_coding_genes
            FROM snp_annotations
            LEFT JOIN snp_pleiotropy ON snp_annotations.id = snp_pleiotropy.snp_id
            WHERE snp_annotations.id = ?
        """
        return self.studies_conn.execute(query, [snp_id]).fetchone()

    @log_performance
    def get_genes(self):
        query = """SELECT
            gene_annotations.*, gene_pleiotropy.distinct_trait_categories, gene_pleiotropy.distinct_protein_coding_genes
            FROM gene_annotations
            LEFT JOIN gene_pleiotropy ON gene_annotations.id = gene_pleiotropy.gene_id"""
        return self.studies_conn.execute(query).fetchall()

    @log_performance
    def get_genes_by_gene_ids(self, gene_ids: List[int]):
        if not gene_ids:
            return []

        query = "SELECT * FROM gene_annotations WHERE id IN (SELECT * FROM UNNEST(?))"
        return self.studies_conn.execute(query, [gene_ids]).fetchall()

    @log_performance
    def get_genes_by_ids(self, gene_ids: List[str | int]):
        """Fetch genes by ID or symbol. Returns full gene with pleiotropy joined."""
        if not gene_ids:
            return []

        ids = []
        symbols = []
        for gid in gene_ids:
            if isinstance(gid, int) or (isinstance(gid, str) and gid.isdigit()):
                ids.append(int(gid))
            else:
                symbols.append(str(gid))

        conditions = []
        params = []
        if ids:
            conditions.append("gene_annotations.id IN (SELECT * FROM UNNEST(?))")
            params.append(ids)
        if symbols:
            conditions.append("gene_annotations.gene IN (SELECT * FROM UNNEST(?))")
            params.append(symbols)
        if not conditions:
            return []

        query = f"""
            SELECT gene_annotations.*,
                gene_pleiotropy.distinct_trait_categories, gene_pleiotropy.distinct_protein_coding_genes
            FROM gene_annotations
            LEFT JOIN gene_pleiotropy ON gene_annotations.id = gene_pleiotropy.gene_id
            WHERE {" OR ".join(conditions)}
        """
        return self.studies_conn.execute(query, params).fetchall()

    @log_performance
    def get_all_colocs_for_genes(self, gene_ids: List[int], include_trans: bool = False):
        if not gene_ids:
            return []
        query = "gene_id IN (SELECT * FROM UNNEST(?))"
        params = [gene_ids]
        if not include_trans:
            query += " AND cis_trans = ?"
            params.append(CisTrans.cis.value)
        return self._fetch_colocs(query, params)

    @log_performance
    def get_rare_results_for_genes(self, gene_ids: List[int], include_trans: bool = False):
        if not gene_ids:
            return []
        query = "(gene_id IN (SELECT * FROM UNNEST(?)) OR situated_gene_id IN (SELECT * FROM UNNEST(?)))"
        params = [gene_ids, gene_ids]
        if not include_trans:
            query += " AND (cis_trans = ? OR cis_trans IS NULL)"
            params.append(CisTrans.cis.value)
        return self._fetch_rare_results(query, params)

    @log_performance
    def get_study_extractions_for_genes(self, gene_ids: List[int], include_trans: bool = False):
        if not gene_ids:
            return []
        query = "(gene_id IN (SELECT * FROM UNNEST(?)) OR situated_gene_id IN (SELECT * FROM UNNEST(?)))"
        params = [gene_ids, gene_ids]
        if not include_trans:
            query += " AND cis_trans = ?"
            params.append(CisTrans.cis.value)
        return self._fetch_study_extractions(query, params)

    @log_performance
    def get_study_extractions_in_gene_regions(self, regions: List[tuple]):
        """regions: list of (chr, start, stop) tuples"""
        if not regions:
            return []
        conditions = []
        params = []
        for chr_val, start, stop in regions:
            conditions.append("(chr = ? AND bp BETWEEN ? AND ?)")
            params.extend([chr_val, start, stop])
        query = "(" + " OR ".join(conditions) + ") AND cis_trans = ?"
        params.append(CisTrans.cis.value)
        return self._fetch_study_extractions(query, params)

    @log_performance
    def get_variants(
        self,
        snp_ids: List[int] = None,
        variant_prefixes: List[str] = None,
        rsids: List[str] = None,
        grange: List[str] = None,
    ):
        if not snp_ids and not variant_prefixes and not rsids and not grange:
            return []

        query = """SELECT snp_annotations.*, snp_pleiotropy.distinct_trait_categories, snp_pleiotropy.distinct_protein_coding_genes
            FROM snp_annotations
            LEFT JOIN snp_pleiotropy ON snp_annotations.id = snp_pleiotropy.snp_id
            WHERE 
        """
        params = []

        if snp_ids:
            query += "id IN (SELECT * FROM UNNEST(?))"
            params.append(snp_ids)
        elif rsids:
            query += "rsid IN (SELECT * FROM UNNEST(?))"
            params.append(rsids)
        elif grange:
            chromosome, position = grange.split(":")
            start_bp, end_bp = position.split("-")
            start_bp, end_bp = int(start_bp), int(end_bp)
            query += "chr = ? AND bp BETWEEN ? AND ?"
            params.extend([chromosome, start_bp, end_bp])
        elif variant_prefixes:
            query += "SPLIT_PART(snp, '_', 1) IN (SELECT * FROM UNNEST(?))"
            params.append(variant_prefixes)

        return self.studies_conn.execute(query, params).fetchall()

    @log_performance
    def get_tissues(self):
        return self.studies_conn.execute("SELECT DISTINCT tissue FROM studies WHERE tissue IS NOT NULL").fetchall()

    @log_performance
    def get_variants_by_snp_strings(self, variants: List[str]):
        if not variants:
            return []

        placeholders = ",".join(["(?, ?)" for _ in variants])
        query = f"""
            WITH input_variants AS (
                SELECT * FROM (VALUES {placeholders}) as t(row_num, variant)
            )
            SELECT snp_annotations.* 
            FROM input_variants 
            LEFT JOIN snp_annotations ON input_variants.variant = snp_annotations.snp 
            ORDER BY input_variants.row_num
        """

        params = []
        for i, variant in enumerate(variants):
            params.extend([i, variant])

        return self.studies_conn.execute(query, params).fetchall()

    @log_performance
    def get_snp_ids_by_snps(self, snps: List[str]):
        if not snps:
            return []

        query = "SELECT id FROM snp_annotations WHERE snp IN (SELECT * FROM UNNEST(?))"
        return self.studies_conn.execute(query, [snps]).fetchall()

    @log_performance
    def get_coloc_metadata(self):
        query = """
            SELECT MAX(coloc_group_id) as count FROM coloc_groups 
        """
        coloc_groups = self.studies_conn.execute(query).fetchone()

        query = """
            SELECT COUNT(DISTINCT snp_id) as count
            FROM coloc_groups
        """
        unique_snps = self.studies_conn.execute(query).fetchone()
        return coloc_groups[0], unique_snps[0]

    @log_performance
    def get_gene_names(self):
        return self.studies_conn.execute("SELECT gene, ensembl_id FROM gene_annotations").fetchall()

    @log_performance
    def get_num_study_extractions_per_study(self):
        query = f"""
            SELECT traits.id, COUNT(DISTINCT study_extractions.id) as num_extractions
            FROM study_extractions 
            JOIN studies ON study_extractions.study_id = studies.id
            JOIN traits ON studies.trait_id = traits.id
            WHERE studies.data_type IN ({",".join(self.common_data_types)})
            GROUP BY traits.id
        """
        return self.studies_conn.execute(query).fetchall()

    @log_performance
    def get_study_extractions_for_studies(self, study_ids: List[int]):
        if not study_ids:
            return []
        return self._fetch_study_extractions("study_id IN (SELECT * FROM UNNEST(?))", [study_ids])

    @log_performance
    def get_study_extractions_for_variant(self, snp_id: int):
        if not snp_id:
            return []

        return self._fetch_study_extractions("snp_id = ?", [snp_id])

    @log_performance
    def get_study_extractions_for_variants(self, snp_ids: List[int]):
        if not snp_ids:
            return []
        return self._fetch_study_extractions("snp_id IN (SELECT * FROM UNNEST(?))", [snp_ids])

    @log_performance
    def get_study_extractions_by_id(self, ids: List[int]):
        if not ids:
            return []
        return self._fetch_study_extractions("id IN (SELECT * FROM UNNEST(?))", [ids])

    def _fetch_study_extractions(self, condition: str, params: List = None):
        if not params:
            raise ValueError("params must be provided for study extraction queries")
        query = f"""
            SELECT * FROM study_extractions_wide
            WHERE {condition}
        """
        return self.studies_conn.execute(query, params).fetchall()

    @log_performance
    def get_study_extractions_by_unique_study_id(self, unique_study_ids: List[str]):
        if not unique_study_ids:
            return []

        placeholders = ",".join(["(?, ?)" for _ in unique_study_ids])
        query = f"""
            WITH input_studies AS (
                SELECT * FROM (VALUES {placeholders}) as t(row_num, unique_study_id)
            )
            SELECT study_extractions.*
            FROM input_studies 
            LEFT JOIN study_extractions ON input_studies.unique_study_id = study_extractions.unique_study_id
            ORDER BY input_studies.row_num
        """

        params = []
        for i, study_id in enumerate(unique_study_ids):
            params.extend([i, study_id])

        return self.studies_conn.execute(query, params).fetchall()

    @log_performance
    def get_num_coloc_groups_per_gene(self):
        query = """
            SELECT gene_annotations.gene, COUNT(DISTINCT coloc_group_id) as num_coloc_groups
            FROM coloc_groups
            JOIN study_extractions ON coloc_groups.study_extraction_id = study_extractions.id
            JOIN gene_annotations ON study_extractions.gene_id = gene_annotations.id
            GROUP BY gene_annotations.gene
        """
        return self.studies_conn.execute(query).fetchall()

    @log_performance
    def get_num_coloc_studies_per_gene(self):
        query = """
            SELECT gene_annotations.gene, COUNT(DISTINCT coloc_groups.study_id) as num_coloc_studies
            FROM coloc_groups
            JOIN study_extractions ON coloc_groups.study_extraction_id = study_extractions.id
            JOIN gene_annotations ON study_extractions.gene_id = gene_annotations.id
            GROUP BY gene_annotations.gene
        """
        return self.studies_conn.execute(query).fetchall()

    @log_performance
    def get_num_study_extractions_per_gene(self):
        query = """
            SELECT gene_annotations.gene, COUNT(DISTINCT study_extractions.id) as num_extractions
            FROM study_extractions
            JOIN gene_annotations ON study_extractions.gene_id = gene_annotations.id
            GROUP BY gene_annotations.gene
        """
        return self.studies_conn.execute(query).fetchall()

    @log_performance
    def get_num_rare_results_per_gene(self):
        query = f"""
            SELECT gene_annotations.gene, COUNT(DISTINCT rare_results.rare_result_group_id) as num_rare_results
            FROM rare_results
            JOIN study_extractions ON rare_results.study_extraction_id = study_extractions.id
            JOIN gene_annotations ON (rare_results.gene_id = gene_annotations.id OR rare_results.situated_gene_id = gene_annotations.id)
            WHERE study_extractions.cis_trans = '{CisTrans.cis.value}' OR study_extractions.cis_trans IS NULL
            GROUP BY gene_annotations.gene
        """
        return self.studies_conn.execute(query).fetchall()

    @log_performance
    def get_study_extractions_for_gene(self, gene_id: int, include_trans: bool = False):
        if not gene_id:
            return []
        query = "(gene_id = ? OR situated_gene_id = ?)"
        if not include_trans:
            query += " AND cis_trans = ?"
            params = [gene_id, gene_id, CisTrans.cis.value]
        else:
            params = [gene_id, gene_id]
        return self._fetch_study_extractions(query, params)

    @log_performance
    def get_study_extractions_in_gene_region(self, chromosome: str, bp_start: int, bp_end: int):
        cis_trans = CisTrans.cis.value
        return self._fetch_study_extractions(
            """
            chr = ? AND bp BETWEEN ? AND ? AND cis_trans = ?
            """,
            [chromosome, bp_start, bp_end, cis_trans],
        )

    @log_performance
    def get_study_extractions_in_ld_block(self, ld_block_id: int):
        return self._fetch_study_extractions("ld_block_id = ?", [ld_block_id])

    @log_performance
    def get_ld_block(self, ld_block_id: int):
        query = "SELECT * FROM ld_blocks WHERE id = ?"
        return self.studies_conn.execute(query, [ld_block_id]).fetchone()

    @log_performance
    def get_ld_blocks_by_ld_block(self, ld_blocks: List[str]):
        if not ld_blocks:
            return []

        placeholders = ",".join(["(?, ?)" for _ in ld_blocks])
        query = f"""
            WITH input_blocks AS (
                SELECT * FROM (VALUES {placeholders}) as t(row_num, ld_block)
            )
            SELECT ld_blocks.* 
            FROM input_blocks 
            LEFT JOIN ld_blocks ON input_blocks.ld_block = ld_blocks.ld_block
            ORDER BY input_blocks.row_num
        """

        params = []
        for i, ld_block in enumerate(ld_blocks):
            params.extend([i, ld_block])

        return self.studies_conn.execute(query, params).fetchall()

    @log_performance
    def get_gene_pleiotropy_scores(self):
        query = """SELECT
            gene_pleiotropy.gene_id, gene_annotations.gene, gene_pleiotropy.distinct_trait_categories, gene_pleiotropy.distinct_protein_coding_genes
            FROM gene_pleiotropy
            JOIN gene_annotations ON gene_pleiotropy.gene_id = gene_annotations.id
        """
        return self.studies_conn.execute(query).fetchall()

    @log_performance
    def get_snp_pleiotropy_scores(self):
        query = """SELECT
            snp_pleiotropy.snp_id, snp_annotations.display_snp, snp_pleiotropy.distinct_trait_categories, snp_pleiotropy.distinct_protein_coding_genes
            FROM snp_pleiotropy
            JOIN snp_annotations ON snp_pleiotropy.snp_id = snp_annotations.id
        """
        return self.studies_conn.execute(query).fetchall()
