import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.middleware.security import SecurityMiddleware
from app.api.v1.router import api_router
from app.config import get_settings
from app.db.studies_db import StudiesDBClient
from app.db.redis import RedisClient

settings = get_settings()

def create_app() -> FastAPI:
    if not settings.DEBUG:
        sentry_sdk.init(dsn=settings.SENTRY_DSN, send_default_pii=True)

    app = FastAPI(
        title="Genotype Phenotype API",
        description="API for accessing genotype-phenotype data",
        version="0.0.1",
        debug=settings.DEBUG
    )

    app.add_middleware(SecurityMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:80",
            "http://localhost",
            "http://localhost:5173",
            "http://127.0.0.1",
            "http://127.0.0.1:80",
            "http://127.0.0.1:5173",
            "http://gpmap.opengwas.io",
            "https://gpmap.opengwas.io/"
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"]
    )

    @app.get("/health")
    async def health_check(request: Request):
        print("Origin:", request.headers.get("origin"))
        print("All headers:", dict(request.headers))
        
        redis_client = RedisClient()
        db_client = StudiesDBClient()
        db_client.get_studies(1)

        peeked_queue = redis_client.peek_queue(redis_client.process_gwas_queue)
        dead_letter_queue = redis_client.peek_queue(redis_client.process_gwas_dlq)

        return {"status": "healthy", "queue_size": len(peeked_queue), "peeked_queue": peeked_queue, "dead_letter_queue": len(dead_letter_queue)}

    app.include_router(api_router, prefix="/v1")
    return app

app = create_app()