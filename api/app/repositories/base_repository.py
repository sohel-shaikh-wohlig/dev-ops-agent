"""
Base Redis Repository
Generic async repository for Redis-backed data access with Pydantic model support.
"""

import json
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

from pydantic import BaseModel
from redis.asyncio import Redis
import redis.asyncio as aioredis

from app.core.logging_config import logger
from app.core.redis import redis_manager

T = TypeVar("T", bound=BaseModel)


class BaseRedisRepository(Generic[T]):
    """
    Generic Redis repository with CRUD operations and TTL support.

    Subclass and set ``prefix`` and ``model_class`` to create
    a typed repository for any Pydantic model:

        class PRStatusRepository(BaseRedisRepository[PRStatusModel]):
            prefix = "github:webhook"
            model_class = PRStatusModel
            default_ttl = 7200
    """

    prefix: str = ""
    model_class: Type[T]
    default_ttl: Optional[int] = None  # seconds; None = no expiry

    def _key(self, identifier: str) -> str:
        """Build a fully-qualified Redis key."""
        return f"{self.prefix}:{identifier}"

    @property
    def _client(self) -> Redis:
        return redis_manager.client

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def create(
        self,
        identifier: str,
        data: T,
        ttl: Optional[int] = None,
    ) -> None:
        """Persist a model instance in Redis."""
        effective_ttl = ttl if ttl is not None else self.default_ttl
        try:
            await self._client.set(
                self._key(identifier),
                data.model_dump_json(),
                ex=effective_ttl,
            )
        except aioredis.RedisError as exc:
            logger.error(f"Redis SET error | key={self._key(identifier)}: {exc}")
            raise

    async def get(self, identifier: str) -> Optional[T]:
        """Retrieve a model instance from Redis, or None if missing."""
        try:
            raw = await self._client.get(self._key(identifier))
        except aioredis.RedisError as exc:
            logger.error(f"Redis GET error | key={self._key(identifier)}: {exc}")
            raise

        if raw is None:
            return None

        try:
            return self.model_class.model_validate_json(raw)
        except Exception:
            logger.warning(
                f"Corrupt data in Redis | key={self._key(identifier)}, purging"
            )
            await self.delete(identifier)
            return None

    async def get_raw(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Retrieve raw dict from Redis, or None if missing."""
        try:
            raw = await self._client.get(self._key(identifier))
        except aioredis.RedisError as exc:
            logger.error(f"Redis GET error | key={self._key(identifier)}: {exc}")
            raise

        if raw is None:
            return None

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning(
                f"Corrupt JSON in Redis | key={self._key(identifier)}, purging"
            )
            await self.delete(identifier)
            return None

    async def set_raw(
        self,
        identifier: str,
        data: Dict[str, Any],
        ttl: Optional[int] = None,
    ) -> None:
        """Persist a raw dict in Redis."""
        effective_ttl = ttl if ttl is not None else self.default_ttl
        try:
            await self._client.set(
                self._key(identifier),
                json.dumps(data),
                ex=effective_ttl,
            )
        except aioredis.RedisError as exc:
            logger.error(f"Redis SET error | key={self._key(identifier)}: {exc}")
            raise

    async def delete(self, identifier: str) -> bool:
        """Delete a key. Returns True if the key existed."""
        try:
            return bool(await self._client.delete(self._key(identifier)))
        except aioredis.RedisError as exc:
            logger.error(f"Redis DEL error | key={self._key(identifier)}: {exc}")
            raise

    async def exists(self, identifier: str) -> bool:
        """Check whether a key exists."""
        try:
            return bool(await self._client.exists(self._key(identifier)))
        except aioredis.RedisError as exc:
            logger.error(f"Redis EXISTS error | key={self._key(identifier)}: {exc}")
            raise

    async def find_keys(self, pattern: str) -> List[str]:
        """Return all keys matching a pattern under this repository's prefix."""
        full_pattern = f"{self.prefix}:{pattern}"
        try:
            keys = []
            async for key in self._client.scan_iter(match=full_pattern):
                keys.append(key)
            return keys
        except aioredis.RedisError as exc:
            logger.error(f"Redis SCAN error | pattern={full_pattern}: {exc}")
            raise
