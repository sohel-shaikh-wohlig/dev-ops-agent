"""
Cache Service
Business-logic caching layer built on top of the global Redis connection.
Provides cache-aside pattern and pattern-based invalidation.
"""

import json
from typing import Any, Callable, Awaitable, Dict, List, Optional

import redis.asyncio as aioredis

from app.core.logging_config import logger
from app.core.redis import redis_manager


class CacheService:
    """
    High-level caching operations backed by Redis.

    Usage:
        cache = CacheService()
        await cache.set("my:key", {"foo": "bar"}, ttl=300)
        value = await cache.get("my:key")
    """

    @property
    def _client(self) -> aioredis.Redis:
        return redis_manager.client

    # ------------------------------------------------------------------
    # Basic get / set / delete
    # ------------------------------------------------------------------

    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve a JSON value from cache. Returns None on miss or error."""
        try:
            raw = await self._client.get(key)
        except aioredis.RedisError as exc:
            logger.error(f"Cache GET error | key={key}: {exc}")
            return None

        if raw is None:
            return None

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning(f"Corrupt cache entry | key={key}")
            return None

    async def set(
        self,
        key: str,
        value: Dict[str, Any],
        ttl: Optional[int] = None,
    ) -> bool:
        """Store a JSON value in cache. Returns True on success."""
        try:
            await self._client.set(key, json.dumps(value), ex=ttl)
            return True
        except aioredis.RedisError as exc:
            logger.error(f"Cache SET error | key={key}: {exc}")
            return False

    async def delete(self, key: str) -> bool:
        """Remove a key from cache. Returns True if it existed."""
        try:
            return bool(await self._client.delete(key))
        except aioredis.RedisError as exc:
            logger.error(f"Cache DEL error | key={key}: {exc}")
            return False

    # ------------------------------------------------------------------
    # Cache-aside pattern
    # ------------------------------------------------------------------

    async def get_or_set(
        self,
        key: str,
        factory: Callable[[], Awaitable[Dict[str, Any]]],
        ttl: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Cache-aside: return cached value if present, otherwise call
        *factory*, cache the result, and return it.
        """
        cached = await self.get(key)
        if cached is not None:
            return cached

        value = await factory()
        await self.set(key, value, ttl=ttl)
        return value

    # ------------------------------------------------------------------
    # Pattern-based invalidation
    # ------------------------------------------------------------------

    async def invalidate_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching *pattern* (e.g. ``github:webhook:*``).
        Returns the number of keys deleted.
        """
        deleted = 0
        try:
            async for key in self._client.scan_iter(match=pattern):
                await self._client.delete(key)
                deleted += 1
        except aioredis.RedisError as exc:
            logger.error(f"Cache invalidation error | pattern={pattern}: {exc}")
        return deleted


# Singleton instance
cache_service = CacheService()
