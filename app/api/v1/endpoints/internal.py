import traceback
from fastapi import APIRouter, HTTPException, Request, Path

from app.logging_config import get_logger, time_endpoint
from app.rate_limiting import limiter, DEFAULT_RATE_LIMIT
from app.services.studies_service import StudiesService
from app.services.associations_service import AssociationsService
from app.db.redis import RedisClient

logger = get_logger(__name__)
router = APIRouter()


@router.post("/clear-cache/all", response_model=dict, include_in_schema=False)
@time_endpoint
async def clear_cache(request: Request):
    try:
        studies_service = StudiesService()
        studies_service.clear_cache()
        associations_service = AssociationsService()
        associations_service.clear_cache()
        return {"message": "All caches cleared"}
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in clear_cache: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clear-cache/studies", response_model=dict, include_in_schema=False)
@time_endpoint
async def clear_cache_studies(request: Request):
    try:
        studies_service = StudiesService()
        studies_service.clear_cache()
        return {"message": "Studies cache cleared"}
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in clear_cache_studies: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rate-limiter", response_model=dict, include_in_schema=False)
@limiter.limit("3/minute")
async def rate_limiter(request: Request):
    """For testing rate limiting. Should block more than 2 calls per minute."""
    return {"success": True}


@router.post("/gwas-dlq/retry/{guid}", response_model=dict, include_in_schema=False)
@time_endpoint
async def retry_gwas_dlq_by_guid(
    request: Request, guid: str = Path(..., description="GUID of the GWAS upload to retry")
):
    """
    Reprocess a specific message from the GWAS dead letter queue by GUID.
    Moves the message back to the normal processing queue.
    """
    try:
        redis_client = RedisClient()
        success = redis_client.retry_guid_from_dlq(redis_client.process_gwas_queue, guid)

        if success:
            return {"message": f"Successfully moved message with GUID {guid} from DLQ to processing queue"}
        else:
            raise HTTPException(status_code=404, detail=f"Message with GUID {guid} not found in dead letter queue")
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in retry_gwas_dlq_by_guid: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/gwas-dlq/retry", response_model=dict, include_in_schema=False)
@time_endpoint
async def retry_all_gwas_dlq(request: Request):
    """
    Reprocess all messages from the GWAS dead letter queue.
    Moves all messages back to the normal processing queue.
    """
    try:
        redis_client = RedisClient()
        guids = redis_client.get_all_guids_from_dlq(redis_client.process_gwas_queue)
        count = 0
        for guid in guids:
            if redis_client.retry_guid_from_dlq(redis_client.process_gwas_queue, guid):
                count += 1

        return {"message": f"Successfully moved {count} message(s) from DLQ to processing queue", "count": count}
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in retry_all_gwas_dlq: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/gwas-dlq", response_model=dict, include_in_schema=False)
@time_endpoint
@limiter.limit(DEFAULT_RATE_LIMIT)
async def clear_gwas_dlq(request: Request):
    """
    Delete all messages from the GWAS dead letter queue.
    This permanently removes all failed messages from the DLQ.
    """
    try:
        redis_client = RedisClient()
        success = redis_client.clear_dlq(redis_client.process_gwas_queue)

        if success:
            return {"message": "Successfully cleared all messages from dead letter queue"}
        else:
            raise HTTPException(status_code=500, detail="Failed to clear dead letter queue")
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in clear_gwas_dlq: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))
