import traceback
from fastapi import APIRouter, HTTPException, Path, Query
from fastapi.responses import StreamingResponse
from app.db.coloc_pairs_db import ColocPairsDBClient
from app.db.studies_db import StudiesDBClient
from app.models.schemas import (
    BasicTraitResponse,
    ColocGroup,
    GetTraitsResponse,
    RareResult,
    Study,
    ExtendedStudyExtraction,
    TraitResponse,
    Trait,
    VariantType,
    convert_duckdb_to_pydantic_model,
)
from typing import List
from app.logging_config import get_logger, time_endpoint
from app.services.associations_service import AssociationsService

router = APIRouter()

logger = get_logger(__name__)


@router.get("", response_model=GetTraitsResponse)
@time_endpoint
async def get_traits() -> GetTraitsResponse:
    try:
        db = StudiesDBClient()
        traits = db.get_traits()
        traits = convert_duckdb_to_pydantic_model(BasicTraitResponse, traits)
        return GetTraitsResponse(traits=traits)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in get_traits: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=traceback.format_exc())


@router.get("/{trait_id}", response_model=TraitResponse)
@time_endpoint
async def get_trait(
    trait_id: str = Path(..., description="Trait ID"),
    include_associations: bool = Query(False, description="Whether to include associations for SNPs"),
) -> TraitResponse:
    try:
        studies_db = StudiesDBClient()
        associations_service = AssociationsService()

        trait = studies_db.get_trait(trait_id)
        if trait is None:
            raise HTTPException(status_code=404, detail=f"Trait {trait_id} not found")

        trait = convert_duckdb_to_pydantic_model(Trait, trait)
        studies = studies_db.get_studies_by_trait_id(trait.id)
        studies = convert_duckdb_to_pydantic_model(Study, studies)
        trait = populate_trait_studies(trait, studies)
        if trait.rare_study is not None:
            rare_results = studies_db.get_rare_results_for_study_id(trait.rare_study.id)
            rare_results = convert_duckdb_to_pydantic_model(RareResult, rare_results)
        else:
            rare_results = []

        study_extractions = studies_db.get_study_extractions_for_study(trait.common_study.id)
        study_extractions = convert_duckdb_to_pydantic_model(ExtendedStudyExtraction, study_extractions)

        colocs = studies_db.get_all_colocs_for_study(trait.common_study.id)
        if colocs is not None:
            colocs = convert_duckdb_to_pydantic_model(ColocGroup, colocs)
        else:
            colocs = []

        associations = None
        if include_associations:
            associations = associations_service.get_associations(colocs, rare_results, trait.id)

        return TraitResponse(
            trait=trait,
            coloc_groups=colocs,
            rare_results=rare_results,
            study_extractions=study_extractions,
            associations=associations,
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in get_trait: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=traceback.format_exc())


@router.get("/{trait_id}/coloc-pairs")
@time_endpoint
async def get_trait_coloc_pairs(
    trait_id: str = Path(..., description="Trait ID"),
    h3_threshold: float = Query(0.0, description="H3 threshold for coloc pairs"),
    h4_threshold: float = Query(0.8, description="H4 threshold for coloc pairs"),
) -> StreamingResponse:
    try:
        studies_db = StudiesDBClient()
        coloc_pairs_db = ColocPairsDBClient()

        trait = studies_db.get_trait(trait_id)
        if trait is None:
            raise HTTPException(status_code=404, detail=f"Trait {trait_id} not found")

        trait = convert_duckdb_to_pydantic_model(Trait, trait)
        studies = studies_db.get_studies_by_trait_id(trait.id)
        studies = convert_duckdb_to_pydantic_model(Study, studies)
        trait = populate_trait_studies(trait, studies)

        colocs = studies_db.get_all_colocs_for_study(trait.common_study.id)
        if colocs is not None:
            colocs = convert_duckdb_to_pydantic_model(ColocGroup, colocs)
        else:
            colocs = []

        snp_ids = sorted([coloc.snp_id for coloc in colocs])
        coloc_pairs = coloc_pairs_db.get_coloc_pairs_by_snp_ids_stream(snp_ids, h3_threshold, h4_threshold)
        return StreamingResponse(coloc_pairs, media_type="application/json")
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in get_trait_coloc_pairs: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=traceback.format_exc())


def populate_trait_studies(trait: Trait, studies: List[Study]):
    common_study = None
    rare_study = None
    for study in studies:
        if study.variant_type == VariantType.common.value:
            common_study = study
        else:
            rare_study = study
    trait.common_study = common_study
    trait.rare_study = rare_study
    return trait
