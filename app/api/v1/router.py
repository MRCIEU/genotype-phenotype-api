from fastapi import APIRouter
from app.api.v1.endpoints import (
    ld,
    regions,
    search,
    gwas,
    traits,
    variants,
    genes,
    info,
    internal,
    associations,
    pleiotropy,
)

api_router = APIRouter()

api_router.include_router(traits.router, prefix="/traits", tags=["traits"])

api_router.include_router(search.router, prefix="/search", tags=["search"])

api_router.include_router(ld.router, prefix="/ld", tags=["ld"])

api_router.include_router(associations.router, prefix="/associations", tags=["associations"])

api_router.include_router(gwas.router, prefix="/gwas", tags=["gwas"])

api_router.include_router(regions.router, prefix="/regions", tags=["regions"])

api_router.include_router(variants.router, prefix="/variants", tags=["variants"])

api_router.include_router(genes.router, prefix="/genes", tags=["genes"])

api_router.include_router(info.router, prefix="/info", tags=["info"])

api_router.include_router(internal.router, prefix="/internal", tags=["internal"])

api_router.include_router(pleiotropy.router, prefix="/pleiotropy", tags=["pleiotropy"])
