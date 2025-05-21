import traceback
from fastapi import APIRouter, HTTPException, Request, Response
from app.db.ld_db import LdDBClient
from app.db.studies_db import StudiesDBClient
from app.models.schemas import Coloc, ExtendedVariant, Ld, SearchTerm, VariantSearchResponse, convert_duckdb_to_pydantic_model
from typing import List
from app.logging_config import get_logger, time_endpoint
from app.services.cache_service import DBCacheService

logger = get_logger(__name__)
router = APIRouter()


@router.get("/options", response_model=List[SearchTerm])
@time_endpoint
async def get_search_options(request: Request, response: Response):
    try:
        # Add cache control headers
        response.headers['Cache-Control'] = 'no-cache, must-revalidate'
        response.headers['Pragma'] = 'no-cache'

        cache_service = DBCacheService()
        search_terms = cache_service.get_search_terms()
        return search_terms

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in get_search_options: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/variant/{search_term}", response_model=VariantSearchResponse)
@time_endpoint
async def search(search_term: str):
    try:
        cache_service = DBCacheService()
        studies_db = StudiesDBClient()
        ld_db = LdDBClient()

        original_variants = []
        if search_term.startswith("rs"):
            original_variants = studies_db.get_variants(rsids=[search_term])
        elif any(c.isdigit() for c in search_term) and ":" in search_term:
            original_variants = studies_db.get_variants(variant_prefixes=[search_term])
        
        if not original_variants: return VariantSearchResponse(original_variants=[], proxy_variants=[]) 
        
        original_variants = convert_duckdb_to_pydantic_model(ExtendedVariant, original_variants)
        snp_ids = [variant.id for variant in original_variants]
        proxies = ld_db.get_ld_proxies(snp_ids=snp_ids)
        proxies = convert_duckdb_to_pydantic_model(Ld, proxies)
        proxy_snp_ids = list(set([proxy.lead_snp_id for proxy in proxies] + [proxy.variant_snp_id for proxy in proxies]))
        proxy_snp_ids = [snp_id for snp_id in proxy_snp_ids if snp_id not in snp_ids]

        variant_proxies = studies_db.get_variants(snp_ids=proxy_snp_ids)
        proxy_variants = convert_duckdb_to_pydantic_model(ExtendedVariant, variant_proxies)

        all_snp_ids = list(set(snp_ids + proxy_snp_ids))
        colocs = studies_db.get_colocs_for_variants(snp_ids=all_snp_ids)
        colocs = convert_duckdb_to_pydantic_model(Coloc, colocs)

        # TODO: Add rare variants
        for variant in original_variants:
            variant.num_colocs = len(set([coloc.coloc_group_id for coloc in colocs if coloc.snp_id == variant.id]))
            variant.ld_proxies = [proxy for proxy in proxies if proxy.lead_snp_id == variant.id or proxy.variant_snp_id == variant.id]
        for variant in proxy_variants:
            variant.num_colocs = len(set([coloc.coloc_group_id for coloc in colocs if coloc.snp_id == variant.id]))
            variant.ld_proxies = [proxy for proxy in proxies if proxy.lead_snp_id == variant.id or proxy.variant_snp_id == variant.id]

        proxy_variants = [variant for variant in proxy_variants if variant.num_colocs > 0]
        proxy_variants.sort(key=lambda x: x.num_colocs, reverse=True)

        return VariantSearchResponse(original_variants=original_variants, proxy_variants=proxy_variants)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in search variant: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))
