from fastapi import APIRouter, HTTPException, Path
from app.db.studies_db import StudiesDBClient
from app.models.schemas import * 
from typing import List

from app.logging_config import get_logger
from app.services.cache_service import DBCacheService

logger = get_logger(__name__)
router = APIRouter()

@router.get("/{ld_block_id}", response_model=RegionResponse)
async def get_region(ld_block_id: int = Path(..., description="LD Block ID")) -> RegionResponse:
    try:
        db = StudiesDBClient()
        cache_service = DBCacheService()

        ld_block = db.get_ld_block(ld_block_id)
        if ld_block is None:
            raise HTTPException(status_code=404, detail=f"LD Block {ld_block_id} not found")

        ld_block = convert_duckdb_to_pydantic_model(LdBlock, ld_block)
        genes = cache_service.get_gene_ranges()

        colocs = db.get_all_colocs_for_ld_block(ld_block_id)
        region = Region(chr=ld_block.chr, start=ld_block.start, end=ld_block.stop, ancestry=ld_block.ancestry)
        colocs = convert_duckdb_to_pydantic_model(Coloc, colocs)
        genes = convert_duckdb_to_pydantic_model(GeneMetadata, genes)

        filtered_genes = [gene for gene in genes
                          if gene.chr == ld_block.chr and 
                          gene.min_bp >= ld_block.start - 1000000 and 
                          gene.max_bp <= ld_block.stop + 1000000
                          ]

        return RegionResponse(region=region, colocs=colocs, genes=filtered_genes)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in get_region: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{ancestry}/{chr}/{start}/{stop}", response_model=RegionResponse)
async def get_region(ancestry: str = Path(..., description="Ancestry"),
                     chr: int = Path(..., description="Chromosome"),
                     start: int = Path(..., description="Start BP of region"),
                     stop: int = Path(..., description="End BP of region")) -> RegionResponse:
    try:
        ld_block = f"{ancestry}/{chr}/{start}-{stop}"
        db = StudiesDBClient()
        cache_service = DBCacheService()

        colocs = db.get_all_colocs_for_ld_block(ld_block)
        if colocs is None:
            raise HTTPException(status_code=404, detail=f"No colocs found for region {ld_block}")
        genes = cache_service.get_gene_ranges()

        region = Region(chr=chr, start=start, stop=stop, ancestry=ancestry)
        colocs = convert_duckdb_to_pydantic_model(Coloc, colocs)
        genes = convert_duckdb_to_pydantic_model(GeneMetadata, genes)
        filtered_genes = [gene for gene in genes if gene.chr == chr and gene.min_bp >= start - 1000000 and gene.max_bp <= stop + 1000000]

        return RegionResponse(region=region, colocs=colocs, genes=filtered_genes)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in get_region: {e}")
        raise HTTPException(status_code=500, detail=str(e))