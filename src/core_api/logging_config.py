"""
Logging configuration for MAAI Core API.

Provides a centralised logger factory so all modules use consistent
formatting and honour the LOG_LEVEL environment variable.
"""

import logging
import os


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger for the given module name.

    Log format: ``YYYY-MM-DD HH:MM:SS,mmm | name | LEVEL | message``
    Level is controlled by the ``LOG_LEVEL`` environment variable (default: INFO).
    """
    logger = logging.getLogger(name)

    # Only configure handlers once per logger instance.
    if not logger.handlers:
        level_name = os.getenv("LOG_LEVEL", "INFO").upper()
        level = getattr(logging, level_name, logging.INFO)

        logger.setLevel(level)

        handler = logging.StreamHandler()
        handler.setLevel(level)

        formatter = logging.Formatter(
            fmt="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        # Prevent log records from propagating to the root logger so we
        # don't get duplicate output when the root logger also has handlers.
        logger.propagate = False

    return logger
