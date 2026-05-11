import json
import hashlib
from typing import Any, Optional
import redis.asyncio as redis
from src.core.config import settings
from src.core.logger import logger

class CacheService:
    """Handles Redis-based caching to improve performance and reduce LLM costs."""
    
    def __init__(self):
        self.redis_client = None
        if settings.REDIS_URL:
            try:
                self.redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
                logger.info("Redis cache initialized.")
            except Exception as e:
                logger.warning(f"Failed to initialize Redis: {e}. Falling back to No-Cache.")

    def _generate_key(self, prefix: str, **kwargs) -> str:
        """Generates a deterministic hash key."""
        sorted_items = sorted(kwargs.items())
        key_str = json.dumps(sorted_items)
        hashed = hashlib.md5(key_str.encode()).hexdigest()
        return f"{prefix}:{hashed}"

    async def get_cached_query(self, question: str) -> Optional[str]:
        if not self.redis_client: return None
        key = self._generate_key("sql_query", question=question)
        try:
            return await self.redis_client.get(key)
        except Exception as e:
            logger.warning(f"Cache GET error: {e}")
            return None

    async def set_cached_query(self, question: str, sql: str) -> None:
        if not self.redis_client: return
        key = self._generate_key("sql_query", question=question)
        try:
            await self.redis_client.setex(key, settings.CACHE_TTL_SECONDS, sql)
        except Exception as e:
            logger.warning(f"Cache SET error: {e}")

    async def get_schema_summary(self) -> Optional[str]:
        if not self.redis_client: return None
        try:
            return await self.redis_client.get("schema_summary")
        except Exception:
            return None

    async def set_schema_summary(self, summary: str) -> None:
        if not self.redis_client: return
        try:
            await self.redis_client.setex("schema_summary", 86400, summary) # Cache schema for 24 hours
        except Exception:
            pass

cache_service = CacheService()
