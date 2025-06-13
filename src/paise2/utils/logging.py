# ABOUTME: Basic logging utilities for the PAISE2 system
# ABOUTME: Provides simple logging setup and in-memory logger for bootstrap

from __future__ import annotations

import logging
from datetime import datetime


class SimpleInMemoryLogger:
    """Simple in-memory logger for bootstrap phase.

    This logger captures log messages during system startup before
    the real logger is configured. Messages can be replayed later.

    Implements the Logger protocol for consistency.
    """

    def __init__(self) -> None:
        self._logs: list[tuple[datetime, str, str]] = []

    def debug(self, message: str) -> None:
        """Log a debug message."""
        self._logs.append((datetime.now(), "DEBUG", message))

    def info(self, message: str) -> None:
        """Log an info message."""
        self._logs.append((datetime.now(), "INFO", message))

    def warning(self, message: str) -> None:
        """Log a warning message."""
        self._logs.append((datetime.now(), "WARNING", message))

    def error(self, message: str) -> None:
        """Log an error message."""
        self._logs.append((datetime.now(), "ERROR", message))

    def get_logs(self) -> list[tuple[datetime, str, str]]:
        """Get all captured log messages.

        Returns:
            List of tuples (timestamp, level, message)
        """
        return self._logs.copy()


def setup_logging(level: str = "INFO") -> logging.Logger:
    """Set up basic logging configuration.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)

    Returns:
        Configured logger instance
    """
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    return logging.getLogger("paise2")


def replay_logs(logger: logging.Logger, logs: list[tuple[datetime, str, str]]) -> None:
    """Replay captured logs to a real logger.

    Args:
        logger: Logger to replay messages to
        logs: List of log tuples from SimpleInMemoryLogger
    """
    for timestamp, level, message in logs:
        log_func = getattr(logger, level.lower(), logger.info)
        log_func(f"[Bootstrap {timestamp}] {message}")
