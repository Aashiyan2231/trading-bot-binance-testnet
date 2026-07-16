"""
Centralized logging configuration.

Logs go to:
  - logs/trading_bot.log  (rotating file, all levels DEBUG+)
  - console                (INFO+ only, human-friendly)

Every API request, response, and error is logged with enough context
(endpoint, params with secrets redacted, status code, response body)
to reconstruct what happened without being noisy about routine details.
"""

import logging
import os
from logging.handlers import RotatingFileHandler

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
LOG_FILE = os.path.join(LOG_DIR, "trading_bot.log")


def setup_logging(level: int = logging.DEBUG) -> logging.Logger:
    """Configure and return the root logger used across the app."""
    os.makedirs(LOG_DIR, exist_ok=True)

    logger = logging.getLogger("trading_bot")
    logger.setLevel(level)

    # Avoid duplicate handlers if setup_logging() is called more than once
    if logger.handlers:
        return logger

    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=2 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(fmt)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(fmt)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
