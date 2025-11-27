import traceback
from fastapi import APIRouter, HTTPException, Path, Query, Request
from fastapi.responses import StreamingResponse

from app.db.coloc_pairs_db import ColocPairsDBClient
from app.db.studies_db import StudiesDBClient
from app.models.schemas import (
    ColocGroup,
    ExtendedColocGroup,
    ExtendedRareResult,
    ExtendedStudyExtraction,
    RareResult,
    Variant,
    VariantResponse,
    convert_duckdb_to_pydantic_model,
    convert_duckdb_tuples_to_dicts,
)
from typing import List
from app.logging_config import get_logger, time_endpoint
from app.rate_limiting import limiter, DEFAULT_RATE_LIMIT
from app.services.associations_service import AssociationsService
from app.services.summary_stat_service import SummaryStatService

logger = get_logger(__name__)
router = APIRouter()


@router.get("", response_model=List[Variant])
@time_endpoint
@limiter.limit(DEFAULT_RATE_LIMIT)
async def get_variants(
    request: Request,
    snp_ids: List[int] = Query(None, description="List of snp_ids to filter results"),
    variants: List[str] = Query(None, description="List of variants to filter results"),
    rsids: List[str] = Query(None, description="List of rsids to filter results"),
    grange: str = Query(None, description="grange to filter results"),
) -> List[Variant]:
    try:
        if sum([bool(snp_ids), bool(rsids), bool(grange)]) > 1:
            raise HTTPException(
                status_code=400,
                detail="Only one of snp_ids, rsids, or grange can be provided.",
            )
        if sum([bool(snp_ids), bool(variants), bool(rsids), bool(grange)]) == 0:
            raise HTTPException(
                status_code=400,
                detail="One of snp_ids, variants, rsids, or grange must be provided.",
            )

        studies_db = StudiesDBClient()

        variants = studies_db.get_variants(snp_ids=snp_ids, variant_prefixes=variants, rsids=rsids, grange=grange)
        variants = convert_duckdb_to_pydantic_model(Variant, variants)

        return variants

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in get_variants: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{snp_id}", response_model=VariantResponse)
@time_endpoint
@limiter.limit(DEFAULT_RATE_LIMIT)
async def get_variant(
    request: Request,
    snp_id: int = Path(..., description="Variant ID to filter results"),
    include_coloc_pairs: bool = Query(False, description="Whether to include coloc pairs for SNPs"),
    h4_threshold: float = Query(0.8, description="H4 threshold for coloc pairs"),
) -> VariantResponse:
    try:
        studies_db = StudiesDBClient()
        coloc_pairs_db = ColocPairsDBClient()
        associations_service = AssociationsService()

        variant = studies_db.get_variant(snp_id)
        if variant is None:
            raise HTTPException(status_code=404, detail="Variant not found")
        colocs = studies_db.get_colocs_for_variants([snp_id])
        if colocs:
            colocs = convert_duckdb_to_pydantic_model(ColocGroup, colocs)

        rare_results = studies_db.get_rare_results_for_variants([snp_id])
        study_extractions_variant = studies_db.get_study_extractions_for_variant(snp_id)
        study_extractions_from_colocs = studies_db.get_study_extractions_by_id(
            [coloc.study_extraction_id for coloc in colocs]
        )
        study_extractions = study_extractions_variant + study_extractions_from_colocs

        if not colocs and not rare_results and not study_extractions:
            variant = convert_duckdb_to_pydantic_model(Variant, variant)
            return VariantResponse(
                variant=variant,
                coloc_groups=[],
                rare_results=[],
                study_extractions=[],
                coloc_pairs=[],
                associations=[],
            )

        rare_results = convert_duckdb_to_pydantic_model(RareResult, rare_results)
        variant = convert_duckdb_to_pydantic_model(Variant, variant)
        study_extractions = convert_duckdb_to_pydantic_model(ExtendedStudyExtraction, study_extractions)

        associations = associations_service.get_associations(colocs, rare_results)

        coloc_pairs = None
        if include_coloc_pairs:
            snp_ids = (
                [coloc.snp_id for coloc in colocs]
                + [rare_result.snp_id for rare_result in rare_results]
                + [study_extraction.snp_id for study_extraction in study_extractions]
            )
            coloc_pair_rows, coloc_pair_columns = coloc_pairs_db.get_coloc_pairs_by_snp_ids(
                snp_ids, h4_threshold=h4_threshold
            )
            coloc_pairs = convert_duckdb_tuples_to_dicts(coloc_pair_rows, coloc_pair_columns)

        extended_colocs = []
        for coloc in colocs:
            association = next((u for u in associations if u["study_id"] == coloc.study_id), None)
            if association is None:
                logger.warning(f"Association not found for variant {snp_id} and study {coloc.study_id}")
            extended_colocs.append(ExtendedColocGroup(**coloc.model_dump(), association=association))
        extended_rare_results = []
        for rare_result in rare_results:
            association = next((u for u in associations if u["study_id"] == rare_result.study_id), None)
            if association is None:
                logger.warning(f"Association not found for variant {snp_id} and study {rare_result.study_id}")
            extended_rare_results.append(ExtendedRareResult(**rare_result.model_dump(), association=association))

        return VariantResponse(
            variant=variant,
            coloc_groups=extended_colocs,
            rare_results=extended_rare_results,
            study_extractions=study_extractions,
            coloc_pairs=coloc_pairs,
            associations=associations,
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in get_variant: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{snp_id}/summary-stats")
@time_endpoint
@limiter.limit(DEFAULT_RATE_LIMIT)
async def get_variant_with_summary_stats(
    request: Request,
    snp_id: int = Path(..., description="Variant ID to filter results"),
):
    try:
        studies_db = StudiesDBClient()
        variant = studies_db.get_variant(snp_id)
        if variant is None:
            raise HTTPException(status_code=404, detail="Variant not found")
        colocs = studies_db.get_colocs_for_variants([snp_id])
        rare_results = studies_db.get_rare_results_for_variants([snp_id])
        study_extractions = studies_db.get_study_extractions_for_variant(snp_id)

        colocs = convert_duckdb_to_pydantic_model(ColocGroup, colocs)
        rare_results = convert_duckdb_to_pydantic_model(RareResult, rare_results)
        variant = convert_duckdb_to_pydantic_model(Variant, variant)
        study_extractions = convert_duckdb_to_pydantic_model(ExtendedStudyExtraction, study_extractions)

        all_study_extraction_ids = (
            [coloc.study_extraction_id for coloc in colocs]
            + [rare_result.study_extraction_id for rare_result in rare_results]
            + [study_extraction.id for study_extraction in study_extractions]
        )
        all_study_extractions = studies_db.get_study_extractions_by_id(all_study_extraction_ids)
        all_study_extractions = convert_duckdb_to_pydantic_model(ExtendedStudyExtraction, all_study_extractions)

        summary_stat_service = SummaryStatService()
        zip_buffer = summary_stat_service.get_study_summary_stats(all_study_extractions)

        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename=variant_{snp_id}_summary_stats.zip"},
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in get_variant: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))
