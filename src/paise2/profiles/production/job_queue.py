# ABOUTME: Production profile plugins - persistent task queues for production
# ABOUTME: Provides SQLite-based and Redis task queues for production environments

from typing import Callable

from paise2.plugins.core.interfaces import TaskQueueProvider
from paise2.plugins.core.registry import hookimpl
from paise2.plugins.providers.task_queue import (
    HueyRedisTaskQueueProvider,
    HueySQLiteTaskQueueProvider,
)


@hookimpl
def register_task_queue_provider(
    register: Callable[[TaskQueueProvider], None],
) -> None:
    """Register task queue providers for production."""
    register(HueySQLiteTaskQueueProvider())  # Default SQLite for simple deployments
    register(HueyRedisTaskQueueProvider())  # Redis for high-scale deployments
