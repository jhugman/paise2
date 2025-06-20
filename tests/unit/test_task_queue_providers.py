# ABOUTME: Unit tests for TaskQueueProvider implementations that replace JobQueue
# ABOUTME: Tests Huey integration and both synchronous and persistent task queues

from __future__ import annotations

from typing import Any


class MockConfiguration:
    """Mock configuration for testing."""

    def __init__(self, data: dict[str, Any] | None = None) -> None:
        self._data = data or {}

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        keys = key.split(".")
        current = self._data
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return default
        return current

    def get_section(self, section: str) -> dict[str, Any]:
        """Get configuration section."""
        return self._data.get(section, {})


def test_no_task_queue_provider_returns_memory_huey() -> None:
    """Test that NoTaskQueueProvider returns MemoryHuey for synchronous execution."""
    from huey import MemoryHuey

    from paise2.plugins.providers.task_queue import NoTaskQueueProvider

    provider = NoTaskQueueProvider()
    configuration = MockConfiguration({})

    task_queue = provider.create_task_queue(configuration)

    assert task_queue is not None
    assert isinstance(task_queue, MemoryHuey)
    assert task_queue.immediate is True  # Should execute immediately for testing


def test_huey_sqlite_task_queue_provider_creates_huey_instance() -> None:
    """Test that HueySQLiteTaskQueueProvider creates a Huey instance."""
    from paise2.plugins.providers.task_queue import HueySQLiteTaskQueueProvider

    provider = HueySQLiteTaskQueueProvider()
    configuration = MockConfiguration({"task_queue": {"sqlite_path": "test_tasks.db"}})

    task_queue = provider.create_task_queue(configuration)

    assert task_queue is not None
    # Check it's a Huey instance
    assert hasattr(task_queue, "task")
    assert hasattr(task_queue, "periodic_task")


def test_huey_sqlite_task_queue_provider_with_default_path() -> None:
    """Test HueySQLiteTaskQueueProvider uses default path when not configured."""
    from paise2.plugins.providers.task_queue import HueySQLiteTaskQueueProvider

    provider = HueySQLiteTaskQueueProvider()
    configuration = MockConfiguration({})

    task_queue = provider.create_task_queue(configuration)

    assert task_queue is not None
    assert hasattr(task_queue, "task")


def test_huey_sqlite_task_queue_provider_immediate_mode() -> None:
    """Test HueySQLiteTaskQueueProvider immediate mode for debugging."""
    from paise2.plugins.providers.task_queue import HueySQLiteTaskQueueProvider

    provider = HueySQLiteTaskQueueProvider(immediate=True)
    configuration = MockConfiguration({})

    task_queue = provider.create_task_queue(configuration)

    assert task_queue is not None
    # Check immediate mode is enabled
    assert task_queue.immediate is True
