import traceback
from fastapi import APIRouter, HTTPException, Path, Query
from app.db.studies_db import StudiesDBClient
from app.db.associations_db import AssociationsDBClient
from app.models.schemas import BasicTraitResponse, Coloc, GetTraitsResponse, RareResult, Study, ExtendedStudyExtraction, TraitResponse, Trait, VariantTypes, Association, convert_duckdb_to_pydantic_model
from typing import List
from app.logging_config import time_endpoint
router = APIRouter()


@router.get("/", response_model=GetTraitsResponse)
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
        raise HTTPException(status_code=500, detail=traceback.format_exc())

@router.get("/{trait_id}", response_model=TraitResponse)
@time_endpoint
async def get_trait(
    trait_id: str = Path(..., description="Trait ID"),
    include_associations: bool = Query(False, description="Whether to include associations for SNPs")
) -> TraitResponse:
    try:
        db = StudiesDBClient()
        associations_db = AssociationsDBClient()
        trait = db.get_trait(trait_id)
        if trait is None:
            raise HTTPException(status_code=404, detail=f"Trait {trait_id} not found")
        
        trait = convert_duckdb_to_pydantic_model(Trait, trait)
        studies = db.get_studies_by_trait_id(trait.id)
        studies = convert_duckdb_to_pydantic_model(Study, studies)
        trait = populate_trait_studies(trait, studies)
        if trait.rare_study is not None:
            rare_results = db.get_rare_results_for_study_ids([trait.rare_study.id])
            rare_results = convert_duckdb_to_pydantic_model(RareResult, rare_results)
        else:
            rare_results = []

        study_extractions = db.get_study_extractions_for_study(trait.common_study.id)
        study_extractions = convert_duckdb_to_pydantic_model(ExtendedStudyExtraction, study_extractions)

        colocs = db.get_all_colocs_for_study(trait.common_study.id)
        if colocs is not None:
            colocs = convert_duckdb_to_pydantic_model(Coloc, colocs)
            study_extraction_ids = [coloc.study_extraction_id for coloc in colocs]
            filtered_studies = [s for s in study_extractions if s.id not in study_extraction_ids]
        else:
            filtered_studies = study_extractions

        # Get associations if requested
        associations = None
        if include_associations:
            # Get all SNP IDs from study extractions
            snp_ids = [s.snp_id for s in study_extractions]
            # Get all study IDs
            study_ids = [trait.common_study.id]
            if trait.rare_study is not None:
                study_ids.append(trait.rare_study.id)
            # Get associations
            associations = associations_db.get_associations(snp_ids, study_ids, None)
            associations = convert_duckdb_to_pydantic_model(Association, associations)
        
        return TraitResponse(
            trait=trait, 
            colocs=colocs, 
            rare_results=rare_results, 
            study_extractions=filtered_studies,
            associations=associations
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=traceback.format_exc())

def populate_trait_studies(trait: Trait, studies: List[Study]):
    common_study = None
    rare_study = None
    for study in studies:
        if study.variant_type == VariantTypes.COMMON.value:
            common_study = study
        else:
            rare_study = study
    trait.common_study = common_study
    trait.rare_study = rare_study
    return trait
 