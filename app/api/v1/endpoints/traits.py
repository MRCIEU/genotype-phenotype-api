import traceback
from fastapi import APIRouter, HTTPException, Path
from app.db.studies_db import StudiesDBClient
from app.models.schemas import Coloc, Study, ExtendedStudyExtraction, TraitResponse, Trait, VariantTypes, convert_duckdb_to_pydantic_model
from typing import List

router = APIRouter()

@router.get("/{trait_id}", response_model=TraitResponse)
async def get_study(trait_id: str = Path(..., description="Trait ID")) -> TraitResponse:
    try:
        db = StudiesDBClient()
        trait = db.get_trait(trait_id)
        if trait is None:
            raise HTTPException(status_code=400, detail=f"Trait {trait_id} not found")
        
        trait = convert_duckdb_to_pydantic_model(Trait, trait)
        studies = db.get_studies_by_trait_id(trait.id)
        print(studies)
        studies = convert_duckdb_to_pydantic_model(Study, studies)
        trait = populate_trait_studies(trait, studies)
        colocs = db.get_all_colocs_for_study(trait.common_study.id)

        study_extractions = db.get_study_extractions_for_study(trait.common_study.id)
        study_extractions = convert_duckdb_to_pydantic_model(ExtendedStudyExtraction, study_extractions)

        if colocs is not None:
            colocs = convert_duckdb_to_pydantic_model(Coloc, colocs)
            study_extraction_ids = [coloc.study_extraction_id for coloc in colocs]
            filtered_studies = [s for s in study_extractions if s.id not in study_extraction_ids]
        else:
            filtered_studies = study_extractions

        return TraitResponse(trait=trait, colocs=colocs, study_extractions=filtered_studies)
    except HTTPException as e:
        raise e
    except Exception as e:
        print(traceback.format_exc())
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
 