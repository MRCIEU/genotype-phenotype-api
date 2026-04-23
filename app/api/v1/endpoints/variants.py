import traceback
from fastapi import APIRouter, HTTPException, Path, Query, Request
from fastapi.responses import StreamingResponse

from app.services.coloc_pairs_service import ColocPairsService
from app.db.studies_db import StudiesDBClient
from app.db.ld_db import LdDBClient
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
)
from typing import List, Optional, Tuple
from app.logging_config import get_logger, time_endpoint
from app.rate_limiting import limiter, DEFAULT_RATE_LIMIT
from app.services.associations_service import AssociationsService
from app.services.studies_service import StudiesService
from app.services.summary_stat_service import SummaryStatService

logger = get_logger(__name__)
router = APIRouter()


@router.get("", response_model=GetVariantsResponse)
@time_endpoint
@limiter.limit(DEFAULT_RATE_LIMIT)
async def get_variants(
    request: Request,
    variants: List[str] = Query(
        None, description="List of variants (variant_ids, rsids, or variant strings - auto-detected)"
    ),
    grange: str = Query(None, description="Genomic range (e.g. chr:start-end)"),
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
        if not variants and not grange:
            raise HTTPException(
                status_code=400,
                detail="One of variants or grange must be provided.",
            )
        if expand and grange:
            raise HTTPException(
                status_code=400,
                detail="expand is not available when using grange filter.",
            )

        studies_db = StudiesDBClient()
        variant_ids, rsids, variant_prefixes, variant_strings = _classify_variants(variants or [])
        variant_rows = studies_db.get_variants(
            variant_ids=variant_ids if variant_ids else None,
            rsids=rsids if rsids else None,
            variant_prefixes=variant_prefixes if variant_prefixes else None,
            variant_strings=variant_strings if variant_strings else None,
            grange=grange,
        )
        variant_rows = convert_duckdb_to_pydantic_model(Variant, variant_rows)
        variant_rows = StudiesService.deduplicate_by_key(
            variant_rows if isinstance(variant_rows, list) else [variant_rows],
            lambda v: v.id,
        )

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
            coloc_pairs_service = ColocPairsService()
            associations_service = AssociationsService()
            studies_service = StudiesService()

            variant_ids_to_expand = [v.id for v in variant_rows]
            colocs = studies_db.get_colocs_for_variants(variant_ids_to_expand)
            rare_results = studies_db.get_rare_results_for_variants(variant_ids_to_expand)
            study_extractions_direct = studies_db.get_study_extractions_for_variants(variant_ids_to_expand)

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

            # Deduplicate coloc_groups, rare_results, study_extractions
            colocs_dedup = StudiesService.deduplicate_by_key(
                colocs,
                lambda c: (c.coloc_group_id, c.study_extraction_id, c.study_id),
            )
            rare_results_dedup = StudiesService.deduplicate_by_key(
                rare_results,
                lambda r: (r.rare_result_group_id, r.study_extraction_id),
            )
            study_extractions_dedup = StudiesService.deduplicate_by_key(study_extractions, lambda e: e.id)

            coloc_pairs = None
            if include_coloc_pairs:
                v_variant_ids = (
                    [c.variant_id for c in colocs_dedup]
                    + [r.variant_id for r in rare_results_dedup]
                    + [e.variant_id for e in study_extractions_dedup]
                )
                v_variant_ids = list(set(v_variant_ids))
                if v_variant_ids:
                    coloc_pairs = coloc_pairs_service.get_coloc_pairs_full(v_variant_ids, h4_threshold=h4_threshold)

            if include_coloc_pairs and coloc_pairs is not None:
                study_extractions_dedup = studies_service.merge_study_extractions_for_coloc_pairs(
                    study_extractions_dedup, coloc_pairs
                )

            associations = []
            if include_associations:
                associations_raw = associations_service.get_associations(
                    colocs_dedup, rare_results_dedup, study_extractions_dedup
                )
                associations = StudiesService.deduplicate_by_key(
                    associations_raw,
                    lambda a: (a.get("variant_id"), a.get("study_id")),
                )

            extended_colocs = [
                ExtendedColocGroup(
                    **coloc.model_dump(),
                    association=next((u for u in associations if u["study_id"] == coloc.study_id), None),
                )
                for coloc in colocs_dedup
            ]
            extended_rare_results = [
                ExtendedRareResult(
                    **rare_result.model_dump(),
                    association=next(
                        (u for u in associations if u["study_id"] == rare_result.study_id),
                        None,
                    ),
                )
                for rare_result in rare_results_dedup
            ]

            return GetVariantsResponse(
                variants=variant_rows,
                coloc_groups=extended_colocs,
                rare_results=extended_rare_results,
                study_extractions=study_extractions_dedup,
                coloc_pairs=coloc_pairs,
                associations=associations if include_associations else None,
            )
        else:
            return GetVariantsResponse(variants=variant_rows)

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in get_variants: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{variant_id}/summary-stats")
@time_endpoint
@limiter.limit(DEFAULT_RATE_LIMIT)
async def get_variant_with_summary_stats(
    request: Request,
    variant_id: int = Path(..., description="Variant ID (variant_id)"),
):
    try:
        studies_db = StudiesDBClient()
        variant = studies_db.get_variant(variant_id)
        if variant is None:
            raise HTTPException(status_code=404, detail="Variant not found")
        colocs = studies_db.get_colocs_for_variants([variant_id])
        rare_results = studies_db.get_rare_results_for_variants([variant_id])
        study_extractions = studies_db.get_study_extractions_for_variant(variant_id)

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
            headers={"Content-Disposition": f"attachment; filename=variant_{variant_id}_summary_stats.zip"},
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in get_variant_with_summary_stats: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{variant_id}", response_model=VariantResponse)
@time_endpoint
@limiter.limit(DEFAULT_RATE_LIMIT)
async def get_variant(
    request: Request,
    variant_id: str = Path(
        ..., description="Variant identifier (variant_id, rsid, chr:pos, or chr:pos_ref_alt - auto-detected)"
    ),
    include_coloc_pairs: bool = Query(True, description="Whether to include coloc pairs for SNPs"),
    h4_threshold: float = Query(0.8, description="H4 threshold for coloc pairs"),
    rsquared_threshold: float = Query(0.9, description="R² threshold for LD proxy fallback when no coloc/rare"),
) -> VariantResponse:
    try:
        variant_id, variant_row = _resolve_variant_id(variant_id)
        if variant_id is None or variant_row is None:
            raise HTTPException(status_code=404, detail="Variant not found")
        if rsquared_threshold < 0.8 or rsquared_threshold > 1:
            raise HTTPException(status_code=400, detail="R² threshold must be between 0.8 and 1")

        studies_db = StudiesDBClient()
        studies_service = StudiesService()
        coloc_pairs_service = ColocPairsService()
        associations_service = AssociationsService()

        variant = variant_row
        colocs = studies_db.get_colocs_for_variants([variant_id])
        if colocs:
            colocs = convert_duckdb_to_pydantic_model(ColocGroup, colocs)

        rare_results = studies_db.get_rare_results_for_variants([variant_id])
        study_extractions_variant = studies_db.get_study_extractions_for_variant(variant_id)
        study_extractions_from_colocs = studies_db.get_study_extractions_by_id(
            [coloc.study_extraction_id for coloc in colocs]
        )
        study_extractions = study_extractions_variant + study_extractions_from_colocs

        if not colocs and not rare_results:
            variant = convert_duckdb_to_pydantic_model(Variant, variant)
            ld_proxy_variants = []
            ld_db = LdDBClient()
            proxies = ld_db.get_ld_proxies(variant_ids=[variant_id], rsquared_threshold=rsquared_threshold)
            if proxies:
                proxy_variant_ids = []

                for p in proxies:
                    lead_variant_id, proxy_variant_id = p[0], p[1]
                    other = proxy_variant_id if lead_variant_id == variant_id else lead_variant_id
                    if other != variant_id:
                        proxy_variant_ids.append(other)
                proxy_variant_ids = list(set(proxy_variant_ids))

                if proxy_variant_ids:
                    proxy_colocs = studies_db.get_colocs_for_variants(variant_ids=proxy_variant_ids)
                    proxy_rare = studies_db.get_rare_results_for_variants(variant_ids=proxy_variant_ids)
                    proxy_colocs = convert_duckdb_to_pydantic_model(ColocGroup, proxy_colocs)
                    proxy_rare = convert_duckdb_to_pydantic_model(RareResult, proxy_rare)
                    proxy_variant_rows = studies_db.get_variants(variant_ids=proxy_variant_ids)
                    proxy_variants = convert_duckdb_to_pydantic_model(Variant, proxy_variant_rows)

                    if not isinstance(proxy_variants, list):
                        proxy_variants = [proxy_variants]

                    proxy_ids_with_results = set(c.variant_id for c in proxy_colocs) | set(
                        r.variant_id for r in proxy_rare
                    )
                    ld_proxy_variants = [pv for pv in proxy_variants if pv.id in proxy_ids_with_results]

            return VariantResponse(
                variant=variant,
                coloc_groups=[],
                rare_results=[],
                study_extractions=[],
                coloc_pairs=[],
                associations=[],
                ld_proxy_variants=ld_proxy_variants if ld_proxy_variants else None,
            )

        rare_results = convert_duckdb_to_pydantic_model(RareResult, rare_results)
        variant = convert_duckdb_to_pydantic_model(Variant, variant)
        study_extractions = convert_duckdb_to_pydantic_model(ExtendedStudyExtraction, study_extractions)

        coloc_pairs = None
        if include_coloc_pairs:
            variant_ids = (
                [coloc.variant_id for coloc in colocs]
                + [rare_result.variant_id for rare_result in rare_results]
                + [study_extraction.variant_id for study_extraction in study_extractions]
            )
            variant_ids = list(set(variant_ids))
            if variant_ids:
                coloc_pairs = coloc_pairs_service.get_coloc_pairs_full(variant_ids, h4_threshold=h4_threshold)

        if include_coloc_pairs and coloc_pairs is not None:
            study_extractions = studies_service.merge_study_extractions_for_coloc_pairs(study_extractions, coloc_pairs)

        associations = associations_service.get_associations(colocs, rare_results, study_extractions)

        extended_colocs = []
        for coloc in colocs:
            association = next((u for u in associations if u["study_id"] == coloc.study_id), None)
            if association is None:
                logger.warning(f"Association not found for variant {variant_id} and study {coloc.study_id}")
            extended_colocs.append(ExtendedColocGroup(**coloc.model_dump(), association=association))
        extended_rare_results = []
        for rare_result in rare_results:
            association = next((u for u in associations if u["study_id"] == rare_result.study_id), None)
            if association is None:
                logger.warning(f"Association not found for variant {variant_id} and study {rare_result.study_id}")
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


def _classify_variants(variants: List[str]) -> Tuple[List[int], List[str], List[str], List[str]]:
    """Classify variant strings into variant_ids, rsids, variant_prefixes, variant_strings."""
    variant_ids = []
    rsids = []
    variant_prefixes = []
    variant_strings = []

    for v in variants:
        if not v or not isinstance(v, str):
            continue
        s = v.strip()
        if not s:
            continue
        if s.lower().startswith("rs"):
            rsids.append(s)
        elif s.isdigit():
            variant_ids.append(int(s))
        elif "_" in s and ":" in s:
            variant_strings.append(s)
        elif ":" in s:
            variant_prefixes.append(s)

    return variant_ids, rsids, variant_prefixes, variant_strings


def _resolve_variant_id(variant_id: str) -> Tuple[Optional[int], Optional[dict]]:
    """
    Resolve a variant identifier (variant_id, rsid, chr:pos, or chr:pos_ref_alt) to (variant_id, variant_row).
    Returns (None, None) if not found.
    """
    if not variant_id or not isinstance(variant_id, str):
        return None, None
    s = variant_id.strip()
    if not s:
        return None, None

    studies_db = StudiesDBClient()
    variant_ids, rsids, variant_prefixes, variant_strings = _classify_variants([s])
    variant_rows = studies_db.get_variants(
        variant_ids=variant_ids if variant_ids else None,
        rsids=rsids if rsids else None,
        variant_prefixes=variant_prefixes if variant_prefixes else None,
        variant_strings=variant_strings if variant_strings else None,
    )
    if not variant_rows:
        return None, None
    row = variant_rows[0]
    vid = row[0] if isinstance(row, (tuple, list)) else row.get("id") if isinstance(row, dict) else None
    return (vid, row) if vid is not None else (None, None)
