"""
WebSocket Routes
Real-time PR status updates via WebSocket.

Endpoints:
  WS /ws/pr-status/{pr_number} — Stream Terraform plan/apply status updates
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.logging_config import logger
from app.core.websocket_manager import ws_manager
from app.services.github_webhook_service import github_webhook_service

ws_router = APIRouter(prefix="/ws", tags=["WebSocket"])


@ws_router.websocket("/pr-status/{pr_number}")
async def ws_pr_status(websocket: WebSocket, pr_number: int) -> None:
    """
    WebSocket endpoint for real-time PR status updates.

    On connect:
      1. Accepts the connection and registers it with WebSocketManager.
      2. Sends the current PR status from Redis (or an idle default).

    Then keeps the connection open, waiting for client disconnect.
    Updates are pushed by the Pub/Sub subscriber via ``ws_manager.broadcast()``.
    """
    await ws_manager.connect(pr_number, websocket)

    try:
        # Send the current state immediately so the client doesn't miss
        # updates that arrived between its last REST poll and this connect.
        current = await github_webhook_service.get_pr_status(pr_number)
        if current is not None:
            await websocket.send_json({**current, "pr_number": pr_number})
        else:
            await websocket.send_json({"pr_number": pr_number, "state": "idle"})

        # Hold the connection open. The only purpose of this loop is to
        # detect client disconnect; all server-initiated sends go through
        # ws_manager.broadcast() which is triggered by the Pub/Sub subscriber.
        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.error(f"WebSocket error | pr=#{pr_number}: {exc}")
    finally:
        ws_manager.disconnect(pr_number, websocket)
