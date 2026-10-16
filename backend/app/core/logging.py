"""Logging configuration for TruthGuard AI.

Provides structured, readable logs and guarantees secret sanitization.
"""

import logging
import sys
from typing import Optional


class SensitiveDataFilter(logging.Filter):
    """Filters log records to prevent accidental leaking of secret keys."""

    def __init__(self, secrets: Optional[list[str]] = None):
        super().__init__()
        self.secrets = [s for s in (secrets or []) if s and len(s) > 4]

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            for secret in self.secrets:
                if secret in record.msg:
                    record.msg = record.msg.replace(secret, "[REDACTED_SECRET]")
        return True


def setup_logging(level: int = logging.INFO, secrets: Optional[list[str]] = None) -> None:
    """Configures application-wide logging with formatting and redaction."""
    log_format = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    formatter = logging.Formatter(fmt=log_format, datefmt=date_format)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    if secrets:
        handler.addFilter(SensitiveDataFilter(secrets))

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers to avoid duplicates
    while root_logger.handlers:
        root_logger.handlers.pop()

    root_logger.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """Convenience accessor for named logger."""
    return logging.getLogger(name)


# Initialize default logger
setup_logging()
logger = get_logger("truthguard")
