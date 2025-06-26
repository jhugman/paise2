# ABOUTME: Basic logging utilities for the PAISE2 system
# ABOUTME: Provides simple logging setup and in-memory logger for bootstrap

from __future__ import annotations

import logging
from datetime import datetime
from typing import Union

# Type for values that can be formatted in log messages
LogFormattableValue = Union[str, int, float, bool, None]


class SimpleInMemoryLogger:
    """Simple in-memory logger for bootstrap phase.

    This logger captures log messages during system startup before
    the real logger is configured. Messages can be replayed later.

    Implements the Logger protocol for consistency.
    """

    def __init__(self) -> None:
        self._logs: list[tuple[datetime, str, str]] = []

    def debug(self, message: str, *args: LogFormattableValue) -> None:
        """Log a debug message."""
        formatted_message = message % args if args else message
        self._logs.append((datetime.now(), "DEBUG", formatted_message))

    def info(self, message: str, *args: LogFormattableValue) -> None:
        """Log an info message."""
        formatted_message = message % args if args else message
        self._logs.append((datetime.now(), "INFO", formatted_message))

    def warning(self, message: str, *args: LogFormattableValue) -> None:
        """Log a warning message."""
        formatted_message = message % args if args else message
        self._logs.append((datetime.now(), "WARNING", formatted_message))

    def error(self, message: str, *args: LogFormattableValue) -> None:
        """Log an error message."""
        formatted_message = message % args if args else message
        self._logs.append((datetime.now(), "ERROR", formatted_message))

    def exception(self, message: str, *args: LogFormattableValue) -> None:
        """Log an exception with traceback."""
        import traceback

        formatted_message = message % args if args else message
        traceback_info = traceback.format_exc()
        full_message = f"{formatted_message}\n{traceback_info}"
        self._logs.append((datetime.now(), "ERROR", full_message))

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


class StandardLoggerWrapper:
    """Wrapper around Python's standard logging that implements Logger protocol.

    This logger configures itself based on provided parameters and provides
    a consistent interface for the PAISE2 system.
    """

    def __init__(
        self, name: str = "paise2", level: str = "INFO", format_str: str | None = None
    ):
        self._logger = logging.getLogger(name)

        # Set up the logger level
        self._logger.setLevel(getattr(logging, level.upper()))

        # Clear any existing handlers to avoid duplicates
        self._logger.handlers.clear()

        # Prevent propagation to parent loggers to avoid duplicate messages
        self._logger.propagate = False

        # Create console handler
        handler = logging.StreamHandler()
        handler.setLevel(getattr(logging, level.upper()))  # Set format
        if format_str is None:
            format_str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

        # Handle simple format strings by mapping them to proper logging formats
        if format_str.lower() == "simple":
            format_str = "%(levelname)s: %(message)s"

        formatter = logging.Formatter(format_str, datefmt="%Y-%m-%d %H:%M:%S")
        handler.setFormatter(formatter)

        # Add handler to logger
        self._logger.addHandler(handler)

    def debug(self, message: str, *args: LogFormattableValue) -> None:
        """Log a debug message."""
        self._logger.debug(message, *args)

    def info(self, message: str, *args: LogFormattableValue) -> None:
        """Log an info message."""
        self._logger.info(message, *args)

    def warning(self, message: str, *args: LogFormattableValue) -> None:
        """Log a warning message."""
        self._logger.warning(message, *args)

    def error(self, message: str, *args: LogFormattableValue) -> None:
        """Log an error message."""
        self._logger.error(message, *args)

    def exception(self, message: str, *args: LogFormattableValue) -> None:
        """Log an exception with traceback."""
        self._logger.exception(message, *args)
