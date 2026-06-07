from typing import List, Optional

from scipy.stats import fisher_exact

from app.db.studies_db import StudiesDBClient
from app.logging_config import get_logger
from app.models.schemas import PathwayEnrichmentResult

logger = get_logger(__name__)

VALID_SOURCES = {"Reactome", "KEGG", "HP"}


class PathwayService:
    def __init__(self):
        self.studies_db = StudiesDBClient()

    @staticmethod
    def _fisher_enrichment_pvalue(
        overlap: int,
        query_size: int,
        pathway_size: int,
        background_size: int,
    ) -> float:
        """One-tailed Fisher's exact test for over-representation."""
        a = overlap
        b = query_size - overlap
        c = pathway_size - overlap
        d = background_size - pathway_size - b
        if d < 0:
            d = 0
        _, p_value = fisher_exact([[a, b], [c, d]], alternative="greater")
        return p_value

    @staticmethod
    def _benjamini_hochberg(p_values: list[float]) -> list[float]:
        """Standard Benjamini-Hochberg FDR correction within a single category."""
        m = len(p_values)
        if m == 0:
            return []
        indexed = sorted(enumerate(p_values), key=lambda x: x[1])
        fdr = [0.0] * m
        cumulative_min = 1.0
        for rank_from_end, (orig_idx, p) in enumerate(reversed(indexed)):
            rank = m - rank_from_end
            adjusted = p * m / rank
            cumulative_min = min(cumulative_min, adjusted)
            fdr[orig_idx] = min(cumulative_min, 1.0)
        return fdr

    def get_pathway_enrichment(
        self,
        gene_ids: List[int],
        source: Optional[str] = None,
        p_value_threshold: float = 0.05,
    ) -> tuple[list[PathwayEnrichmentResult], int, int]:
        """
        Run STRING-style pathway enrichment for the given gene IDs.

        Returns (results, matched_gene_count, total_terms_tested).
        """
        mappings = self.studies_db.get_pathway_mappings_for_genes(gene_ids, source)
        if not mappings:
            return [], 0, 0

        matched_gene_ids = set()
        term_genes_by_source: dict[str, dict[str, set[int]]] = {}
        term_meta_by_source: dict[str, dict[str, tuple[str, str | None]]] = {}
        for gene_id, term_id, src, desc in mappings:
            matched_gene_ids.add(gene_id)
            term_genes_by_source.setdefault(src, {}).setdefault(term_id, set()).add(gene_id)
            if term_id not in term_meta_by_source.setdefault(src, {}):
                term_meta_by_source[src][term_id] = (src, desc)

        sources_to_test = [source] if source else sorted(term_genes_by_source.keys())
        all_results: list[PathwayEnrichmentResult] = []
        total_terms_tested = 0

        for src in sources_to_test:
            term_genes = term_genes_by_source.get(src, {})
            if not term_genes:
                continue

            term_ids = list(term_genes.keys())
            pathway_sizes_rows = self.studies_db.get_pathway_sizes(term_ids, src)
            size_lookup: dict[str, tuple[int, int]] = {}
            for term_id, _, _, pathway_size, background_size in pathway_sizes_rows:
                size_lookup[term_id] = (pathway_size, background_size)

            genes_in_source = {gid for genes in term_genes.values() for gid in genes}
            query_size = len(genes_in_source)

            category_results, category_tested = self._enrich_category(
                term_genes=term_genes,
                term_meta=term_meta_by_source[src],
                size_lookup=size_lookup,
                query_size=query_size,
                fdr_threshold=p_value_threshold,
            )
            all_results.extend(category_results)
            total_terms_tested += category_tested

        all_results.sort(key=lambda r: (r.fdr, r.source, r.term_id))
        return all_results, len(matched_gene_ids), total_terms_tested

    def _enrich_category(
        self,
        term_genes: dict[str, set[int]],
        term_meta: dict[str, tuple[str, str | None]],
        size_lookup: dict[str, tuple[int, int]],
        query_size: int,
        fdr_threshold: float,
    ) -> tuple[list[PathwayEnrichmentResult], int]:
        """
        STRING-style enrichment for one pathway source/category:
        - Only test terms that overlap the input gene list.
        - Pathway size 1: only tested when that gene is present (overlap > 0).
        - Exclude terms that could not pass BH even in the best-case overlap.
        - Apply BH FDR only across terms actually tested in this category.
        """
        candidate_ids = [term_id for term_id in term_genes if term_id in size_lookup]
        if not candidate_ids:
            return [], 0

        num_candidates = len(candidate_ids)

        tested_terms: list[tuple[str, set[int], int, int, float]] = []
        for term_id in candidate_ids:
            pathway_size, background_size = size_lookup[term_id]
            genes_in_term = term_genes[term_id]
            overlap = len(genes_in_term)

            if pathway_size == 1 and overlap == 0:
                continue

            best_overlap = min(query_size, pathway_size)
            if best_overlap == 0:
                continue
            p_best = self._fisher_enrichment_pvalue(best_overlap, query_size, pathway_size, background_size)
            if p_best > fdr_threshold / num_candidates:
                continue

            p_value = self._fisher_enrichment_pvalue(overlap, query_size, pathway_size, background_size)
            tested_terms.append((term_id, genes_in_term, pathway_size, background_size, p_value))

        if not tested_terms:
            return [], 0

        raw_p_values = [t[4] for t in tested_terms]
        fdr_values = self._benjamini_hochberg(raw_p_values)

        results: list[PathwayEnrichmentResult] = []
        for (term_id, genes_in_term, pathway_size, background_size, p_value), fdr in zip(tested_terms, fdr_values):
            if fdr <= fdr_threshold:
                src, desc = term_meta[term_id]
                results.append(
                    PathwayEnrichmentResult(
                        term_id=term_id,
                        source=src,
                        description=desc,
                        pathway_size=pathway_size,
                        background_size=background_size,
                        overlap=len(genes_in_term),
                        p_value=p_value,
                        fdr=fdr,
                        gene_ids=sorted(genes_in_term),
                    )
                )

        results.sort(key=lambda r: r.fdr)
        return results, len(tested_terms)
