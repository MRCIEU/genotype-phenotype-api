import traceback
from fastapi import APIRouter, HTTPException, Path
from app.db.studies_db import StudiesDBClient
from app.models.schemas import (
    LdBlock,
    RegionResponse,
    ColocGroup,
    RareResult,
    Variant,
    convert_duckdb_to_pydantic_model,
)
from app.logging_config import get_logger, time_endpoint
from app.services.studies_service import StudiesService

logger = get_logger(__name__)
router = APIRouter()


@router.get("/{ld_block_id}", response_model=RegionResponse)
@time_endpoint
async def get_region(
    ld_block_id: int = Path(..., description="LD Block ID"),
) -> RegionResponse:
    try:
        studies_service = StudiesService()
        tissues = studies_service.get_tissues()

        db = StudiesDBClient()
        ld_block = db.get_ld_block(ld_block_id)
        if ld_block is None:
            raise HTTPException(status_code=404, detail=f"LD Block {ld_block_id} not found")
        ld_block = convert_duckdb_to_pydantic_model(LdBlock, ld_block)

        genes = studies_service.get_genes()
        genes_in_region = [
            g for g in genes if g.chr == ld_block.chr and g.start >= ld_block.start and g.stop <= ld_block.stop
        ]

        coloc_snp_ids = rare_result_snp_ids = []
        region_colocs = db.get_all_colocs_for_ld_block(ld_block_id)
        if region_colocs:
            region_colocs = convert_duckdb_to_pydantic_model(ColocGroup, region_colocs)
            coloc_snp_ids = [coloc.snp_id for coloc in region_colocs]

        region_rare_results = db.get_rare_results_for_ld_block(ld_block_id)
        # TODO: Remove this once we have fixed the rare results in the pipeline
        region_rare_results = [r for r in region_rare_results if r[2] is not None]
        if region_rare_results:
            region_rare_results = convert_duckdb_to_pydantic_model(RareResult, region_rare_results)
            rare_result_snp_ids = [rare_result.snp_id for rare_result in region_rare_results]

        snp_ids = coloc_snp_ids + rare_result_snp_ids

        variants = []
        if snp_ids:
            variants = db.get_variants(snp_ids=snp_ids)
            variants = convert_duckdb_to_pydantic_model(Variant, variants)

        return RegionResponse(
            region=ld_block,
            genes_in_region=genes_in_region,
            tissues=tissues,
            coloc_groups=region_colocs,
            variants=variants,
            rare_results=region_rare_results,
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in get_region: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))
