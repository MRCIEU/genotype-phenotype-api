import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.middleware.security import SecurityMiddleware
from app.api.v1.router import api_router
from app.config import get_settings
from app.db.duckdb import DuckDBClient
from app.db.redis import RedisClient

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
        LoggingCORSMiddleware,
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