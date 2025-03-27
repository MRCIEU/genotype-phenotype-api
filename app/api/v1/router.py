from fastapi import APIRouter
from app.api.v1.endpoints import ld, regions, studies, search, gwas, variants, genes

api_router = APIRouter()

api_router.include_router(
    studies.router,
    prefix="/studies",
    tags=["studies"]
)

api_router.include_router(
    search.router,
    prefix="/search",
    tags=["search"]
)

api_router.include_router(
    ld.router,
    prefix="/ld",
    tags=["ld"]
)

api_router.include_router(
    gwas.router,
    prefix="/gwases",
    tags=["gwas"]
)

api_router.include_router(
    regions.router,
    prefix="/regions",
    tags=["regions"]
)

api_router.include_router(
    variants.router,
    prefix="/variants",
    tags=["variants"]
)

api_router.include_router(
    genes.router,
    prefix="/genes",
    tags=["genes"]
)