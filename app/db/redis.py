from loguru import logger
from redis import Redis
from app.config import get_settings
import json
import datetime
from typing import Optional, Any
from datetime import UTC
from app.models.schemas import Singleton

settings = get_settings()


class RedisClient(metaclass=Singleton):
    def __init__(self):
        self.process_gwas_queue = "process_gwas"
        self.process_gwas_dlq = f"{self.process_gwas_queue}_dlq"
        self.delete_gwas_queue = "delete_gwas"
        self.accepted_queue_names = [self.process_gwas_queue, self.process_gwas_dlq, self.delete_gwas_queue]
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

    def get_all_guids_from_dlq(self, queue_name: str) -> list[str]:
        """
        Get all GUIDs from messages in the dead letter queue.
        Returns a list of GUIDs found in the DLQ.
        """
        if queue_name not in self.accepted_queue_names:
            raise ValueError(f"Queue name {queue_name} is not accepted")

        dlq_name = f"{queue_name}_dlq"
        guids = []

        try:
            messages = self.redis.lrange(dlq_name, 0, -1)
            for message in messages:
                try:
                    dlq_entry = json.loads(message)
                    original_message = dlq_entry.get("original_message", {})
                    guid = original_message.get("metadata", {}).get("guid")
                    if guid:
                        guids.append(guid)
                except (json.JSONDecodeError, KeyError, TypeError) as e:
                    logger.warning(f"Error parsing DLQ message to extract GUID: {e}")
                    continue
        except Exception as e:
            logger.error(f"Error getting GUIDs from DLQ: {e}")

        return guids

    def clear_dlq(self, queue_name: str) -> bool:
        """
        Clear all messages from the dead letter queue.
        Returns True if successful, False otherwise.
        """
        if queue_name not in self.accepted_queue_names:
            raise ValueError(f"Queue name {queue_name} is not accepted")

        dlq_name = f"{queue_name}_dlq"

        try:
            self.redis.delete(dlq_name)
            return True
        except Exception as e:
            logger.error(f"Error clearing DLQ: {e}")
            return False

    def _find_and_remove_from_dlq(self, queue_name: str, guid: str) -> Optional[dict]:
        """
        Find and remove a message from the dead letter queue by GUID.
        Returns the DLQ entry if found and removed, None otherwise.
        """
        dlq_name = f"{queue_name}_dlq"
        try:
            # Get all messages from the DLQ
            messages = self.redis.lrange(dlq_name, 0, -1)

            for message in messages:
                try:
                    dlq_entry = json.loads(message)
                    original_message = dlq_entry.get("original_message", {})

                    if original_message.get("metadata", {}).get("guid") == guid:
                        # Found the message with the matching GUID, now remove it
                        if self.redis.lrem(dlq_name, 1, message) > 0:
                            return dlq_entry
                except (json.JSONDecodeError, KeyError, TypeError):
                    continue
            return None
        except Exception as e:
            logger.error(f"Error finding and removing from DLQ: {e}")
            return None

    def remove_from_dlq(self, queue_name: str, guid: str) -> bool:
        """
        Remove a specific message from the dead letter queue by GUID.
        Returns True if the message was found and successfully removed, False otherwise.
        """
        if queue_name not in self.accepted_queue_names:
            raise ValueError(f"Queue name {queue_name} is not accepted")

        return self._find_and_remove_from_dlq(queue_name, guid) is not None

    def remove_from_queue(self, queue_name: str, guid: str) -> bool:
        """
        Remove a specific message from a queue by GUID.
        Returns True if the message was found and successfully removed, False otherwise.
        """
        if queue_name not in self.accepted_queue_names:
            raise ValueError(f"Queue name {queue_name} is not accepted")

        try:
            messages = self.redis.lrange(queue_name, 0, -1)
            for message in messages:
                try:
                    data = json.loads(message)
                    if data.get("metadata", {}).get("guid") == guid:
                        if self.redis.lrem(queue_name, 1, message) > 0:
                            return True
                except (json.JSONDecodeError, KeyError, TypeError):
                    continue
            return False
        except Exception as e:
            logger.error(f"Error removing from queue {queue_name}: {e}")
            return False

    def retry_guid_from_dlq(self, queue_name: str, guid: str) -> bool:
        """
        Find and retry a specific message from the dead letter queue by GUID.
        Returns True if the message was found and successfully moved, False otherwise.
        """
        if queue_name not in self.accepted_queue_names:
            raise ValueError(f"Queue name {queue_name} is not accepted")

        try:
            dlq_entry = self._find_and_remove_from_dlq(queue_name, guid)
            if dlq_entry:
                original_message = dlq_entry["original_message"]
                if self.add_to_queue(queue_name, original_message):
                    return True
                else:
                    # If failed to add back to the original queue, put it back in DLQ
                    self.move_to_dlq(queue_name, original_message, dlq_entry.get("error", "Unknown error"))
                    return False

            return False
        except Exception as e:
            logger.error(f"Error retrying GUID from DLQ: {e}")
            return False

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

    def get_queue_position(self, queue_name: str, guid: str) -> Optional[int]:
        """
        Find the position of a message with the given GUID in the queue.
        Returns 1-based position if found, None otherwise.
        """
        if queue_name not in self.accepted_queue_names:
            raise ValueError(f"Queue name {queue_name} is not accepted")

        try:
            messages = self.redis.lrange(queue_name, 0, -1)
            for i, message in enumerate(messages):
                try:
                    data = json.loads(message)
                    if data.get("metadata", {}).get("guid") == guid:
                        return i + 1
                except (json.JSONDecodeError, KeyError, TypeError):
                    continue
            return None
        except Exception as e:
            logger.error(f"Error getting queue position for {guid}: {e}")
            return None

    def get_processing_guids_for_user(self, email: str) -> list[str]:
        """
        Find all GUIDs currently in the processing queue for a specific user email.
        """
        processing_guids = []
        try:
            # We use the standard queue name
            queue_items = self.redis.lrange(self.process_gwas_queue, 0, -1)
            for item in queue_items:
                try:
                    data = item
                    if isinstance(item, bytes):
                        data = item.decode("utf-8")
                    data_json = json.loads(data)

                    if data_json.get("metadata", {}).get("email") == email:
                        guid = data_json["metadata"].get("guid")
                        if guid:
                            processing_guids.append(guid)
                except Exception:
                    continue
        except Exception as e:
            logger.error(f"Error checking processing queue for user {email}: {e}")

        return processing_guids

    def add_gwas_to_queue(self, file_location: str, metadata: dict) -> bool:
        """
        Add a GWAS processing request to the queue.
        """
        message = {
            "file_location": file_location,
            "metadata": metadata,
        }
        return self.add_to_queue(self.process_gwas_queue, message)

    def add_delete_gwas_to_queue(self, guid: str) -> bool:
        """
        Add a GWAS deletion request to the queue.
        """
        return self.add_to_queue(self.delete_gwas_queue, {"guid": guid})
