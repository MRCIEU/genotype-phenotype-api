from fastapi import APIRouter, HTTPException, Query
from app.db.duckdb import DuckDBClient
from app.models.schemas import Ld, convert_duckdb_to_pydantic_model
from typing import List

router = APIRouter()

@router.get("/matrix", response_model=List[Ld])
async def get_matrix(
    variants: List[str] = Query(None, description="List of variants to filter results"),
    snp_ids: List[int] = Query(None, description="List of snp_ids to filter results")
):
    try:
        db = DuckDBClient()
        if variants:
            snp_ids = db.get_snp_ids_by_variants(variants)
        ld_matrix = db.get_ld_matrix(snp_ids)
        if ld_matrix is None:
            raise HTTPException(status_code=404, detail=f"LD matrix for variants {variants} not found")
        response = convert_duckdb_to_pydantic_model(Ld, ld_matrix)
        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/proxies", response_model=List[Ld])
async def get_proxies(
    variants: List[str] = Query(None, description="List of variants to filter results"),
    snp_ids: List[int] = Query(None, description="List of snp_ids to filter results")
):
    try:
        db = DuckDBClient()
        if variants:
            snp_ids = db.get_snp_ids_by_variants(variants)

        ld_proxies = db.get_ld_proxies(snp_ids)
        ld_proxies = db.get_ld_proxies(snp_ids)
        if ld_proxies is None:
            raise HTTPException(status_code=404, detail=f"LD proxies for snp_ids {snp_ids} not found")
        response = convert_duckdb_to_pydantic_model(Ld, ld_proxies)
        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

