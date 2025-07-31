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
    ColocPair,
    GeneResponse,
    convert_duckdb_to_pydantic_model,
)
import traceback

from app.services.cache_service import DBCacheService
from app.logging_config import get_logger, time_endpoint

logger = get_logger(__name__)
router = APIRouter()


@router.get("", response_model=GetGenesResponse)
@time_endpoint
async def get_genes() -> GetGenesResponse:
    try:
        cache_service = DBCacheService()
        genes = cache_service.get_genes()
        return GetGenesResponse(genes=genes)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in get_genes: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{gene_identifier}", response_model=GeneResponse)
@time_endpoint
async def get_gene(
    gene_identifier: str = Path(..., description="Gene Symbol or ID"),
    include_coloc_pairs: bool = Query(False, description="Whether to include coloc pairs for SNPs"),
    h4_threshold: float = Query(0.8, description="H4 threshold for coloc pairs"),
) -> GeneResponse:
    try:
        cache_service = DBCacheService()
        tissues = cache_service.get_tissues()
        studies_db = StudiesDBClient()
        coloc_pairs_db = ColocPairsDBClient()

        gene_id = None
        try:
            gene_id = int(gene_identifier)
            gene = studies_db.get_gene(id=gene_id)
        except ValueError:
            gene = studies_db.get_gene(symbol=gene_identifier)

        if gene is None:
            raise HTTPException(status_code=404, detail=f"Gene {gene_identifier} not found")
        gene = convert_duckdb_to_pydantic_model(Gene, gene)

        genes = cache_service.get_genes()

        genes_in_region = [
            g
            for g in genes
            if g.chr == gene.chr
            and g.start <= gene.start + 1000000
            and g.stop >= gene.stop - 1000000
            and (g.gene != gene_identifier or g.id != gene_id)
        ]
        gene.genes_in_region = genes_in_region

        study_extractions = studies_db.get_study_extractions_in_gene_region(gene.chr, gene.start, gene.stop, gene.gene)
        if study_extractions is not None:
            study_extractions = convert_duckdb_to_pydantic_model(ExtendedStudyExtraction, study_extractions)
            study_extraction_ids = [s.id for s in study_extractions]

        region_colocs = studies_db.get_all_colocs_for_study_extraction_ids(study_extraction_ids)
        gene_colocs = studies_db.get_all_colocs_for_gene(gene.gene)
        coloc_groups = region_colocs + gene_colocs
        if coloc_groups is not None:
            coloc_groups = convert_duckdb_to_pydantic_model(ColocGroup, coloc_groups)
            study_extraction_ids = [coloc.study_extraction_id for coloc in coloc_groups]
            filtered_studies = [s for s in study_extractions if s.id not in study_extraction_ids]

            snp_ids = [coloc.snp_id for coloc in coloc_groups]
            variants = studies_db.get_variants(snp_ids=snp_ids)
            variants = convert_duckdb_to_pydantic_model(Variant, variants)
        else:
            variants = []
            filtered_studies = []

        study_rare_results = studies_db.get_rare_results_for_study_extraction_ids(study_extraction_ids)
        gene_rare_results = studies_db.get_rare_results_for_gene(gene.gene)
        rare_results = study_rare_results + gene_rare_results
        # TODO: Remove this once we have fixed the rare results in the pipeline
        rare_results = [r for r in rare_results if r[2] is not None]
        if rare_results is not None:
            rare_results = convert_duckdb_to_pydantic_model(RareResult, rare_results)

        coloc_pairs = None
        if include_coloc_pairs:
            study_extraction_ids = (
                [coloc.study_extraction_id for coloc in coloc_groups]
                + [rare_result.study_extraction_id for rare_result in rare_results]
                + [study_extraction.id for study_extraction in study_extractions]
            )
            coloc_pairs = coloc_pairs_db.get_coloc_pairs_for_study_extraction_matches(
                study_extraction_ids, h4_threshold=h4_threshold
            )
            coloc_pairs = convert_duckdb_to_pydantic_model(ColocPair, coloc_pairs)

        return GeneResponse(
            tissues=tissues,
            gene=gene,
            coloc_groups=coloc_groups,
            coloc_pairs=coloc_pairs,
            variants=variants,
            study_extractions=filtered_studies,
            rare_results=rare_results,
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in get_gene: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))
