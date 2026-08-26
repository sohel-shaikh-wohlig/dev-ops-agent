"""
Redis Pub/Sub Subscriber
Background task that listens for PR status update events published
by any FastAPI instance and fans them out to local WebSocket clients.
"""

import asyncio
import json
from typing import Optional

import redis.asyncio as aioredis

from app.core.config import get_settings
from app.core.logging_config import logger
from app.core.websocket_manager import ws_manager

CHANNEL_PATTERN = "pr_updates:*"
MAX_BACKOFF = 30  # seconds


class PubSubSubscriber:
    """
    Manages a background asyncio task that subscribes to
    ``pr_updates:*`` via Redis pattern-subscribe and dispatches
    incoming messages to the WebSocketManager.
    """

    def __init__(self) -> None:
        self._task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self) -> None:
        """Launch the subscriber background task."""
        if self._task is not None:
            logger.warning("Pub/Sub subscriber is already running")
            return
        self._running = True
        self._task = asyncio.create_task(self._listen_loop())
        logger.info("Pub/Sub subscriber started")

    async def stop(self) -> None:
        """Cancel the subscriber task and wait for it to finish."""
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Pub/Sub subscriber stopped")

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _listen_loop(self) -> None:
        """
        Reconnecting listener loop.  On disconnect it backs off
        exponentially (1 s → 2 s → 4 s → … → 30 s) then retries.
        """
        backoff = 1

        while self._running:
            pubsub: Optional[aioredis.client.PubSub] = None
            client: Optional[aioredis.Redis] = None
            try:
                settings = get_settings()
                client = aioredis.from_url(
                    settings.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                )
                pubsub = client.pubsub()
                await pubsub.psubscribe(CHANNEL_PATTERN)
                logger.info(f"Pub/Sub subscribed to {CHANNEL_PATTERN}")
                backoff = 1  # reset on successful subscribe

                async for message in pubsub.listen():
                    if not self._running:
                        break
                    if message["type"] != "pmessage":
                        continue
                    await self._dispatch(message)

            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.error(f"Pub/Sub listener error: {exc}")
                if not self._running:
                    break
                logger.info(f"Pub/Sub reconnecting in {backoff}s")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, MAX_BACKOFF)
            finally:
                # Both the pubsub AND the client it came from must be released.
                #
                # from_url() builds a new Redis client with its own connection
                # pool on every iteration of this loop. Closing only the pubsub
                # left that pool open, so each reconnect leaked a pool and its
                # sockets — unbounded over a long-running instability, which is
                # exactly when this loop iterates most.
                if pubsub is not None:
                    try:
                        await pubsub.punsubscribe(CHANNEL_PATTERN)
                        await pubsub.aclose()
                    except Exception as exc:
                        logger.debug(f"Pub/Sub cleanup failed (non-fatal): {exc}")
                if client is not None:
                    try:
                        await client.aclose()
                    except Exception as exc:
                        logger.debug(f"Redis client close failed (non-fatal): {exc}")

    @staticmethod
    async def _dispatch(message: dict) -> None:
        """Extract pr_number from channel and broadcast to WebSocket clients."""
        channel: str = message.get("channel", "")
        # channel format: "pr_updates:{pr_number}"
        parts = channel.rsplit(":", 1)
        if len(parts) != 2:
            return

        try:
            pr_number = int(parts[1])
        except ValueError:
            logger.warning(f"Invalid PR number in Pub/Sub channel: {channel}")
            return

        raw_data = message.get("data", "")
        try:
            data = json.loads(raw_data) if isinstance(raw_data, str) else raw_data
        except json.JSONDecodeError:
            logger.warning(f"Corrupt Pub/Sub message on {channel}")
            return

        await ws_manager.broadcast(pr_number, data)


# Global singleton
pubsub_subscriber = PubSubSubscriber()
