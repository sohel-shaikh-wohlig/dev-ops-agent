
import logging
import asyncio
import json
from contextvars import ContextVar
from typing import Optional

# Context variable to track the current request ID
request_id_ctx: ContextVar[Optional[str]] = ContextVar("request_id", default=None)

class LogStreamHandler(logging.Handler):
    """
    Logging handler that streams logs to a queue based on request ID context
    """
    def __init__(self):
        super().__init__()
        self.queues: dict[str, asyncio.Queue] = {}

    def register(self, request_id: str) -> asyncio.Queue:
        """Register a new request ID and return its queue"""
        queue = asyncio.Queue()
        self.queues[request_id] = queue
        return queue

    def unregister(self, request_id: str):
        """Unregister a request ID"""
        if request_id in self.queues:
            del self.queues[request_id]

    def emit(self, record: logging.LogRecord):
        """Emit a log record to the appropriate queue (thread-safe)"""
        try:
            request_id = request_id_ctx.get()
            if request_id and request_id in self.queues:
                msg = self.format(record)

                # Create a structured log message
                log_entry = {
                    "type": "log",
                    "level": record.levelname,
                    "message": msg,
                    "timestamp": record.created
                }

                queue = self.queues[request_id]
                item = json.dumps(log_entry)

                # Use call_soon_threadsafe when called from a worker thread,
                # fall back to put_nowait when on the event loop thread.
                try:
                    loop = asyncio.get_running_loop()
                    loop.call_soon_threadsafe(queue.put_nowait, item)
                except RuntimeError:
                    # No running loop (shouldn't happen, but be safe)
                    try:
                        queue.put_nowait(item)
                    except asyncio.QueueFull:
                        pass
        except Exception:
            self.handleError(record)

# Global instance
log_stream_handler = LogStreamHandler()
log_stream_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
