import sys
from pathlib import Path
from types import ModuleType
from typing import Callable

import click

from paise2.config.providers import ProfileFileConfigurationProvider
from paise2.constants import get_default_task_db_path
from paise2.plugins.core.interfaces import (
    Configuration,
    ConfigurationProvider,
    LifecycleHost,
    ResetAction,
    TaskQueueProvider,
)
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
            ProfileFileConfigurationProvider(
                self._tq_config_file,
                plugin_module=self._plugin_module,
                config_id="task_queue",
            )
        )
        register(
            ProfileFileConfigurationProvider(
                self._worker_config_file,
                plugin_module=self._plugin_module,
                config_id="worker",
            )
        )

    @hookimpl
    def register_commands(self, cli: click.Group) -> None:
        from .cli import register_commands

        register_commands(cli)

    @hookimpl
    def register_reset_action(self, register: Callable[[ResetAction], None]) -> None:
        class ResetTaskQueue(ResetAction):
            def hard_reset(
                self,
                host: LifecycleHost,  # noqa: ARG002
                configuration: Configuration,
            ) -> None:
                db_path = configuration.get(
                    "task_queue.sqlite_path", get_default_task_db_path()
                )
                assert isinstance(db_path, str)
                resolved_path = Path(db_path).expanduser()
                resolved_path.unlink()

            def soft_reset(
                self, host: LifecycleHost, configuration: Configuration
            ) -> None:
                pass

        register(ResetTaskQueue())
