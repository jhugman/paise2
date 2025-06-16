# ABOUTME: Development profile plugins - multiple task queue providers
# ABOUTME: Provides both synchronous and SQLite task queues for development

from typing import Callable

from paise2.plugins.core.interfaces import TaskQueueProvider
from paise2.plugins.core.registry import hookimpl
from paise2.plugins.providers.task_queue import (
    HueySQLiteTaskQueueProvider,
    NoTaskQueueProvider,
)

# Note: We provide both providers in development for flexibility.
# The developer can choose which one to use based on their needs.

synchronous_task_provider = NoTaskQueueProvider()
sqlite_task_provider = HueySQLiteTaskQueueProvider(immediate=True)  # For debugging


@hookimpl
def register_task_queue_provider(
    register: Callable[[TaskQueueProvider], None],
) -> None:
    """Register both synchronous and SQLite task queue providers for development."""
    register(synchronous_task_provider)
    register(sqlite_task_provider)
