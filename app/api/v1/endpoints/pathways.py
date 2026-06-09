import traceback

from fastapi import APIRouter, HTTPException, Request

from app.logging_config import get_logger, time_endpoint
from app.models.schemas import PathwayEnrichmentRequest, PathwayEnrichmentResponse
from app.rate_limiting import limiter, DEFAULT_RATE_LIMIT
from app.services.pathway_service import PathwayService, VALID_SOURCES

logger = get_logger(__name__)
router = APIRouter()


@router.post("/enrichment", response_model=PathwayEnrichmentResponse)
@time_endpoint
@limiter.limit(DEFAULT_RATE_LIMIT)
async def pathway_enrichment(
    request: Request,
    body: PathwayEnrichmentRequest,
) -> PathwayEnrichmentResponse:
    try:
        if body.source and body.source not in VALID_SOURCES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid source '{body.source}'. Must be one of: {', '.join(sorted(VALID_SOURCES))}",
            )

        pathway_service = PathwayService()
        results, matched_gene_count, total_terms_tested = pathway_service.get_pathway_enrichment(
            gene_ids=body.gene_ids,
            source=body.source,
            p_value_threshold=body.p_value_threshold,
        )

        return PathwayEnrichmentResponse(
            results=results,
            input_gene_count=len(body.gene_ids),
            matched_gene_count=matched_gene_count,
            source=body.source,
            p_value_threshold=body.p_value_threshold,
            total_terms_tested=total_terms_tested,
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in pathway_enrichment: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))
