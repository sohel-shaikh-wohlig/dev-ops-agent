"""
Logging Configuration
"""
import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from app.core.config import get_settings


def setup_logging() -> logging.Logger:
    """
    Setup application logging with console and file handlers
    """
    # Get settings
    settings = get_settings()

    # Create logger
    logger = logging.getLogger("devops_api")

    # Prevent adding duplicate handlers if already configured
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, settings.LOG_LEVEL))

    # Create formatters
    formatter = logging.Formatter(settings.LOG_FORMAT)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (if log file path is specified)
    if settings.LOG_FILE:
        # Create logs directory
        settings.LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = RotatingFileHandler(
            settings.LOG_FILE,
            maxBytes=10485760,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # Log Stream Handler
    from app.core.log_stream import log_stream_handler
    logger.addHandler(log_stream_handler)
    
    return logger


# Create logger instance
logger = setup_logging()