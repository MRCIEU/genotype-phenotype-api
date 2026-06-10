from typing import List, Optional

from scipy.stats import fisher_exact

from app.db.studies_db import StudiesDBClient
from app.logging_config import get_logger
from app.models.schemas import PathwayEnrichmentResult

logger = get_logger(__name__)

VALID_SOURCES = {"Reactome", "KEGG", "HP"}


class UnknownGenesError(Exception):
    def __init__(self, unknown_genes: list[str | int]):
        self.unknown_genes = unknown_genes
        super().__init__(f"Unknown genes: {', '.join(str(g) for g in unknown_genes)}")


class PathwayService:
    def __init__(self):
        self.studies_db = StudiesDBClient()

    def resolve_genes(self, genes: List[str | int]) -> list[int]:
        """Resolve gene symbols or numeric IDs to gene_annotations IDs."""
        rows = self.studies_db.get_genes_by_ids(genes)
        ids_found = {row[0] for row in rows}
        symbols_to_id = {row[2]: row[0] for row in rows}

        resolved: list[int] = []
        unknown: list[str | int] = []
        for gene in genes:
            if isinstance(gene, int) or (isinstance(gene, str) and gene.isdigit()):
                gene_id = int(gene)
                if gene_id in ids_found:
                    resolved.append(gene_id)
                else:
                    unknown.append(gene)
            elif gene in symbols_to_id:
                resolved.append(symbols_to_id[gene])
            else:
                unknown.append(gene)

        if unknown:
            raise UnknownGenesError(unknown)
        return resolved

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
        genes: List[str | int],
        source: Optional[str] = None,
        p_value_threshold: float = 0.05,
        minimum_count_in_network: int = 2,
    ) -> tuple[list[PathwayEnrichmentResult], int, int]:
        """
        Run STRING-style pathway enrichment for the given genes.

        Returns (results, matched_gene_count, total_terms_tested).
        """
        gene_ids = self.resolve_genes(genes)
        unique_gene_ids = list(set(gene_ids))
        query_size = len(unique_gene_ids)

        mappings = self.studies_db.get_pathway_mappings_for_genes(unique_gene_ids, source)
        if not mappings:
            return [], 0, 0

        matched_gene_ids = set()
        term_genes_by_source: dict[str, dict[str, set[int]]] = {}
        for gene_id, term_id, src, _desc in mappings:
            matched_gene_ids.add(gene_id)
            term_genes_by_source.setdefault(src, {}).setdefault(term_id, set()).add(gene_id)

        sources_to_test = [source] if source else sorted(term_genes_by_source.keys())
        all_results: list[PathwayEnrichmentResult] = []
        total_terms_tested = 0

        for src in sources_to_test:
            term_genes = term_genes_by_source.get(src, {})
            if not term_genes:
                continue

            all_pathway_sizes = self.studies_db.get_all_pathway_sizes(src)
            category_results, category_tested = self._enrich_category(
                term_genes=term_genes,
                all_pathway_sizes=all_pathway_sizes,
                query_size=query_size,
                fdr_threshold=p_value_threshold,
                minimum_count_in_network=minimum_count_in_network,
            )
            all_results.extend(category_results)
            total_terms_tested += category_tested

        all_results = self._attach_pathway_gene_ids(all_results)
        all_results.sort(key=lambda r: (r.fdr, r.source, r.term_id))
        return all_results, len(matched_gene_ids), total_terms_tested

    def _attach_pathway_gene_ids(self, results: list[PathwayEnrichmentResult]) -> list[PathwayEnrichmentResult]:
        if not results:
            return results

        term_ids_by_source: dict[str, list[str]] = {}
        for result in results:
            term_ids_by_source.setdefault(result.source, []).append(result.term_id)

        pathway_genes_by_term: dict[tuple[str, str], list[int]] = {}
        for src, term_ids in term_ids_by_source.items():
            for term_id, gene_id in self.studies_db.get_pathway_genes_for_terms(term_ids, src):
                pathway_genes_by_term.setdefault((term_id, src), []).append(gene_id)

        return [
            result.model_copy(
                update={"pathway_gene_ids": pathway_genes_by_term.get((result.term_id, result.source), [])}
            )
            for result in results
        ]

    def _enrich_category(
        self,
        term_genes: dict[str, set[int]],
        all_pathway_sizes: list[tuple],
        query_size: int,
        fdr_threshold: float,
        minimum_count_in_network: int,
    ) -> tuple[list[PathwayEnrichmentResult], int]:
        """
        STRING-style enrichment for one pathway source/category:
        - Query size is the full submitted gene list (STRING foreground).
        - Only terms with overlap >= minimum_count_in_network are tested and included in BH FDR.
        - Only significant overlapping terms are returned.
        """
        if not all_pathway_sizes:
            return [], 0

        tested_terms: list[tuple[str, set[int], str, str | None, int, int, float]] = []
        for term_id, src, desc, pathway_size, background_size in all_pathway_sizes:
            genes_in_term = term_genes.get(term_id, set())
            overlap = len(genes_in_term)

            if overlap < minimum_count_in_network:
                continue

            p_value = self._fisher_enrichment_pvalue(overlap, query_size, pathway_size, background_size)
            tested_terms.append((term_id, genes_in_term, src, desc, pathway_size, background_size, p_value))

        if not tested_terms:
            return [], 0

        raw_p_values = [t[6] for t in tested_terms]
        fdr_values = self._benjamini_hochberg(raw_p_values)

        results: list[PathwayEnrichmentResult] = []
        for (term_id, genes_in_term, src, desc, pathway_size, background_size, p_value), fdr in zip(
            tested_terms, fdr_values
        ):
            if fdr <= fdr_threshold:
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
                        pathway_gene_ids=[],
                    )
                )

        results.sort(key=lambda r: r.fdr)
        return results, len(tested_terms)
