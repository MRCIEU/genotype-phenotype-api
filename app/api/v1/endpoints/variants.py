from fastapi import APIRouter, HTTPException, Path, Query
from app.db.duckdb import DuckDBClient
from app.models.schemas import Association, Coloc, ExtendedColoc, Variant, VariantResponse, convert_duckdb_to_pydantic_model
from typing import List


router = APIRouter()

@router.get("/associations", response_model=List[Association])
async def get_associations(
    variants: List[str] = Query(None, description="List of variants to filter results"),
    studies: List[str] = Query(None, description="List of studies to filter results"),
    p_value_threshold: float = Query(None, description="P-value threshold to filter results")
) -> List[Association]:
    try:
        db = DuckDBClient()
        associations = db.get_associations(variants, studies, p_value_threshold)
        associations = convert_duckdb_to_pydantic_model(Association, associations)

        return associations

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[Variant])
async def get_variants(
    variants: List[str] = Query(None, description="List of variants to filter results"),
    rsids: List[str] = Query(None, description="List of rsids to filter results"),
    grange: str = Query(None, description="grange to filter results"),
) -> List[Variant]:
    try:
        if sum([bool(variants), bool(rsids), bool(grange)]) > 1:
            raise HTTPException(status_code=400, detail="Only one of variants, rsids, or granges can be provided.")

        db = DuckDBClient()
        variants = db.get_variants(variants, rsids, grange)
        variants = convert_duckdb_to_pydantic_model(Variant, variants)

        return variants

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{variant_id}", response_model=VariantResponse)
async def get_variant(
    variant_id: str = Path(..., description="Variant ID to filter results"),
) -> VariantResponse:
    try:
        db = DuckDBClient()

        variant = db.get_variant(variant_id)
        colocs = db.get_colocs_for_variant(variant_id)
        colocs = convert_duckdb_to_pydantic_model(Coloc, colocs)
        variant = convert_duckdb_to_pydantic_model(Variant, variant)

        studies = [coloc.study for coloc in colocs]
        associations = db.get_associations_for_variant_and_studies(variant_id, studies)
        associations = convert_duckdb_to_pydantic_model(Association, associations)
        
        extended_colocs = []
        for coloc in colocs:
            association = next((u for u in associations if u.study == coloc.study), None)
            if association is None:
                #TODO: Remove this once we have fixed the data 
                print(f"Association not found for variant {variant_id} and study {coloc.study}")
                # raise HTTPException(status_code=400, detail="Association not found for variant and study")
            extended_colocs.append(ExtendedColoc(
                **coloc.model_dump(),
                association=association
            ))

        return VariantResponse(variant=variant, colocs=extended_colocs)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

