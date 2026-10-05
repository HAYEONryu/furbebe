"""Emit application records without enabling SQL or request-body debug logging."""

import logging


def configure_logging():
    logger = logging.getLogger("furbebe")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
