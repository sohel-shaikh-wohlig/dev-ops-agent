"""
Redis Connection Manager
Provides async Redis connection pooling and lifecycle management.
"""

from typing import Optional

import redis.asyncio as aioredis
from redis.asyncio import ConnectionPool, Redis

from app.core.config import get_settings
from app.core.logging_config import logger


class RedisManager:
    """
    Async Redis connection manager with connection pooling.

    Usage:
        redis_manager = RedisManager()
        await redis_manager.connect()     # call during app startup
        client = redis_manager.client     # use anywhere
        await redis_manager.close()       # call during app shutdown
    """

    def __init__(self) -> None:
        self._pool: Optional[ConnectionPool] = None
        self._client: Optional[Redis] = None

    @property
    def client(self) -> Redis:
        """Return the active Redis client. Raises if not connected."""
        if self._client is None:
            raise RuntimeError(
                "Redis is not connected. Call 'await redis_manager.connect()' first."
            )
        return self._client

    @property
    def is_connected(self) -> bool:
        return self._client is not None

    async def connect(self) -> None:
        """Create the connection pool and Redis client."""
        if self._client is not None:
            logger.warning("Redis is already connected, skipping reconnect")
            return

        settings = get_settings()

        self._pool = ConnectionPool.from_url(
            settings.redis_url,
            max_connections=settings.REDIS_MAX_CONNECTIONS,
            socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
            socket_connect_timeout=settings.REDIS_SOCKET_TIMEOUT,
            decode_responses=True,
            encoding="utf-8",
        )
        self._client = Redis(connection_pool=self._pool)

        # Verify the connection is alive
        try:
            await self._client.ping()
            logger.info(
                f"Redis connected | url={settings.redis_url} | "
                f"max_connections={settings.REDIS_MAX_CONNECTIONS}"
            )
        except aioredis.RedisError as exc:
            logger.error(f"Redis connection failed: {exc}")
            self._client = None
            self._pool = None
            raise

    async def close(self) -> None:
        """Gracefully close the Redis client and connection pool."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            logger.info("Redis client closed")
        if self._pool is not None:
            await self._pool.aclose()
            self._pool = None
            logger.info("Redis connection pool closed")

    async def health_check(self) -> bool:
        """Return True if Redis is reachable, False otherwise."""
        if self._client is None:
            return False
        try:
            return await self._client.ping()
        except aioredis.RedisError:
            return False


# Global singleton — initialised at import, connected during app lifespan
redis_manager = RedisManager()
