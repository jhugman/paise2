# ABOUTME: Test profile plugins - synchronous job queue for fast testing
# ABOUTME: Provides only synchronous job queue for unit tests and CI

from typing import Callable

from paise2.plugins.core.interfaces import JobQueueProvider
from paise2.plugins.core.jobs import NoJobQueueProvider
from paise2.plugins.core.registry import hookimpl


@hookimpl
def register_job_queue_provider(
    register: Callable[[JobQueueProvider], None],
) -> None:
    """Register the synchronous job queue provider for testing."""
    register(NoJobQueueProvider())
