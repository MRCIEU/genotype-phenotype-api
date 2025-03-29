from duckdb import HTTPException
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.middleware.security import SecurityMiddleware
from app.api.v1.router import api_router
from app.config import get_settings
from app.db.duckdb import DuckDBClient
from app.db.redis import RedisClient
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from fastapi.responses import JSONResponse

settings = get_settings()

class LoggingCORSMiddleware(CORSMiddleware):
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":  # pragma: no cover
            return await super().__call__(scope, receive, send)
            
        # Extract headers from scope
        headers = dict(scope.get("headers", []))
        origin = headers.get(b"origin", b"").decode()
        print(f"CORS Check - Incoming request from origin: {origin}")
        print(f"CORS Check - Headers: {headers}")
        
        return await super().__call__(scope, receive, send)

def create_app() -> FastAPI:
    app = FastAPI(
        title="Genotype Phenotype API",
        description="API for accessing genotype-phenotype data",
        version="0.0.1",
        debug=settings.DEBUG
    )

    app.add_middleware(SecurityMiddleware)

    @app.options("/{rest_of_path:path}")
    async def preflight_handler(request: Request, rest_of_path: str):
        response = JSONResponse(content={})
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"
        return response

    app.add_middleware(
        LoggingCORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
        allow_origin_regex=None,
        max_age=3600,
    )

    @app.middleware("http")
    async def add_cors_headers(request: Request, call_next):
        if request.method == "OPTIONS":
            # Handle preflight requests
            response = JSONResponse(content={})
        else:
            response = await call_next(request)
            
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"
        return response

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