import traceback
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Request

from app.logging_config import get_logger, time_endpoint
from app.models.schemas import PathwayEnrichmentResponse
from app.rate_limiting import limiter, DEFAULT_RATE_LIMIT
from app.services.pathway_service import PathwayService, VALID_SOURCES

logger = get_logger(__name__)
router = APIRouter()


@router.get("/enrichment", response_model=PathwayEnrichmentResponse)
@time_endpoint
@limiter.limit(DEFAULT_RATE_LIMIT)
async def get_pathway_enrichment(
    request: Request,
    gene_ids: List[int] = Query(..., description="List of gene IDs (from gene_annotations) to test for enrichment"),
    source: Optional[str] = Query(None, description="Pathway source to filter by (Reactome, KEGG, or HP)"),
    p_value_threshold: float = Query(0.05, description="FDR-adjusted p-value threshold for filtering results"),
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

        pathway_service = PathwayService()
        results, matched_gene_count, total_terms_tested = pathway_service.get_pathway_enrichment(
            gene_ids=gene_ids,
            source=source,
            p_value_threshold=p_value_threshold,
        )

        return PathwayEnrichmentResponse(
            results=results,
            input_gene_count=len(gene_ids),
            matched_gene_count=matched_gene_count,
            source=source,
            p_value_threshold=p_value_threshold,
            total_terms_tested=total_terms_tested,
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in get_pathway_enrichment: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))
