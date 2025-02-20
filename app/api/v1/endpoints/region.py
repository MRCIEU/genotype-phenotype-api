from fastapi import APIRouter, HTTPException, Path
from app.db.duckdb import DuckDBClient
from app.models.schemas import * 
from typing import List

from app.services.cache_service import CacheService

router = APIRouter()

# @router.get("/", response_model=List[RegionResponse])
# async def get_regions() -> List[RegionResponse]:
#     try:
#         db = DuckDBClient()
#         regions = db.get_regions()
#         regions = convert_duckdb_to_pydantic_model(RegionResponse, regions)
#         return regions
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


@router.get("/{ancestry}/{chr}/{start}/{end}", response_model=RegionResponse)
async def get_region(ancestry: str = Path(..., description="Ancestry"),
                     chr: int = Path(..., description="Chromosome"),
                     start: int = Path(..., description="Start BP of region"),
                     end: int = Path(..., description="End BP of region")) -> RegionResponse:
    try:
        region_name = f"{ancestry} {chr}:{start}-{end}"
        db = DuckDBClient()
        cache_service = CacheService()

        colocs = db.get_all_colocs_for_region(region_name)
        genes = cache_service.get_gene_ranges()

        region = Region(chr=chr, start=start, end=end, name=region_name)
        colocs = convert_duckdb_to_pydantic_model(Coloc, colocs)
        genes = convert_duckdb_to_pydantic_model(GeneMetadata, genes)
        filtered_genes = [gene for gene in genes if gene.chr == chr and gene.min_bp >= start and gene.max_bp <= end]

        return RegionResponse(region=region, colocs=colocs, genes=filtered_genes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))