# LogRaven — Structured Logger
#
# PURPOSE:
#   Configures structured JSON logging for production.
#   Human-readable format for development.
#   Every log entry includes: timestamp, level, logger name, message.
#   Request middleware adds request_id to all log entries within a request.
#
# USAGE:
#   from app.utils.logger import get_logger
#   logger = get_logger(__name__)
#   logger.info("Processing investigation", investigation_id=str(inv_id))
#
# TODO Month 1 Week 1: Implement basic logger. Full structured logging Month 5.

import logging
import os


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(logging.DEBUG if os.getenv("DEBUG") == "True" else logging.INFO)
    return logger
