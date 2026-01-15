import traceback
import shutil
from fastapi import APIRouter, HTTPException, Request, Path
import json
import os

from app.config import get_settings
from app.db.gwas_db import GwasDBClient
from app.services.oci_service import OCIService
from app.models.schemas import convert_duckdb_to_pydantic_model, GwasUpload
from app.logging_config import get_logger, time_endpoint
from app.rate_limiting import limiter, DEFAULT_RATE_LIMIT
from app.services.studies_service import StudiesService
from app.services.associations_service import AssociationsService
from app.db.redis import RedisClient

logger = get_logger(__name__)
router = APIRouter()

settings = get_settings()

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


@router.post("/gwas-queue/rerun/{guid}", response_model=dict, include_in_schema=False)
@time_endpoint
async def rerun_gwas(request: Request, guid: str = Path(..., description="GUID of the GWAS upload to rerun")):
    """
    Rerun a GWAS upload by GUID.
    """
    try:
        gwas_db = GwasDBClient()
        redis_client = RedisClient()

        gwas = gwas_db.get_gwas_by_guid(guid)
        if gwas is None:
            raise HTTPException(status_code=404, detail="GWAS not found")

        gwas = convert_duckdb_to_pydantic_model(GwasUpload, gwas)
        redis_client.add_to_queue(redis_client.process_gwas_queue, json.loads(gwas.upload_metadata))

        return {"message": f"Successfully rerun GWAS upload with GUID {guid}"}
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in rerun_gwas: {e}\n{traceback.format_exc()}")
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


@router.post("/gwas-queue/add", response_model=dict, include_in_schema=False)
@time_endpoint
@limiter.limit(DEFAULT_RATE_LIMIT)
async def add_to_gwas_queue(request: Request, message: dict):
    """
    Add a JSON message to the process_gwas_queue.
    The message will be added to the queue for processing.
    """
    try:
        redis_client = RedisClient()
        success = redis_client.add_to_queue(redis_client.process_gwas_queue, message)

        if success:
            return {
                "message": "Successfully added message to process_gwas_queue",
                "queue_size": redis_client.get_queue_size(redis_client.process_gwas_queue),
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to add message to queue")
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in add_to_gwas_queue: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/gwas/{guid}", response_model=dict, include_in_schema=False)
@time_endpoint
@limiter.limit(DEFAULT_RATE_LIMIT)
async def delete_gwas(request: Request, guid: str = Path(..., description="GUID of the GWAS upload to delete")):
    """
    Delete a GWAS upload by GUID.
    Deletes associated files from OCI and entries from the database.
    """
    try:
        oci_service = OCIService()
        gwas_db = GwasDBClient()
        redis_client = RedisClient()

        if os.path.exists(f"{settings.GWAS_DIR}/{guid}/"):
            shutil.rmtree(f"{settings.GWAS_DIR}/{guid}/")

        oci_service.delete_prefix(f"gwas_upload/{guid}/")
        redis_client.add_delete_gwas_to_queue(guid)
        gwas_db.delete_gwas_upload(guid)

        return {"message": f"Successfully deleted GWAS upload with GUID {guid} and all associated data"}
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in delete_gwas: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))
