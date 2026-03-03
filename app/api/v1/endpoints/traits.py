import traceback
from fastapi import APIRouter, HTTPException, Path, Query, Request
from app.services.coloc_pairs_service import ColocPairsService
from app.db.studies_db import StudiesDBClient
from app.models.schemas import (
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
from app.rate_limiting import limiter, DEFAULT_RATE_LIMIT
from app.services.associations_service import AssociationsService
from app.config import get_settings
from app.services.studies_service import StudiesService


router = APIRouter()

logger = get_logger(__name__)
settings = get_settings()


@router.get("", response_model=GetTraitsResponse)
@time_endpoint
@limiter.limit(DEFAULT_RATE_LIMIT)
async def get_traits(
    request: Request,
    ids: List[str] = Query(None, description="List of trait IDs or names to filter results"),
    include_associations: bool = Query(False, description="Whether to include associations for SNPs"),
) -> GetTraitsResponse:
    try:
        studies_service = StudiesService()
        if not ids:
            traits = studies_service.get_traits()
            return traits

        maximum_num_traits = 10
        if len(ids) > maximum_num_traits:
            raise HTTPException(
                status_code=400, detail=f"Can not request more than {maximum_num_traits} in one request"
            )

        studies_db = StudiesDBClient()
        associations_service = AssociationsService()

        # 1. Get basic trait info for all requested traits
        trait_data = studies_db.get_traits_by_ids(ids)
        if not trait_data:
            return GetTraitsResponse(traits=[])

        traits = convert_duckdb_to_pydantic_model(Trait, trait_data)
        if not isinstance(traits, list):
            traits = [traits]

        trait_map = {t.id: t for t in traits}
        trait_ids_numeric = list(trait_map.keys())

        # 2. Get all studies for these traits
        all_studies = studies_service.get_studies_by_trait_ids(trait_ids_numeric)

        # Group studies by trait_id
        studies_by_trait = {}
        for study in all_studies:
            if study.trait_id not in studies_by_trait:
                studies_by_trait[study.trait_id] = []
            studies_by_trait[study.trait_id].append(study)

        # Populate traits with their studies
        for tid, t in trait_map.items():
            populate_trait_studies(t, studies_by_trait.get(tid, []))

        # 3. Get rare results, study extractions, and colocs for all relevant studies
        all_study_ids = []
        for t in traits:
            if t.common_study:
                all_study_ids.append(t.common_study.id)
            if t.rare_study:
                all_study_ids.append(t.rare_study.id)

        rare_results_map = {}
        study_extractions_map = {}
        colocs_map = {}

        if all_study_ids:
            # Batch fetch
            all_rare_data = studies_db.get_rare_results_for_study_ids(all_study_ids)
            all_extractions_data = studies_db.get_study_extractions_for_studies(all_study_ids)
            all_colocs_data = studies_db.get_all_colocs_for_study_ids(all_study_ids)

            # Convert and group
            if all_rare_data:
                rare_results = convert_duckdb_to_pydantic_model(RareResult, all_rare_data)
                for r in rare_results:
                    if r.study_id not in rare_results_map:
                        rare_results_map[r.study_id] = []
                    rare_results_map[r.study_id].append(r)

            if all_extractions_data:
                extractions = convert_duckdb_to_pydantic_model(ExtendedStudyExtraction, all_extractions_data)
                for e in extractions:
                    if e.study_id not in study_extractions_map:
                        study_extractions_map[e.study_id] = []
                    study_extractions_map[e.study_id].append(e)

            if all_colocs_data:
                colocs = convert_duckdb_to_pydantic_model(ColocGroup, all_colocs_data)
                for c in colocs:
                    if c.study_id not in colocs_map:
                        colocs_map[c.study_id] = []
                    colocs_map[c.study_id].append(c)

        # 4. Construct final responses
        trait_responses = []
        for t in traits:
            t_rare = []
            if t.rare_study and t.rare_study.id in rare_results_map:
                t_rare = rare_results_map[t.rare_study.id]

            t_extractions = []
            if t.common_study and t.common_study.id in study_extractions_map:
                t_extractions.extend(study_extractions_map[t.common_study.id])
            if t.rare_study and t.rare_study.id in study_extractions_map:
                t_extractions.extend(study_extractions_map[t.rare_study.id])

            t_colocs = []
            if t.common_study and t.common_study.id in colocs_map:
                t_colocs = colocs_map[t.common_study.id]
            elif t.rare_study and t.rare_study.id in colocs_map:
                t_colocs = colocs_map[t.rare_study.id]

            associations = None
            if include_associations:
                associations = associations_service.get_associations(t_colocs, t_rare, t_extractions)

            trait_responses.append(
                TraitResponse(
                    trait=t,
                    coloc_groups=t_colocs,
                    rare_results=t_rare,
                    study_extractions=t_extractions,
                    associations=associations,
                )
            )

        return GetTraitsResponse(traits=trait_responses)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in get_traits: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=traceback.format_exc())


