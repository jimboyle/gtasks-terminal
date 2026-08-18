"""
Logging configuration for the Google Tasks CLI application.
"""

import logging
import os
from pathlib import Path

# Quiet noisy third-party loggers (Google API client cache chatter, etc.)
for _noisy in ('googleapiclient.discovery_cache', 'googleapiclient', 'google.auth', 'LiteLLM', 'litellm'):
    logging.getLogger(_noisy).setLevel(logging.ERROR)


def setup_logger(name='gtasks'):
    """
    Configure application logging with:
    - Console output (INFO level)
    - File output with rotation (DEBUG level)
    - Structured log format
    
    Args:
        name (str): Logger name
        
    Returns:
        logging.Logger: Configured logger instance
    """
    
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    # Don't re-emit through any root handler (kills duplicate rich-formatted console lines)
    logger.propagate = False

    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger

    # Console verbosity: default WARNING (quiet). Override via GTASKS_LOG_LEVEL=INFO|DEBUG|ERROR.
    console_level = getattr(
        logging, os.environ.get('GTASKS_LOG_LEVEL', 'WARNING').upper(), logging.WARNING
    )
    
    # Log directory
    log_dir = Path.home() / '.gtasks' / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Format
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    
    # Console handler (quiet by default; see GTASKS_LOG_LEVEL above)
    console = logging.StreamHandler()
    console.setLevel(console_level)
    console.setFormatter(formatter)
    
    # File handler with rotation (DEBUG)
    from logging.handlers import RotatingFileHandler
    file_handler = RotatingFileHandler(
        log_dir / 'gtasks.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    logger.addHandler(console)
    logger.addHandler(file_handler)
    
    return logger