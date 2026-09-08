"""File-only logging configuration for pipeline runs."""

from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path

LOGGER_NAME = "seller_trust"
DEFAULT_LOG_DIR = Path("logs")


def configure_pipeline_logging(
    log_dir: str | Path = DEFAULT_LOG_DIR,
    level: str | int | None = None,
) -> logging.Logger:
    """Configure date-stamped, file-only logging and return the pipeline logger.

    ``PIPELINE_LOG_LEVEL`` provides a process-level default. Reconfiguring the
    logger replaces only the handler owned by this module, which keeps repeated
    pipeline runs in the same process safe.
    """
    configured_level = level or os.getenv("PIPELINE_LOG_LEVEL", "INFO")
    if isinstance(configured_level, str):
        configured_level = getattr(logging, configured_level.upper(), None)
        if not isinstance(configured_level, int):
            raise ValueError("PIPELINE_LOG_LEVEL must be a valid logging level")

    directory = Path(log_dir)
    directory.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(configured_level)
    logger.propagate = False

    for handler in logger.handlers[:]:
        if getattr(handler, "_seller_trust_handler", False):
            logger.removeHandler(handler)
            handler.close()

    filename = directory / f"pipeline_{datetime.now():%Y%m%d}.log"
    handler = logging.FileHandler(filename, encoding="utf-8")
    handler._seller_trust_handler = True
    handler.setLevel(configured_level)
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(handler)
    return logger


def get_pipeline_logger(name: str) -> logging.Logger:
    """Return a child logger that writes through the configured pipeline logger."""
    return logging.getLogger(f"{LOGGER_NAME}.{name}")
