import traceback
from fastapi import APIRouter, HTTPException, Path
from app.db.studies_db import StudiesDBClient
from app.models.schemas import Coloc, RareResult, Study, ExtendedStudyExtraction, TraitResponse, Trait, VariantTypes, convert_duckdb_to_pydantic_model
from typing import List, Union
from app.logging_config import time_endpoint
from pydantic import BaseModel, validator

class TraitId(BaseModel):
    trait_id: Union[int, str]

router = APIRouter()

@router.get("/{trait_id}", response_model=TraitResponse)
@time_endpoint
async def get_trait(trait_id: TraitId = Path(..., description="Trait ID (can be integer or string)")) -> TraitResponse:
    try:
        db = StudiesDBClient()

        if isinstance(trait_id, int):
            trait = db.get_trait(trait_id)
        else:
            trait = db.get_trait_by_name(trait_id)

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
        
        return TraitResponse(trait=trait, colocs=colocs, rare_results=rare_results, study_extractions=filtered_studies)
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
 