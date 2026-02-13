"""
WebSocket Connection Manager
Tracks per-PR WebSocket connections for this FastAPI instance
and broadcasts updates to connected clients.
"""

import asyncio
from collections import defaultdict
from typing import Any, Dict, Set

from fastapi import WebSocket
from starlette.websockets import WebSocketState

from app.core.logging_config import logger


class WebSocketManager:
    """
    Instance-local WebSocket connection manager.

    Maintains a mapping of ``pr_number -> set[WebSocket]`` so that
    Pub/Sub messages can be fanned out only to clients watching a
    specific pull request.
    """

    def __init__(self) -> None:
        # pr_number → set of connected WebSocket clients
        self._connections: Dict[int, Set[WebSocket]] = defaultdict(set)

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def connect(self, pr_number: int, websocket: WebSocket) -> None:
        """Accept and register a WebSocket connection for *pr_number*."""
        await websocket.accept()
        self._connections[pr_number].add(websocket)
        logger.info(
            f"WS connected | pr=#{pr_number} | "
            f"clients={len(self._connections[pr_number])}"
        )

    def disconnect(self, pr_number: int, websocket: WebSocket) -> None:
        """Remove a WebSocket connection. Cleans up empty sets."""
        conns = self._connections.get(pr_number)
        if conns is None:
            return
        conns.discard(websocket)
        if not conns:
            del self._connections[pr_number]
        logger.info(
            f"WS disconnected | pr=#{pr_number} | "
            f"clients={len(self._connections.get(pr_number, set()))}"
        )

    async def disconnect_all(self) -> None:
        """Close every tracked connection. Called during app shutdown."""
        for pr_number, conns in list(self._connections.items()):
            for ws in list(conns):
                try:
                    if ws.client_state == WebSocketState.CONNECTED:
                        await ws.close(code=1001, reason="Server shutting down")
                except Exception:
                    pass
        self._connections.clear()
        logger.info("All WebSocket connections closed")

    # ------------------------------------------------------------------
    # Broadcasting
    # ------------------------------------------------------------------

    async def broadcast(self, pr_number: int, data: Dict[str, Any]) -> None:
        """
        Send *data* as JSON to every client watching *pr_number*.
        Dead connections are removed automatically.
        """
        conns = self._connections.get(pr_number)
        if not conns:
            return

        dead: list[WebSocket] = []

        async def _send(ws: WebSocket) -> None:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)

        await asyncio.gather(*[_send(ws) for ws in conns])

        for ws in dead:
            conns.discard(ws)
        if not conns:
            del self._connections[pr_number]

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    @property
    def total_connections(self) -> int:
        return sum(len(c) for c in self._connections.values())

    @property
    def active_prs(self) -> int:
        return len(self._connections)


# Global singleton
ws_manager = WebSocketManager()
