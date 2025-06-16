# ABOUTME: Test profile plugins - synchronous task queues for fast testing
# ABOUTME: Provides only synchronous task queues for unit tests and CI

from typing import Callable

from paise2.plugins.core.interfaces import TaskQueueProvider
from paise2.plugins.core.registry import hookimpl
from paise2.plugins.providers.task_queue import NoTaskQueueProvider


@hookimpl
def register_task_queue_provider(
    register: Callable[[TaskQueueProvider], None],
) -> None:
    """Register the synchronous task queue provider for testing."""
    register(NoTaskQueueProvider())
