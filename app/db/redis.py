from redis import Redis
from app.config import get_settings
import json
from typing import Optional, Any

settings = get_settings()

class RedisClient:
    def __init__(self):
        self.process_gwas_queue= "process_gwas_queue"
        self.accepted_queue_names = [self.process_gwas_queue]
        self.redis = Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            decode_responses=True
        )

    async def get_cached_data(self, key: str):
        data = await self.redis.get(key)
        return json.loads(data) if data else None

    async def set_cached_data(self, key: str, value: dict, expire: int = 3600):
        await self.redis.set(
            key,
            json.dumps(value),
            ex=expire
        )
    
    async def add_to_queue(self, queue_name: str, message: Any) -> bool:
        """
        Add a message to a queue.
        Returns True if successful, False otherwise.
        """
        if queue_name not in self.accepted_queue_names:
            raise ValueError(f"Queue name {queue_name} is not accepted")
        try:
            serialized_message = json.dumps(message)
            await self.redis.lpush(queue_name, serialized_message)
            return True
        except Exception as e:
            print(f"Error adding to queue: {e}")
            return False

    async def get_from_queue(self, queue_name: str, timeout: int = 0) -> Optional[Any]:
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
                result = await self.redis.brpop(queue_name, timeout)
                if result:
                    _, message = result
                else:
                    return None
            else:
                message = await self.redis.rpop(queue_name)
                if not message:
                    return None
            
            return json.loads(message)
        except Exception as e:
            print(f"Error getting from queue: {e}")
            return None

    async def get_queue_length(self, queue_name: str) -> int:
        """
        Get the current length of the queue.
        """
        if queue_name not in self.accepted_queue_names:
            raise ValueError(f"Queue name {queue_name} is not accepted")
        return await self.redis.llen(queue_name)

    async def peek_queue(self, queue_name: str, start: int = 0, end: int = -1) -> list:
        """
        Peek at messages in the queue without removing them.
        start and end are indices (inclusive).
        """
        if queue_name not in self.accepted_queue_names:
            raise ValueError(f"Queue name {queue_name} is not accepted")
        try:
            messages = await self.redis.lrange(queue_name, start, end)
            return [json.loads(msg) for msg in messages]
        except Exception as e:
            print(f"Error peeking queue: {e}")
            return [] 