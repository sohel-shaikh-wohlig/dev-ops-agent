"""
Cleanup Utilities
"""
import asyncio
from app.services.session_manager import session_manager
from app.core.config import get_settings
from app.core.logging_config import logger

settings = get_settings()

async def cleanup_old_sessions():
    """
    Periodic cleanup of old sessions
    """
    logger.info("Running session cleanup")
    count = session_manager.cleanup_expired_sessions()
    
    if count > 0:
        logger.info(f"Cleaned up {count} expired sessions")
    
    return count


async def start_cleanup_scheduler():
    """
    Start background task for periodic cleanup
    """
    while True:
        await asyncio.sleep(settings.SESSION_CLEANUP_INTERVAL_HOURS * 3600)
        await cleanup_old_sessions()