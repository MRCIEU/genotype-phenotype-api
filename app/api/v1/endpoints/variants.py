from fastapi import APIRouter, HTTPException, Path, Query
from app.db.associations_db import AssociationsDBClient
from app.db.studies_db import StudiesDBClient
from app.models.schemas import Association, Coloc, ExtendedColoc, ExtendedRareResult, RareResult, Variant, VariantResponse, convert_duckdb_to_pydantic_model
from typing import List
from app.logging_config import get_logger, time_endpoint

logger = get_logger(__name__)
router = APIRouter()

@router.get("/associations", response_model=List[Association])
@time_endpoint
async def get_associations(
    snp_ids: List[int] = Query(None, description="List of snp_ids to filter results"),
    study_ids: List[int] = Query(None, description="List of study_ids to filter results"),
    p_value_threshold: float = Query(None, description="P-value threshold to filter results")
) -> List[Association]:
    try:
        db = AssociationsDBClient()
        if p_value_threshold and not (snp_ids or study_ids):
            raise HTTPException(status_code=400, detail="p_value_threshold must be accompanied by either snp_ids or study_ids")

        associations = db.get_associations(snp_ids, study_ids, p_value_threshold)
        associations = convert_duckdb_to_pydantic_model(Association, associations)

        return associations

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in get_associations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[Variant])
@time_endpoint
async def get_variants(
    snp_ids: List[int] = Query(None, description="List of snp_ids to filter results"),
    variants: List[str] = Query(None, description="List of variants to filter results"),
    rsids: List[str] = Query(None, description="List of rsids to filter results"),
    grange: str = Query(None, description="grange to filter results"),
) -> List[Variant]:
    try:
        if sum([bool(snp_ids), bool(rsids), bool(grange)]) > 1:
            raise HTTPException(status_code=400, detail="Only one of snp_ids, rsids, or grange can be provided.")

        db = StudiesDBClient()
        variants = db.get_variants(snp_ids=snp_ids, variants=variants, rsids=rsids, grange=grange)
        variants = convert_duckdb_to_pydantic_model(Variant, variants)

        return variants

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in get_variants: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{snp_id}", response_model=VariantResponse)
@time_endpoint
async def get_variant(
    snp_id: int = Path(..., description="Variant ID to filter results"),
) -> VariantResponse:
    try:
        studies_db = StudiesDBClient()
        associations_db = AssociationsDBClient()

        variant = studies_db.get_variant(snp_id)
        if variant is None:
            raise HTTPException(status_code=404, detail="Variant not found")
        colocs = studies_db.get_colocs_for_variants([snp_id])
        rare_results = studies_db.get_rare_results_for_variants([snp_id])

        if not colocs and not rare_results:
            variant = convert_duckdb_to_pydantic_model(Variant, variant)
            return VariantResponse(variant=variant, colocs=[], rare_results=[])

        colocs = convert_duckdb_to_pydantic_model(Coloc, colocs)
        rare_results = convert_duckdb_to_pydantic_model(RareResult, rare_results)
        variant = convert_duckdb_to_pydantic_model(Variant, variant)

        study_ids = [coloc.study_id for coloc in colocs] + [rare_result.study_id for rare_result in rare_results]
        associations = associations_db.get_associations_for_variant_and_studies(snp_id, study_ids)
        associations = convert_duckdb_to_pydantic_model(Association, associations)
        
        extended_colocs = []
        for coloc in colocs:
            association = next((u for u in associations if u.study_id == coloc.study_id), None)
            if association is None:
                #TODO: Remove this once we have fixed the data 
                logger.warning(f"Association not found for variant {snp_id} and study {coloc.study_id}")
                # raise HTTPException(status_code=400, detail="Association not found for variant and study")
            extended_colocs.append(ExtendedColoc(
                **coloc.model_dump(),
                association=association
            ))
        extended_rare_results = []
        for rare_result in rare_results:
            association = next((u for u in associations if u.study_id == rare_result.study_id), None)
            if association is None:
                #TODO: Remove this once we have fixed the data 
                logger.warning(f"Association not found for variant {snp_id} and study {rare_result.study_id}")
                # raise HTTPException(status_code=400, detail="Association not found for variant and study")
            extended_rare_results.append(ExtendedRareResult(
                **rare_result.model_dump(),
                association=association
            ))

        return VariantResponse(variant=variant, colocs=extended_colocs, rare_results=extended_rare_results)

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in get_variant: {e}")
        raise HTTPException(status_code=500, detail=str(e))

