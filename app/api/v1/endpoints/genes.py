from fastapi import APIRouter, HTTPException, Path, Query, Request
import traceback
from typing import List

from app.services.coloc_pairs_service import ColocPairsService
from app.db.studies_db import StudiesDBClient
from app.models.schemas import (
    Gene,
    ExtendedStudyExtraction,
    ColocGroup,
    GetGenesResponse,
    RareResult,
    Variant,
    GeneResponse,
    convert_duckdb_to_pydantic_model,
)
from app.rate_limiting import ENTITY_RESOURCE_RATE_LIMIT, limiter
from app.services.studies_service import StudiesService
from app.logging_config import get_logger, time_endpoint
from app.services.associations_service import AssociationsService

logger = get_logger(__name__)
router = APIRouter()


@router.get("", response_model=GetGenesResponse)
@time_endpoint
@limiter.shared_limit(ENTITY_RESOURCE_RATE_LIMIT, scope="entity_resource_reads")
async def get_genes(
    request: Request,
    ids: List[str] = Query(None, description="List of gene IDs or symbols to filter results"),
    include_trans: bool = Query(False, description="Whether to include trans-coloc results"),
    include_associations: bool = Query(False, description="Whether to include associations for SNPs"),
    include_coloc_pairs: bool = Query(False, description="Whether to include coloc pairs for SNPs"),
    h4_threshold: float = Query(0.8, description="H4 threshold for coloc pairs"),
) -> GetGenesResponse:
    try:
        studies_service = StudiesService()
        if not ids:
            genes = studies_service.get_genes()
            return genes

        maximum_num_genes = 10
        if len(ids) > maximum_num_genes:
            raise HTTPException(
                status_code=400,
                detail=f"Can not request more than {maximum_num_genes} in one request",
            )

        studies_db = StudiesDBClient()
        coloc_pairs_service = ColocPairsService()
        associations_service = AssociationsService()

        gene_data = studies_db.get_genes_by_ids(ids)
        if not gene_data:
            return GetGenesResponse(genes=[])

        genes = convert_duckdb_to_pydantic_model(Gene, gene_data)
        if not isinstance(genes, list):
            genes = [genes]

        gene_map = {g.id: g for g in genes}
        gene_ids_numeric = list(gene_map.keys())

        regions = [(g.chr, g.start, g.stop) for g in genes]
        region_extractions_data = studies_db.get_study_extractions_in_gene_regions(regions)
        gene_extractions_data = studies_db.get_study_extractions_for_genes(gene_ids_numeric, include_trans)

        region_extractions = (
            convert_duckdb_to_pydantic_model(ExtendedStudyExtraction, region_extractions_data)
            if region_extractions_data
            else []
        )
        gene_extractions = (
            convert_duckdb_to_pydantic_model(ExtendedStudyExtraction, gene_extractions_data)
            if gene_extractions_data
            else []
        )

        study_extractions_by_gene = {}
        for g in genes:
            region_for_gene = [e for e in region_extractions if e.chr == g.chr and g.start <= e.bp <= g.stop]
            gene_for_gene = [
                e
                for e in gene_extractions
                if (e.gene_id == g.id if e.gene_id else False)
                or (e.situated_gene_id == g.id if e.situated_gene_id else False)
            ]
            seen = {}
            combined = []
            for e in region_for_gene + gene_for_gene:
                if e.id not in seen:
                    seen[e.id] = True
                    combined.append(e)
            study_extractions_by_gene[g.id] = combined

        all_study_extraction_ids = []
        for ext_list in study_extractions_by_gene.values():
            all_study_extraction_ids.extend(e.id for e in ext_list)
        all_study_extraction_ids = list(set(all_study_extraction_ids))

        region_colocs_data = studies_db.get_all_colocs_for_study_extraction_ids(all_study_extraction_ids)
        gene_colocs_data = studies_db.get_all_colocs_for_genes(gene_ids_numeric, include_trans)
        study_rare_data = studies_db.get_rare_results_for_study_extraction_ids(all_study_extraction_ids)
        gene_rare_data = studies_db.get_rare_results_for_genes(gene_ids_numeric, include_trans)

        region_colocs = convert_duckdb_to_pydantic_model(ColocGroup, region_colocs_data) if region_colocs_data else []
        gene_colocs = convert_duckdb_to_pydantic_model(ColocGroup, gene_colocs_data) if gene_colocs_data else []
        study_rare = convert_duckdb_to_pydantic_model(RareResult, study_rare_data) if study_rare_data else []
        gene_rare = convert_duckdb_to_pydantic_model(RareResult, gene_rare_data) if gene_rare_data else []

        # Combine all coloc_groups, rare_results, study_extractions (deduplicated)
        all_coloc_groups = StudiesService.deduplicate_by_key(
            region_colocs + gene_colocs,
            lambda c: (c.coloc_group_id, c.study_extraction_id, c.study_id),
        )
        all_rare_results = StudiesService.deduplicate_by_key(
            study_rare + gene_rare,
            lambda r: (r.rare_result_group_id, r.study_extraction_id),
        )
        all_study_extractions = []
        for ext_list in study_extractions_by_gene.values():
            all_study_extractions.extend(ext_list)
        all_study_extractions = StudiesService.deduplicate_by_key(all_study_extractions, lambda e: e.id)

        tissues = studies_service.get_tissues()

        associations = None
        if include_associations:
            associations_raw = associations_service.get_associations(
                all_coloc_groups, all_rare_results, all_study_extractions
            )
            associations = StudiesService.deduplicate_by_key(
                associations_raw,
                lambda a: (a.get("variant_id"), a.get("study_id")),
            )

        coloc_pairs = None
        if include_coloc_pairs:
            variant_ids = (
                [c.variant_id for c in all_coloc_groups]
                + [r.variant_id for r in all_rare_results]
                + [e.variant_id for e in all_study_extractions]
            )
            variant_ids = list(set(variant_ids))
            if variant_ids:
                coloc_pairs = coloc_pairs_service.get_coloc_pairs_full(variant_ids, h4_threshold=h4_threshold)

        if include_coloc_pairs and coloc_pairs is not None:
            all_study_extractions = studies_service.merge_study_extractions_for_coloc_pairs(
                all_study_extractions, coloc_pairs
            )

        variants = []
        if all_coloc_groups or all_rare_results or all_study_extractions:
            variant_ids = (
                [c.variant_id for c in all_coloc_groups]
                + [r.variant_id for r in all_rare_results]
                + [e.variant_id for e in all_study_extractions]
            )
            variant_ids = list(set(variant_ids))
            if variant_ids:
                variants_data = studies_db.get_variants(variant_ids=variant_ids)
                variants = convert_duckdb_to_pydantic_model(Variant, variants_data)
                if not isinstance(variants, list):
                    variants = [variants]

        return GetGenesResponse(
            genes=genes,
            coloc_groups=all_coloc_groups,
            coloc_pairs=coloc_pairs,
            rare_results=all_rare_results,
            variants=variants,
            study_extractions=all_study_extractions,
            tissues=tissues,
            associations=associations,
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in get_genes: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{gene_identifier}", response_model=GeneResponse)
@time_endpoint
@limiter.shared_limit(ENTITY_RESOURCE_RATE_LIMIT, scope="entity_resource_reads")
async def get_gene(
    request: Request,
    gene_identifier: str = Path(..., description="Gene Symbol or ID"),
    include_trans: bool = Query(False, description="Whether to include trans-coloc results"),
    include_associations: bool = Query(False, description="Whether to include associations for SNPs"),
    include_coloc_pairs: bool = Query(False, description="Whether to include coloc pairs for SNPs"),
    h4_threshold: float = Query(0.8, description="H4 threshold for coloc pairs"),
) -> GeneResponse:
    try:
        studies_service = StudiesService()
        tissues = studies_service.get_tissues()
        studies_db = StudiesDBClient()
        coloc_pairs_service = ColocPairsService()
        associations_service = AssociationsService()

        gene_id = None
        try:
            gene_id = int(gene_identifier)
            gene = studies_db.get_gene(id=gene_id)
        except ValueError:
            gene = studies_db.get_gene(symbol=gene_identifier)

        if gene is None:
            raise HTTPException(status_code=404, detail=f"Gene {gene_identifier} not found")
        gene = convert_duckdb_to_pydantic_model(Gene, gene)

        genes = studies_db.get_genes()
        genes = convert_duckdb_to_pydantic_model(Gene, genes)

        genes_in_region = [
            g
            for g in genes
            if g.chr == gene.chr
            and g.start <= gene.start + 1000000
            and g.stop >= gene.stop - 1000000
            and (g.gene != gene_identifier or g.id != gene_id)
        ]
        gene.genes_in_region = genes_in_region

        study_extractions_in_region = (
            studies_db.get_study_extractions_in_gene_region(gene.chr, gene.start, gene.stop) or []
        )
        study_extractions_of_gene = studies_db.get_study_extractions_for_gene(gene.id, include_trans) or []
        study_extractions = study_extractions_in_region + study_extractions_of_gene

        if study_extractions:
            study_extractions = convert_duckdb_to_pydantic_model(ExtendedStudyExtraction, study_extractions)
            unique_study_extractions_dict = {}
            for s in study_extractions:
                unique_study_extractions_dict[s.id] = s
            study_extractions = list(unique_study_extractions_dict.values())
            study_extraction_ids = [s.id for s in study_extractions]
        else:
            study_extraction_ids = []

        region_colocs = studies_db.get_all_colocs_for_study_extraction_ids(study_extraction_ids)
        gene_colocs = studies_db.get_all_colocs_for_gene(gene.id, include_trans)
        coloc_groups = (region_colocs or []) + (gene_colocs or [])
        coloc_groups = list(set(coloc_groups)) if coloc_groups else []

        study_rare_results = studies_db.get_rare_results_for_study_extraction_ids(study_extraction_ids)

        gene_rare_results = studies_db.get_rare_results_for_gene(gene.id, include_trans)
        rare_results = list(set(study_rare_results + gene_rare_results))

        if rare_results is not None:
            rare_results = convert_duckdb_to_pydantic_model(RareResult, rare_results)
        if coloc_groups is not None:
            coloc_groups = convert_duckdb_to_pydantic_model(ColocGroup, coloc_groups)

        associations = None
        if include_associations:
            associations = associations_service.get_associations(coloc_groups, rare_results, study_extractions)

        coloc_pairs = None
        if include_coloc_pairs:
            variant_ids = (
                [coloc.variant_id for coloc in coloc_groups]
                + [rare_result.variant_id for rare_result in rare_results]
                + [study_extraction.variant_id for study_extraction in study_extractions]
            )
            variant_ids = list(set(variant_ids))
            if variant_ids:
                coloc_pairs = coloc_pairs_service.get_coloc_pairs_full(variant_ids, h4_threshold=h4_threshold)

        if include_coloc_pairs and coloc_pairs is not None and study_extractions is not None:
            study_extractions = studies_service.merge_study_extractions_for_coloc_pairs(
                list(study_extractions), coloc_pairs
            )

        variants: List[Variant] = []
        if rare_results or coloc_groups or study_extractions:
            variant_ids = (
                [coloc.variant_id for coloc in (coloc_groups or [])]
                + [rare_result.variant_id for rare_result in (rare_results or [])]
                + [study_extraction.variant_id for study_extraction in (study_extractions or [])]
            )
            variants = studies_db.get_variants(variant_ids=variant_ids)
            variants = convert_duckdb_to_pydantic_model(Variant, variants)
            if not isinstance(variants, list):
                variants = [variants]

        return GeneResponse(
            tissues=tissues,
            gene=gene,
            coloc_groups=coloc_groups,
            coloc_pairs=coloc_pairs,
            variants=variants,
            study_extractions=study_extractions,
            associations=associations,
            rare_results=rare_results,
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in get_gene: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))
