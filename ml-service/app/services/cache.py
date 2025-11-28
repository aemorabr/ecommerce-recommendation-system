import json
import logging
from typing import Any, Optional

import redis.asyncio as redis

logger = logging.getLogger(__name__)


class CacheService:
    def __init__(self, url: str = "redis://localhost:6379/0", ttl: int = 300):
        self.url = url
        self.ttl = ttl
        self.client: Optional[redis.Redis] = None

    async def connect(self):
        self.client = redis.from_url(self.url, decode_responses=True)
        try:
            await self.client.ping()
            logger.info("✓ Connected to Redis cache")
        except Exception as e:
            logger.error(f"Unable to connect to Redis at {self.url}: {e}")
            self.client = None
            raise

    async def close(self):
        if self.client:
            await self.client.close()
            self.client = None

    def _key_for_recommendations(self, customer_id: int, strategy: str, limit: int) -> str:
        return f"rec:{strategy}:{customer_id}:{limit}"

    async def get_recommendations(self, customer_id: int, strategy: str, limit: int) -> Optional[Any]:
        if not self.client:
            return None
        key = self._key_for_recommendations(customer_id, strategy, limit)
        try:
            payload = await self.client.get(key)
            if not payload:
                return None
            return json.loads(payload)
        except Exception:
            return None

    async def set_recommendations(self, customer_id: int, strategy: str, limit: int, value: Any):
        if not self.client:
            return
        key = self._key_for_recommendations(customer_id, strategy, limit)
        try:
            await self.client.set(key, json.dumps(value), ex=self.ttl)
        except Exception as e:
            logger.debug(f"Failed to set cache for {key}: {e}")

    async def invalidate_recommendations_for_customer(self, customer_id: int):
        if not self.client:
            return
        pattern = f"rec:*:{customer_id}:*"
        async for key in self.client.scan_iter(match=pattern):
            try:
                await self.client.delete(key)
            except Exception:
                pass

    async def invalidate_all_recommendations(self):
        if not self.client:
            return
        pattern = "rec:*"
        async for key in self.client.scan_iter(match=pattern):
            try:
                await self.client.delete(key)
            except Exception:
                pass
