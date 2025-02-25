from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.middleware.security import SecurityMiddleware
from app.api.v1.router import api_router
from app.config import get_settings
from app.db.duckdb import DuckDBClient
from app.db.redis import RedisClient

settings = get_settings()

def create_app() -> FastAPI:
    app = FastAPI(
        title="Genotype Phenotype API",
        description="API for accessing genotype-phenotype data",
        version="0.0.1",
        debug=settings.DEBUG
    )

    app.add_middleware(SecurityMiddleware)

    # TODO: Add more origins when we have a production environment
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include the v1 router with prefix
    app.include_router(api_router, prefix="/v1")

    @app.get("/health")
    async def health_check():
        redis_client = RedisClient()
        db_client = DuckDBClient()

        await redis_client.peek_queue(redis_client.process_gwas_queue)
        db_client.get_studies(1)

        return {"status": "healthy"}

    return app

app = create_app()