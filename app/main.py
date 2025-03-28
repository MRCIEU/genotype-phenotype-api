from duckdb import HTTPException
from fastapi import FastAPI, Request
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

    # Add logging for CORS
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        print("Incoming request from origin:", request.headers.get("origin"))
        print("Request headers:", dict(request.headers))
        response = await call_next(request)
        return response

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost",
            "http://localhost:80",
            "http://localhost:5173",
            "http://127.0.0.1",
            "http://127.0.0.1:80",
            "https://gpmap.opengwas.io",
            "http://gpmap.opengwas.io",
            "http://gpmap.opengwas.io/"
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health_check(request: Request):
        print("Origin:", request.headers.get("origin"))
        print("All headers:", dict(request.headers))
        
        redis_client = RedisClient()
        db_client = DuckDBClient()

        db_client.get_studies(1)

        # await redis_client.peek_queue(redis_client.process_gwas_queue)
        # dead_letter_queue = await redis_client.peek_queue(redis_client.process_gwas_dlq)
        # if not dead_letter_queue.empty():
        #     error_message = {
        #         "message": "Dead letter queue is not empty",
        #         "queue_size": len(dead_letter_queue)
        #     }
        # else:
        #     error_message = {}


        # if error_message:
            # raise HTTPException(status_code=500, detail=error_message)
        # else:
        return {"status": "healthy"}

    # Include the v1 router with prefix
    app.include_router(api_router, prefix="/v1")

    return app

app = create_app()