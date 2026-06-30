"""
logger.py
=========
Centralised logging setup for the AI Candidate Discovery System backend.

Usage
-----
    from logger import get_logger

    log = get_logger(__name__)
    log.info("Hello from module %s", __name__)

All modules must import their logger through this factory so that:
  * console + rotating-file handlers are attached exactly once
  * log format is consistent across the whole backend
  * the log directory is created automatically if absent
"""

from __future__ import annotations

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional

# Lazy import of config to avoid circular dependencies at import time.
# We import only what is needed.
from config import (
    LOG_DIR,
    LOG_FILE,
    LOG_LEVEL_CONSOLE,
    LOG_LEVEL_FILE,
    LOG_MAX_BYTES,
    LOG_BACKUP_COUNT,
)

# ---------------------------------------------------------------------------
# Module-level sentinel: tracks whether the root backend logger has been
# configured already.  Prevents duplicate handlers when get_logger() is
# called multiple times.
# ---------------------------------------------------------------------------
_CONFIGURED: bool = False

# Name for the shared root logger that every module logger inherits from.
_ROOT_LOGGER_NAME: str = "redrob"

# ---------------------------------------------------------------------------
# Log format strings
# ---------------------------------------------------------------------------
_FMT_DETAIL = (
    "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s"
)
_FMT_SIMPLE = "%(asctime)s | %(levelname)-8s | %(message)s"

_DATE_FMT = "%Y-%m-%d %H:%M:%S"


def _level(name: str) -> int:
    """Convert a string level name to the corresponding logging constant."""
    level = logging.getLevelName(name.upper())
    if not isinstance(level, int):
        raise ValueError(
            f"Invalid log level '{name}'. "
            "Expected one of: DEBUG, INFO, WARNING, ERROR, CRITICAL."
        )
    return level


def _configure_root_logger() -> None:
    """
    Attach a console handler and a rotating file handler to the shared root
    logger exactly once.  Subsequent calls are no-ops.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    # Ensure the log directory exists
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger(_ROOT_LOGGER_NAME)
    root.setLevel(logging.DEBUG)  # handlers filter at their own levels

    # ---- Console handler ---------------------------------------------------
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(_level(LOG_LEVEL_CONSOLE))
    console_handler.setFormatter(
        logging.Formatter(fmt=_FMT_SIMPLE, datefmt=_DATE_FMT)
    )

    # ---- Rotating file handler ---------------------------------------------
    file_handler = logging.handlers.RotatingFileHandler(
        filename=LOG_FILE,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(_level(LOG_LEVEL_FILE))
    file_handler.setFormatter(
        logging.Formatter(fmt=_FMT_DETAIL, datefmt=_DATE_FMT)
    )

    root.addHandler(console_handler)
    root.addHandler(file_handler)

    _CONFIGURED = True


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Return a logger that is a child of the shared ``redrob`` root logger.

    Parameters
    ----------
    name:
        Typically ``__name__`` of the calling module.  If *None* the root
        ``redrob`` logger is returned directly.

    Returns
    -------
    logging.Logger
    """
    _configure_root_logger()

    if name is None:
        return logging.getLogger(_ROOT_LOGGER_NAME)

    # Prefix every module logger under the "redrob" namespace so that all
    # child loggers inherit the handlers above.
    logger_name = (
        name if name.startswith(_ROOT_LOGGER_NAME)
        else f"{_ROOT_LOGGER_NAME}.{name}"
    )
    return logging.getLogger(logger_name)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
__all__ = ["get_logger"]
