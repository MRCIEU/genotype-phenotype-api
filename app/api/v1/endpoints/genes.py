from fastapi import APIRouter, HTTPException, Path, Query
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
import traceback

from app.rate_limiting import limiter, DEFAULT_RATE_LIMIT
from app.services.studies_service import StudiesService
from app.logging_config import get_logger, time_endpoint
from app.services.associations_service import AssociationsService
from app.models.schemas import CisTrans

logger = get_logger(__name__)
router = APIRouter()


@router.get("", response_model=GetGenesResponse)
@time_endpoint
@limiter.limit(DEFAULT_RATE_LIMIT)
async def get_genes() -> GetGenesResponse:
    try:
        studies_service = StudiesService()
        genes = studies_service.get_genes()
        return GetGenesResponse(genes=genes)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in get_genes: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{gene_identifier}", response_model=GeneResponse)
@time_endpoint
@limiter.limit(DEFAULT_RATE_LIMIT)
async def get_gene(
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

        genes = studies_service.get_genes()

        genes_in_region = [
            g
            for g in genes
            if g.chr == gene.chr
            and g.start <= gene.start + 1000000
            and g.stop >= gene.stop - 1000000
            and (g.gene != gene_identifier or g.id != gene_id)
        ]
        gene.genes_in_region = genes_in_region

        study_extractions_in_region = studies_db.get_study_extractions_in_gene_region(
            gene.chr, gene.start, gene.stop, gene.id
        )
        cis_trans = None if include_trans else CisTrans.cis
        study_extractions_of_gene = studies_db.get_study_extractions_for_gene(gene.id, cis_trans)
        study_extractions = study_extractions_in_region + study_extractions_of_gene

        if study_extractions is not None:
            study_extractions = convert_duckdb_to_pydantic_model(ExtendedStudyExtraction, study_extractions)
            study_extraction_ids = [s.id for s in study_extractions]

        region_colocs = studies_db.get_all_colocs_for_study_extraction_ids(study_extraction_ids)
        gene_colocs = studies_db.get_all_colocs_for_gene(gene.id)
        coloc_groups = (region_colocs or []) + (gene_colocs or [])
        coloc_groups = list(set(coloc_groups)) if coloc_groups else []

        study_rare_results = studies_db.get_rare_results_for_study_extraction_ids(study_extraction_ids)

        gene_rare_results = studies_db.get_rare_results_for_gene(gene.id)
        rare_results = list(set(study_rare_results + gene_rare_results))

        if rare_results is not None:
            rare_results = convert_duckdb_to_pydantic_model(RareResult, rare_results)
        if coloc_groups is not None:
            coloc_groups = convert_duckdb_to_pydantic_model(ColocGroup, coloc_groups)

        associations = None
        if include_associations:
            associations = associations_service.get_associations(coloc_groups, rare_results)

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
