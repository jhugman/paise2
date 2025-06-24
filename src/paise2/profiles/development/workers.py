# ABOUTME: Developement profile plugins - persistent task queues
# ABOUTME: Provides SQLite-based and Redis task queues environments

import sys
from typing import Any, Callable

from paise2.plugins.core.registry import hookimpl
from paise2.plugins.workers.sqlite import SqliteWorkerPlugin


@hookimpl
def register_plugin(register: Callable[[Any], None]) -> None:
    """Register the SQLite worker plugin."""
    register(
        SqliteWorkerPlugin(
            config_file="task_queue.yaml", plugin_module=sys.modules[__name__]
        )
    )
