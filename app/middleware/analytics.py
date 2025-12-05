import asyncio
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import httpx

from app.config import get_settings
from app.logging_config import get_logger
from app.rate_limiting import rate_limit_identifier

settings = get_settings()
logger = get_logger("app.middleware.analytics")


def get_client_id(request: Request) -> str:
    """
    Get client_id for GA4 tracking.
    First tries to use GA client_id from frontend (if provided in header),
    otherwise falls back to hashed headers (for R package and other clients).
    """
    # Try to get GA client_id from frontend (if provided in custom header)
    ga_client_id = request.headers.get("X-GA-Client-ID")
    if ga_client_id:
        return ga_client_id
    
    # Fall back to hashed headers for R package and other clients
    try:
        return rate_limit_identifier(request)
    except Exception as e:
        logger.warning(f"Failed to generate client_id: {e}")
        return "unknown"


def detect_client_source(request: Request) -> str:
    """
    Detect the source of the API request (R package, web, etc.)
    """
    user_agent = request.headers.get("user-agent", "").lower()
    
    if "r/" in user_agent or "rstudio" in user_agent or "rtools" in user_agent:
        return "r_package"
    elif "python" in user_agent or "requests" in user_agent:
        return "python_client"
    elif "curl" in user_agent:
        return "curl"
    elif "postman" in user_agent:
        return "postman"
    else:
        return "web_browser"


async def send_ga4_event(
    measurement_id: str,
    api_secret: str,
    client_id: str,
    event_name: str,
    event_params: dict,
):
    """
    Send an event to GA4 Measurement Protocol (async, non-blocking)
    """
    if not measurement_id or not api_secret:
        return  # Skip if GA4 not configured
    
    url = f"https://www.google-analytics.com/mp/collect?measurement_id={measurement_id}&api_secret={api_secret}"
    
    payload = {
        "client_id": client_id,
        "events": [
            {
                "name": event_name,
                "params": event_params,
            }
        ],
    }
    
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            await client.post(url, json=payload)
    except Exception as e:
        logger.debug(f"Failed to send GA4 event: {e}")


class AnalyticsMiddleware(BaseHTTPMiddleware):
    """
    Middleware to track API usage with Google Analytics 4
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip analytics for health checks and docs
        if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)
        
        # Skip if GA4 not configured
        if not settings.GA4_MEASUREMENT_ID or not settings.GA4_API_SECRET:
            return await call_next(request)
        
        # Start timing
        start_time = time.time()
        
        # Generate client_id
        client_id = get_client_id(request)
        
        # Detect client source
        client_source = detect_client_source(request)
        
        # Process request
        response = await call_next(request)
        
        # Calculate latency
        latency_ms = int((time.time() - start_time) * 1000)
        
        # Extract endpoint info
        endpoint = request.url.path
        method = request.method
        status_code = response.status_code
        
        # Extract path parameters (e.g., trait_id, variant_id)
        path_params = {}
        if request.path_params:
            # Only include specific IDs we care about
            for key in ["trait_id", "variant_id", "gene_id", "region_id", "snp_id"]:
                if key in request.path_params:
                    path_params[key] = str(request.path_params[key])
        
        # Prepare event parameters
        event_params = {
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
            "latency_ms": latency_ms,
            "client_source": client_source,
        }
        
        # Add path parameters if present
        if path_params:
            event_params.update(path_params)
        
        # Send GA4 event asynchronously (non-blocking)
        # Use asyncio.create_task to fire and forget
        asyncio.create_task(
            send_ga4_event(
                measurement_id=settings.GA4_MEASUREMENT_ID,
                api_secret=settings.GA4_API_SECRET,
                client_id=client_id,
                event_name="api_request",
                event_params=event_params,
            )
        )
        
        return response

