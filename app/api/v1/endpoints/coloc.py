from fastapi import APIRouter, HTTPException
from app.models.schemas import Coloc
from typing import List

router = APIRouter()

@router.get("/", response_model=List[Coloc])
async def get_colocs():
    return []

@router.get("/{coloc_id}", response_model=Coloc)
async def get_coloc(coloc_id: str):
    return {}
