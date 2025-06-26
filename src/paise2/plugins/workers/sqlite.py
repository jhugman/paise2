import sys
from types import ModuleType
from typing import Callable

import click

from paise2.config.providers import FileConfigurationProvider
from paise2.plugins.core.interfaces import ConfigurationProvider, TaskQueueProvider
from paise2.plugins.core.registry import hookimpl
from paise2.plugins.providers.task_queue import HueySQLiteTaskQueueProvider


class SqliteWorkerPlugin:
    def __init__(
        self,
        tq_config_file: str = "sqlite.yaml",
        worker_config_file: str = "worker.yaml",
        plugin_module: ModuleType = sys.modules[__name__],
    ):
        self._tq_config_file = tq_config_file
        self._worker_config_file = worker_config_file
        self._plugin_module = plugin_module

    @hookimpl
    def register_task_queue_provider(
        self,
        register: Callable[[TaskQueueProvider], None],
    ) -> None:
        """Register task queue providers for production."""
        register(HueySQLiteTaskQueueProvider())  # Default SQLite for simple deployments

    @hookimpl
    def register_configuration_provider(
        self,
        register: Callable[[ConfigurationProvider], None],
    ) -> None:
        """Register the task queue configuration provider."""
        register(
            FileConfigurationProvider(
                self._tq_config_file,
                plugin_module=self._plugin_module,
                config_id="task_queue",
            )
        )
        register(
            FileConfigurationProvider(
                self._worker_config_file,
                plugin_module=self._plugin_module,
                config_id="worker",
            )
        )

    @hookimpl
    def register_commands(self, cli: click.Group) -> None:
        from .cli import register_commands

        register_commands(cli)
