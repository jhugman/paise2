# ABOUTME: Production profile plugins - persistent job queue for production
# ABOUTME: Provides only SQLite-based job queue for production environments

from typing import Callable

from paise2.plugins.core.interfaces import JobQueueProvider
from paise2.plugins.core.jobs import SQLiteJobQueueProvider
from paise2.plugins.core.registry import hookimpl


@hookimpl
def register_job_queue_provider(
    register: Callable[[JobQueueProvider], None],
) -> None:
    """Register the SQLite job queue provider for production."""
    register(SQLiteJobQueueProvider())
