from fastapi import APIRouter, HTTPException, Path, Query, Request
import traceback
from typing import List

from app.db.coloc_pairs_db import ColocPairsDBClient
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
    convert_duckdb_tuples_to_dicts,
)
from app.rate_limiting import limiter, DEFAULT_RATE_LIMIT
from app.services.studies_service import StudiesService
from app.logging_config import get_logger, time_endpoint
from app.services.associations_service import AssociationsService

logger = get_logger(__name__)
router = APIRouter()


@router.get("", response_model=GetGenesResponse)
@time_endpoint
@limiter.limit(DEFAULT_RATE_LIMIT)
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

        maximum_num_genes = 5
        if len(ids) > maximum_num_genes:
            raise HTTPException(
                status_code=400,
                detail=f"Can not request more than {maximum_num_genes} in one request",
            )

        studies_db = StudiesDBClient()
        coloc_pairs_db = ColocPairsDBClient()
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
            region_for_gene = [
                e for e in region_extractions
                if e.chr == g.chr and g.start <= e.bp <= g.stop
            ]
            gene_for_gene = [
                e for e in gene_extractions
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

        region_colocs = (
            convert_duckdb_to_pydantic_model(ColocGroup, region_colocs_data)
            if region_colocs_data
            else []
        )
        gene_colocs = (
            convert_duckdb_to_pydantic_model(ColocGroup, gene_colocs_data)
            if gene_colocs_data
            else []
        )
        study_rare = (
            convert_duckdb_to_pydantic_model(RareResult, study_rare_data)
            if study_rare_data
            else []
        )
        gene_rare = (
            convert_duckdb_to_pydantic_model(RareResult, gene_rare_data)
            if gene_rare_data
            else []
        )

        # Build coloc_groups and rare_results per gene
        coloc_groups_by_gene = {}
        for g in genes:
            ext_ids = {e.id for e in study_extractions_by_gene[g.id]}
            from_region = [c for c in region_colocs if c.study_extraction_id in ext_ids]
            from_gene = [
                c for c in gene_colocs
                if (c.gene_id == g.id if c.gene_id else False)
                or (getattr(c, "situated_gene_id", None) == g.id)
            ]
            seen_cg = {}
            combined_colocs = []
            for c in from_region + from_gene:
                if c.coloc_group_id not in seen_cg:
                    seen_cg[c.coloc_group_id] = True
                    combined_colocs.append(c)
            coloc_groups_by_gene[g.id] = combined_colocs

        rare_by_extraction = {}
        for r in study_rare:
            if r.study_extraction_id not in rare_by_extraction:
                rare_by_extraction[r.study_extraction_id] = []
            rare_by_extraction[r.study_extraction_id].append(r)

        rare_results_by_gene = {}
        for g in genes:
            ext_ids = {e.id for e in study_extractions_by_gene[g.id]}
            from_study = []
            for eid in ext_ids:
                from_study.extend(rare_by_extraction.get(eid, []))
            from_gene = [r for r in gene_rare if (r.gene_id == g.id if r.gene_id else False) or (r.situated_gene_id == g.id if r.situated_gene_id else False)]
            seen_rr = {}
            combined_rare = []
            for r in from_study + from_gene:
                key = (r.rare_result_group_id, r.study_extraction_id)
                if key not in seen_rr:
                    seen_rr[key] = True
                    combined_rare.append(r)
            rare_results_by_gene[g.id] = combined_rare

        tissues = studies_service.get_tissues()

        # Build variants and associations per gene
        gene_responses = []
        for g in genes:
            study_extractions = study_extractions_by_gene[g.id]
            coloc_groups = coloc_groups_by_gene[g.id]
            rare_results = rare_results_by_gene[g.id]

            associations = None
            if include_associations:
                associations = associations_service.get_associations(
                    coloc_groups, rare_results, study_extractions
                )

            coloc_pairs = None
            if include_coloc_pairs:
                snp_ids = (
                    [c.snp_id for c in coloc_groups]
                    + [r.snp_id for r in rare_results]
                    + [e.snp_id for e in study_extractions]
                )
                snp_ids = list(set(snp_ids))
                if snp_ids:
                    pair_rows, pair_columns = coloc_pairs_db.get_coloc_pairs_by_snp_ids(
                        snp_ids, h4_threshold=h4_threshold
                    )
                    coloc_pairs = convert_duckdb_tuples_to_dicts(pair_rows, pair_columns)

            variants = None
            if rare_results or coloc_groups or study_extractions:
                snp_ids = (
                    [c.snp_id for c in coloc_groups]
                    + [r.snp_id for r in rare_results]
                    + [e.snp_id for e in study_extractions]
                )
                snp_ids = list(set(snp_ids))
                if snp_ids:
                    variants_data = studies_db.get_variants(snp_ids=snp_ids)
                    variants = convert_duckdb_to_pydantic_model(Variant, variants_data)
                else:
                    variants = []
            else:
                variants = []

            gene_responses.append(
                GeneResponse(
                    gene=g,
                    coloc_groups=coloc_groups,
                    coloc_pairs=coloc_pairs,
                    rare_results=rare_results,
                    variants=variants,
                    study_extractions=study_extractions,
                    tissues=tissues,
                    associations=associations,
                )
            )

        return GetGenesResponse(genes=gene_responses)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in get_genes: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{gene_identifier}", response_model=GeneResponse)
@time_endpoint
@limiter.limit(DEFAULT_RATE_LIMIT)
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
        coloc_pairs_db = ColocPairsDBClient()
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
            snp_ids = (
                [coloc.snp_id for coloc in coloc_groups]
                + [rare_result.snp_id for rare_result in rare_results]
                + [study_extraction.snp_id for study_extraction in study_extractions]
            )
            coloc_pair_rows, coloc_pair_columns = coloc_pairs_db.get_coloc_pairs_by_snp_ids(
                snp_ids, h4_threshold=h4_threshold
            )
            coloc_pairs = convert_duckdb_tuples_to_dicts(coloc_pair_rows, coloc_pair_columns)

        variants = None
        if rare_results or coloc_groups or study_extractions:
            snp_ids = (
                [coloc.snp_id for coloc in (coloc_groups or [])]
                + [rare_result.snp_id for rare_result in (rare_results or [])]
                + [study_extraction.snp_id for study_extraction in (study_extractions or [])]
            )
            variants = studies_db.get_variants(snp_ids=snp_ids)
            variants = convert_duckdb_to_pydantic_model(Variant, variants)

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
