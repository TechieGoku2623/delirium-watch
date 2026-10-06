"""structlog setup: pretty in dev, JSON when DELIRIUM_WATCH_ENV=prod."""

from __future__ import annotations

import logging
import os

import structlog


def configure_logging() -> None:
    pretty = os.environ.get("DELIRIUM_WATCH_ENV", "dev") != "prod"
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
    ]
    if pretty:
        processors.append(structlog.dev.ConsoleRenderer())
    else:
        processors.append(structlog.processors.JSONRenderer())
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        logger_factory=structlog.PrintLoggerFactory(),
    )
