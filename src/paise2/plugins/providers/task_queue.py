# ABOUTME: Task queue provider implementations using Huey for async job processing
# ABOUTME: Provides sync (None), SQLite, and Redis task queue implementations

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from huey import Huey

    from paise2.config.models import Configuration


class NoTaskQueueProvider:
    """
    Task queue provider that returns a MemoryHuey for synchronous execution.

    Used in testing and development when immediate execution is preferred
    over asynchronous task processing. Uses in-memory storage with immediate
    execution for fast, isolated tests.
    """

    def create_task_queue(self, configuration: Configuration) -> Huey:
        """
        Create a task queue that executes synchronously using memory storage.

        Args:
            configuration: System configuration (ignored for memory execution)

        Returns:
            MemoryHuey instance with immediate execution for testing
        """
        from huey import MemoryHuey

        _ = configuration  # Explicitly acknowledge unused parameter

        return MemoryHuey(
            "paise2-test",
            immediate=True,  # Execute tasks synchronously
            results=True,
            utc=True,
        )


class HueySQLiteTaskQueueProvider:
    """
    Task queue provider that creates SQLite-backed Huey instances.

    Suitable for development and single-machine deployments where
    persistent task queues are needed without external dependencies.
    """

    def __init__(self, immediate: bool = False) -> None:
        """
        Initialize the SQLite task queue provider.

        Args:
            immediate: Whether to execute tasks immediately for debugging
        """
        self.immediate = immediate

    def create_task_queue(self, configuration: Configuration) -> Huey:
        """
        Create a SQLite-backed Huey instance.

        Args:
            configuration: System configuration containing SQLite settings

        Returns:
            Huey instance configured with SQLite backend
        """
        from huey import SqliteHuey

        db_path = configuration.get(
            "task_queue.sqlite_path", "~/.local/share/paise2/tasks.db"
        )
        resolved_path = Path(db_path).expanduser()

        # Ensure directory exists
        resolved_path.parent.mkdir(parents=True, exist_ok=True)

        return SqliteHuey(
            "paise2",
            filename=str(resolved_path),
            immediate=self.immediate,
            results=True,
            utc=True,
        )


class HueyRedisTaskQueueProvider:
    """
    Task queue provider that creates Redis-backed Huey instances.

    Suitable for production deployments with multiple workers and
    high-availability requirements.
    """

    def create_task_queue(self, configuration: Configuration) -> Huey:
        """
        Create a Redis-backed Huey instance.

        Args:
            configuration: System configuration containing Redis settings

        Returns:
            Huey instance configured with Redis backend
        """
        from huey import RedisHuey

        return RedisHuey(
            "paise2",
            host=configuration.get("redis.host", "localhost"),
            port=configuration.get("redis.port", 6379),
            db=configuration.get("redis.db", 0),
            immediate=False,
            results=True,
        )
