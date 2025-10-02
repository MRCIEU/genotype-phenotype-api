from loguru import logger
from redis import Redis
from app.config import get_settings
import json
import datetime
from typing import Optional, Any
from datetime import UTC
from pydantic import BaseModel
from app.models.schemas import Singleton

settings = get_settings()



class RedisClient(metaclass=Singleton):
    def __init__(self):
        self.process_gwas_queue = "process_gwas"
        self.process_gwas_dlq = f"{self.process_gwas_queue}_dlq"
        self.accepted_queue_names = [self.process_gwas_queue, self.process_gwas_dlq]
        self.scheduled_jobs_key = "scheduled_jobs"
        self.redis = Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, decode_responses=True)
    
    def get_cached_data(self, key: str):
        data = self.redis.get(key)
        return json.loads(data) if data else None
    

    def set_cached_data(self, key: str, value: dict | str, expire: int = 0):
        if isinstance(value, dict):
            value = json.dumps(value)

        if expire == 0:
            self.redis.set(key, value)
        else:
            self.redis.set(key, value, ex=expire)

    def add_to_queue(self, queue_name: str, message: Any) -> bool:
        """
        Add a message to a queue.
        Returns True if successful, False otherwise.
        """
        if queue_name not in self.accepted_queue_names:
            raise ValueError(f"Queue name {queue_name} is not accepted")
        try:
            serialized_message = json.dumps(message)
            self.redis.lpush(queue_name, serialized_message)
            return True
        except Exception as e:
            logger.error(f"Error adding to queue: {e}")
            return False

    def get_from_queue(self, queue_name: str, timeout: int = 0) -> Optional[Any]:
        """
        Get and remove a message from a queue.
        If timeout is 0, returns immediately if queue is empty.
        If timeout is > 0, waits up to timeout seconds for a message.
        Returns None if no message is available.
        """
        if queue_name not in self.accepted_queue_names:
            raise ValueError(f"Queue name {queue_name} is not accepted")
        try:
            # BRPOP blocks until timeout, RPOP doesn't block
            if timeout > 0:
                result = self.redis.brpop(queue_name, timeout)
                if result:
                    _, message = result
                else:
                    return None
            else:
                message = self.redis.rpop(queue_name)
                if not message:
                    return None

            return json.loads(message)
        except Exception as e:
            logger.error(f"Error getting from queue: {e}")
            return None

    def get_queue_size(self, queue_name: str) -> int:
        """
        Get the current length of the queue.
        """
        if queue_name not in self.accepted_queue_names:
            raise ValueError(f"Queue name {queue_name} is not accepted")

        return self.redis.llen(queue_name)

    def peek_queue(self, queue_name: str, start: int = 0, end: int = -1) -> list:
        """
        Peek at messages in the queue without removing them.
        start and end are indices (inclusive).
        """
        if queue_name not in self.accepted_queue_names:
            raise ValueError(f"Queue name {queue_name} is not accepted")
        try:
            messages = self.redis.lrange(queue_name, start, end)
            return [json.loads(msg) for msg in messages]
        except Exception as e:
            logger.error(f"Error peeking queue: {e}")
            return []

    def move_to_dlq(self, queue_name: str, message: Any, error: str) -> bool:
        """
        Move a failed message to the dead letter queue with error information.
        Returns True if successful, False otherwise.
        """
        if queue_name not in self.accepted_queue_names:
            raise ValueError(f"Queue name {queue_name} is not accepted")

        dlq_name = f"{queue_name}_dlq"
        try:
            dlq_message = {
                "original_message": message,
                "error": str(error),
                "timestamp": datetime.datetime.now(UTC).isoformat(),
            }
            serialized_message = json.dumps(dlq_message)
            self.redis.lpush(dlq_name, serialized_message)
            return True
        except Exception as e:
            logger.error(f"Error moving message to DLQ: {e}")
            return False

    def retry_from_dlq(self, queue_name: str, count: int = 1) -> int:
        """
        Retry specified number of messages from the dead letter queue by moving them
        back to the original queue. Returns the number of messages successfully moved.
        """
        if queue_name not in self.accepted_queue_names:
            raise ValueError(f"Queue name {queue_name} is not accepted")

        dlq_name = f"{queue_name}_dlq"
        retried_count = 0

        try:
            for _ in range(count):
                message = self.redis.rpop(dlq_name)
                if not message:
                    break

                # Extract original message from DLQ entry
                dlq_entry = json.loads(message)
                original_message = dlq_entry["original_message"]

                # Push back to original queue
                if self.add_to_queue(queue_name, original_message):
                    retried_count += 1
                else:
                    # If failed to add to original queue, put it back in DLQ
                    self.redis.rpush(dlq_name, message)

            return retried_count
        except Exception as e:
            logger.error(f"Error retrying messages from DLQ: {e}")
            return retried_count

    def schedule_job(self, job_data: dict, run_at: datetime.datetime) -> bool:
        """
        Schedule a job to run at a specific time.
        job_data should be a dictionary containing the job details.
        run_at should be a datetime object specifying when the job should run.
        """
        try:
            job_entry = {
                "job_data": job_data,
                "created_at": datetime.datetime.now(UTC).isoformat(),
            }
            # Convert datetime to timestamp for score
            timestamp = run_at.timestamp()
            self.redis.zadd(self.scheduled_jobs_key, {json.dumps(job_entry): timestamp})
            return True
        except Exception as e:
            logger.error(f"Error scheduling job: {e}")
            return False

    def get_due_jobs(self) -> list:
        """
        Get all jobs that are due to run (scheduled time <= current time).
        Returns a list of job data dictionaries.
        """
        try:
            current_timestamp = datetime.datetime.now(UTC).timestamp()
            # Get all jobs with score <= current timestamp
            due_jobs = self.redis.zrangebyscore(self.scheduled_jobs_key, "-inf", current_timestamp)
            # Remove the jobs we're about to process
            if due_jobs:
                self.redis.zremrangebyscore(self.scheduled_jobs_key, "-inf", current_timestamp)

            return [json.loads(job)["job_data"] for job in due_jobs]
        except Exception as e:
            logger.error(f"Error getting due jobs: {e}")
            return []

    def get_scheduled_jobs(self, start: int = 0, end: int = -1) -> list:
        """
        Get all scheduled jobs within the specified range.
        Returns a list of tuples (job_data, scheduled_time).
        """
        try:
            jobs_with_scores = self.redis.zrange(self.scheduled_jobs_key, start, end, withscores=True)
            return [
                (
                    json.loads(job)["job_data"],
                    datetime.datetime.fromtimestamp(score, tz=UTC),
                )
                for job, score in jobs_with_scores
            ]
        except Exception as e:
            logger.error(f"Error getting scheduled jobs: {e}")
            return []

    def update_user_upload(self, email: str, max_daily_uploads: int = 100) -> tuple[bool, int]:
        """
        Track user upload attempts and check rate limiting.
        Returns (is_allowed: bool, recent_uploads: int)
        """
        try:
            email_key = f"email_uploads:{email}"
            current_time = datetime.datetime.now(UTC).isoformat()

            self.redis.zadd(email_key, {current_time: current_time})

            # Get count of uploads in last 24 hours
            yesterday = (datetime.datetime.now(UTC) - datetime.timedelta(days=1)).timestamp()
            recent_uploads = self.redis.zcount(email_key, yesterday, "+inf")

            return recent_uploads <= max_daily_uploads, recent_uploads
        except Exception as e:
            logger.error(f"Error tracking user upload: {e}")
            return True, 0  # Default to allowing upload if Redis fails
