from fastapi import APIRouter, HTTPException
from app.models.schemas import SearchTerm
from typing import List

from app.services.cache_service import CacheService


router = APIRouter()

@router.get("/options", response_model=List[SearchTerm])
async def get_search_options():
    try:
        cache_service = CacheService()
        search_terms = cache_service.get_study_names_for_search()
        genes = cache_service.get_genes()

        search_terms = [{"type": "study", "name": term[1], "type_id": term[0]} for term in search_terms]
        genes = [{"type": "gene", "name": gene[0], "type_id": gene[0]} for gene in genes]
        search_terms.extend(genes)
        search_terms = [term for term in search_terms if term['name'] is not None]
        return search_terms

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

