from cachetools import TTLCache
import redis
from typing import Optional, Any
import redis.asyncio as redis
from src.core.settings import Settings
from src.core.exceptions import VRPOptimizerError


class CacheManager:
    """Manages Redis caching operations."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.redis_client: Optional[redis.Redis] = None

    def _validate_redis_url(self, url: str):
        """Validate the Redis URL."""
        if not url:
            raise VRPOptimizerError("Redis URL is not set or is empty.")
    
    async def initialize(self):
        """Initialize Redis connection."""
        try:
            self.redis_client = redis.from_url(
                self._validate_redis_url(self.settings.REDIS_URL),
                encoding="utf-8",
                decode_responses=True
            )
            # Test connection
            await self.redis_client.ping()
        except Exception as e:
            raise VRPOptimizerError(f"Failed to initialize Redis connection: {str(e)}")

    async def get(self, key: str) -> Optional[str]:
        """Get value from cache."""
        if not self.redis_client:
            await self.initialize()
        return await self.redis_client.get(key)

    async def set(self, key: str, value: Any, expire: int = None):
        """Set value in cache with optional expiration."""
        if not self.redis_client:
            await self.initialize()
        await self.redis_client.set(key, value, ex=expire)

    async def delete(self, key: str):
        """Delete value from cache."""
        if not self.redis_client:
            await self.initialize()
        await self.redis_client.delete(key)

    async def close(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
