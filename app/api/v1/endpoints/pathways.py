import traceback
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from scipy.stats import fisher_exact

from app.db.studies_db import StudiesDBClient
from app.logging_config import get_logger, time_endpoint
from app.models.schemas import (
    PathwayEnrichmentResponse,
    PathwayEnrichmentResult,
)
from app.rate_limiting import limiter, DEFAULT_RATE_LIMIT

logger = get_logger(__name__)
router = APIRouter()

VALID_SOURCES = {"Reactome", "KEGG", "HP"}


@router.get("/enrichment", response_model=PathwayEnrichmentResponse)
@time_endpoint
@limiter.limit(DEFAULT_RATE_LIMIT)
async def get_pathway_enrichment(
    request: Request,
    gene_ids: List[int] = Query(..., description="List of gene IDs (from gene_annotations) to test for enrichment"),
    source: Optional[str] = Query(None, description="Pathway source to filter by (Reactome, KEGG, or HP)"),
    p_value_threshold: float = Query(0.05, description="P-value threshold for filtering results"),
) -> PathwayEnrichmentResponse:
    try:
        if source and source not in VALID_SOURCES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid source '{source}'. Must be one of: {', '.join(sorted(VALID_SOURCES))}",
            )

        if not gene_ids:
            raise HTTPException(status_code=400, detail="At least one gene_id is required")

        if p_value_threshold <= 0 or p_value_threshold > 1:
            raise HTTPException(status_code=400, detail="p_value_threshold must be between 0 and 1")

        studies_db = StudiesDBClient()

        mappings = studies_db.get_pathway_mappings_for_genes(gene_ids, source)
        if not mappings:
            return PathwayEnrichmentResponse(
                results=[],
                input_gene_count=len(gene_ids),
                matched_gene_count=0,
                source=source,
                p_value_threshold=p_value_threshold,
            )

        # gene_id, term_id, source, description
        matched_gene_ids = set()
        term_genes: dict[str, set[int]] = {}
        term_meta: dict[str, tuple[str, str | None]] = {}
        for gene_id, term_id, src, desc in mappings:
            matched_gene_ids.add(gene_id)
            term_genes.setdefault(term_id, set()).add(gene_id)
            if term_id not in term_meta:
                term_meta[term_id] = (src, desc)

        term_ids = list(term_genes.keys())
        pathway_sizes_rows = studies_db.get_pathway_sizes(term_ids, source)

        # term_id -> (pathway_size, background_size)
        size_lookup: dict[str, tuple[int, int]] = {}
        for term_id, _, _, pathway_size, background_size in pathway_sizes_rows:
            size_lookup[term_id] = (pathway_size, background_size)

        matched_count = len(matched_gene_ids)
        results: list[PathwayEnrichmentResult] = []

        for term_id, genes_in_term in term_genes.items():
            if term_id not in size_lookup:
                continue

            pathway_size, background_size = size_lookup[term_id]
            overlap = len(genes_in_term)

            # One-tailed Fisher's exact test (over-representation)
            #                  In pathway    Not in pathway
            # In gene list     a             b
            # Not in gene list c             d
            a = overlap
            b = matched_count - overlap
            c = pathway_size - overlap
            d = background_size - pathway_size - b

            if d < 0:
                d = 0

            _, p_value = fisher_exact([[a, b], [c, d]], alternative="greater")

            if p_value <= p_value_threshold:
                src, desc = term_meta[term_id]
                results.append(
                    PathwayEnrichmentResult(
                        term_id=term_id,
                        source=src,
                        description=desc,
                        pathway_size=pathway_size,
                        overlap=overlap,
                        p_value=p_value,
                        gene_ids=sorted(genes_in_term),
                    )
                )

        results.sort(key=lambda r: r.p_value)

        return PathwayEnrichmentResponse(
            results=results,
            input_gene_count=len(gene_ids),
            matched_gene_count=matched_count,
            source=source,
            p_value_threshold=p_value_threshold,
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in get_pathway_enrichment: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))