@router.get("/{trait_id}", response_model=TraitResponse)
@time_endpoint
@limiter.limit(DEFAULT_RATE_LIMIT)
async def get_trait(
    request: Request,
    trait_id: str = Path(..., description="Trait ID or name"),
    include_associations: bool = Query(False, description="Whether to include associations for SNPs"),
) -> TraitResponse:
    try:
        studies_db = StudiesDBClient()
        associations_service = AssociationsService()

        if not trait_id.isdigit():
            trait_id = trait_id.replace("_", "-")

        trait = studies_db.get_trait(trait_id)
        if trait is None:
            raise HTTPException(status_code=404, detail=f"Trait {trait_id} not found")

        trait = convert_duckdb_to_pydantic_model(Trait, trait)
        studies_service = StudiesService()
        studies = studies_service.get_studies_by_trait_ids([trait.id])
        trait = populate_trait_studies(trait, studies)
        rare_results = []
        study_extractions = []
        colocs = []

        if trait.rare_study is not None:
            rare_results_data = studies_db.get_rare_results_for_study_id(trait.rare_study.id)
            rare_results = convert_duckdb_to_pydantic_model(RareResult, rare_results_data) if rare_results_data else []

        study_ids = [study.id for study in [trait.common_study, trait.rare_study] if study is not None]
        if study_ids:
            study_extractions_data = studies_db.get_study_extractions_for_studies(study_ids)
            study_extractions = (
                convert_duckdb_to_pydantic_model(ExtendedStudyExtraction, study_extractions_data)
                if study_extractions_data
                else []
            )

            colocs_data = studies_db.get_all_colocs_for_study_ids(study_ids)
            if colocs_data:
                colocs = convert_duckdb_to_pydantic_model(ColocGroup, colocs_data)

        associations = None
        if include_associations:
            associations = associations_service.get_associations(colocs, rare_results, study_extractions)

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
@limiter.limit(DEFAULT_RATE_LIMIT)
async def get_trait_coloc_pairs(
    request: Request,
    trait_id: str = Path(..., description="Trait ID or name"),
    h3_threshold: float = Query(0.0, description="H3 threshold for coloc pairs"),
    h4_threshold: float = Query(0.8, description="H4 threshold for coloc pairs"),
) -> dict:
    try:
        studies_db = StudiesDBClient()
        coloc_pairs_service = ColocPairsService()

        trait = studies_db.get_trait(trait_id)
        if trait is None:
            raise HTTPException(status_code=404, detail=f"Trait {trait_id} not found")

        trait = convert_duckdb_to_pydantic_model(Trait, trait)
        studies_service = StudiesService()
        studies = studies_service.get_studies_by_trait_ids([trait.id])
        trait = populate_trait_studies(trait, studies)

        study_ids = [study.id for study in [trait.common_study, trait.rare_study] if study is not None]
        colocs_data = studies_db.get_all_colocs_for_study_ids(study_ids) if study_ids else []
        if colocs_data:
            colocs = convert_duckdb_to_pydantic_model(ColocGroup, colocs_data)
        else:
            colocs = []

        snp_ids = sorted([coloc.snp_id for coloc in colocs])
        coloc_pairs = coloc_pairs_service.get_coloc_pairs_full(
            snp_ids, h3_threshold=h3_threshold, h4_threshold=h4_threshold
        )
        if coloc_pairs:
            pair_columns = list(coloc_pairs[0].keys())
            pair_rows = [[d[col] for col in pair_columns] for d in coloc_pairs]
        else:
            pair_columns = []
            pair_rows = []
        return {"coloc_pair_column_names": pair_columns, "coloc_pair_rows": pair_rows}

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
