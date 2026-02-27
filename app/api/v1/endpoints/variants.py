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
    GetVariantsResponse,
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


@router.get("", response_model=GetVariantsResponse)
@time_endpoint
@limiter.limit(DEFAULT_RATE_LIMIT)
async def get_variants(
    request: Request,
    snp_ids: List[int] = Query(None, description="List of snp_ids to filter results"),
    variants: List[str] = Query(None, description="List of variants to filter results"),
    rsids: List[str] = Query(None, description="List of rsids to filter results"),
    grange: str = Query(None, description="grange to filter results"),
    expand: bool = Query(
        False, description="Return full VariantResponse for each variant (max 10, not available with grange)"
    ),
    include_associations: bool = Query(
        False, description="Whether to include associations for SNPs (only when expand=True)"
    ),
    include_coloc_pairs: bool = Query(
        False, description="Whether to include coloc pairs for SNPs (only when expand=True)"
    ),
    h4_threshold: float = Query(0.8, description="H4 threshold for coloc pairs"),
) -> GetVariantsResponse:
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
        if expand and grange:
            raise HTTPException(
                status_code=400,
                detail="expand is not available when using grange filter.",
            )

        studies_db = StudiesDBClient()
        variant_rows = studies_db.get_variants(snp_ids=snp_ids, variant_prefixes=variants, rsids=rsids, grange=grange)
        variant_rows = convert_duckdb_to_pydantic_model(Variant, variant_rows)

        if not variant_rows:
            return GetVariantsResponse(variants=[])

        if not isinstance(variant_rows, list):
            variant_rows = [variant_rows]

        if expand:
            maximum_num_variants_expanded = 10
            if len(variant_rows) > maximum_num_variants_expanded:
                raise HTTPException(
                    status_code=400,
                    detail=f"Can not request more than {maximum_num_variants_expanded} variants when expand=True.",
                )
            coloc_pairs_db = ColocPairsDBClient()
            associations_service = AssociationsService()

            snp_ids_to_expand = [v.id for v in variant_rows]
            colocs = studies_db.get_colocs_for_variants(snp_ids_to_expand)
            rare_results = studies_db.get_rare_results_for_variants(snp_ids_to_expand)
            study_extractions_direct = studies_db.get_study_extractions_for_variants(snp_ids_to_expand)

            colocs = convert_duckdb_to_pydantic_model(ColocGroup, colocs) if colocs else []
            rare_results = convert_duckdb_to_pydantic_model(RareResult, rare_results) if rare_results else []
            study_extractions_direct = (
                convert_duckdb_to_pydantic_model(ExtendedStudyExtraction, study_extractions_direct)
                if study_extractions_direct
                else []
            )

            study_extraction_ids_from_colocs = list({c.study_extraction_id for c in colocs})
            existing_ids = {e.id for e in study_extractions_direct}
            extra_ids = [eid for eid in study_extraction_ids_from_colocs if eid not in existing_ids]
            study_extractions = list(study_extractions_direct)
            if extra_ids:
                extra_data = studies_db.get_study_extractions_by_id(extra_ids)
                extra_extractions = convert_duckdb_to_pydantic_model(ExtendedStudyExtraction, extra_data)
                study_extractions = study_extractions + (
                    extra_extractions if isinstance(extra_extractions, list) else [extra_extractions]
                )

            colocs_by_snp = {}
            for c in colocs:
                if c.snp_id not in colocs_by_snp:
                    colocs_by_snp[c.snp_id] = []
                colocs_by_snp[c.snp_id].append(c)

            rare_by_snp = {}
            for r in rare_results:
                if r.snp_id not in rare_by_snp:
                    rare_by_snp[r.snp_id] = []
                rare_by_snp[r.snp_id].append(r)

            extractions_by_snp = {}
            extraction_by_id = {e.id: e for e in study_extractions}
            for e in study_extractions:
                if e.snp_id not in extractions_by_snp:
                    extractions_by_snp[e.snp_id] = []
                extractions_by_snp[e.snp_id].append(e)
            for c in colocs:
                ext = extraction_by_id.get(c.study_extraction_id)
                if ext:
                    if c.snp_id not in extractions_by_snp:
                        extractions_by_snp[c.snp_id] = []
                    if ext.id not in {e.id for e in extractions_by_snp[c.snp_id]}:
                        extractions_by_snp[c.snp_id].append(ext)

            variant_responses = []
            for v in variant_rows:
                v_colocs = colocs_by_snp.get(v.id, [])
                v_rare = rare_by_snp.get(v.id, [])
                v_extractions = extractions_by_snp.get(v.id, [])

                if not v_colocs and not v_rare and not v_extractions:
                    variant_responses.append(
                        VariantResponse(
                            variant=v,
                            coloc_groups=[],
                            rare_results=[],
                            study_extractions=[],
                            coloc_pairs=[],
                            associations=[],
                        )
                    )
                    continue

                associations = (
                    associations_service.get_associations(v_colocs, v_rare, v_extractions)
                    if include_associations
                    else []
                )

                coloc_pairs = None
                if include_coloc_pairs:
                    v_snp_ids = (
                        [c.snp_id for c in v_colocs] + [r.snp_id for r in v_rare] + [e.snp_id for e in v_extractions]
                    )
                    v_snp_ids = list(set(v_snp_ids))
                    if v_snp_ids:
                        pair_rows, pair_columns = coloc_pairs_db.get_coloc_pairs_by_snp_ids(
                            v_snp_ids, h4_threshold=h4_threshold
                        )
                        coloc_pairs = convert_duckdb_tuples_to_dicts(pair_rows, pair_columns)

                extended_colocs = [
                    ExtendedColocGroup(
                        **coloc.model_dump(),
                        association=next(
                            (u for u in associations if u["study_id"] == coloc.study_id),
                            None,
                        ),
                    )
                    for coloc in v_colocs
                ]
                extended_rare_results = [
                    ExtendedRareResult(
                        **rare_result.model_dump(),
                        association=next(
                            (u for u in associations if u["study_id"] == rare_result.study_id),
                            None,
                        ),
                    )
                    for rare_result in v_rare
                ]

                variant_responses.append(
                    VariantResponse(
                        variant=v,
                        coloc_groups=extended_colocs,
                        rare_results=extended_rare_results,
                        study_extractions=v_extractions,
                        coloc_pairs=coloc_pairs,
                        associations=associations if include_associations else None,
                    )
                )
            return GetVariantsResponse(variants=variant_responses)
        else:
            return GetVariantsResponse(variants=variant_rows)

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

        associations = associations_service.get_associations(colocs, rare_results, study_extractions)

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
