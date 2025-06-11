# ABOUTME: Development profile plugins - multiple job queue providers for flexibility
# ABOUTME: Provides both synchronous and SQLite job queues for development convenience

from typing import Callable

from paise2.plugins.core.interfaces import JobQueueProvider
from paise2.plugins.core.jobs import NoJobQueueProvider, SQLiteJobQueueProvider
from paise2.plugins.core.registry import hookimpl

# Note: We provide both providers in development for flexibility.
# The developer can choose which one to use based on their needs.

synchronous_provider = NoJobQueueProvider()
sqlite_provider = SQLiteJobQueueProvider()


@hookimpl
def register_job_queue_provider(
    register: Callable[[JobQueueProvider], None],
) -> None:
    """Register both synchronous and SQLite job queue providers for development."""
    register(synchronous_provider)
    register(sqlite_provider)
