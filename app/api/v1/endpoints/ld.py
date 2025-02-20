from fastapi import APIRouter, HTTPException, Query
from app.db.duckdb import DuckDBClient
from app.models.schemas import Ld, convert_duckdb_to_pydantic_model
from typing import List

router = APIRouter()

@router.get("/matrix", response_model=List[Ld])
async def get_matrix(
    variants: List[str] = Query(None, description="List of variants to filter results"),
):
    try:
        db = DuckDBClient()
        ld_matrix = db.get_ld_matrix(variants)
        response = convert_duckdb_to_pydantic_model(Ld, ld_matrix)
        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/proxies", response_model=List[Ld])
async def get_proxies(
    variants: List[str] = Query(None, description="List of variants to filter results"),
):
    try:
        db = DuckDBClient()
        ld_proxies = db.get_ld_proxies(variants)
        response = convert_duckdb_to_pydantic_model(Ld, ld_proxies)
        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

