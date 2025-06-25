from typing import Any, Callable

from paise2.plugins.cli.config_commands import ConfigCliPlugin
from paise2.plugins.core.registry import hookimpl


@hookimpl
def register_plugin(register: Callable[[Any], None]) -> None:
    register(ConfigCliPlugin())
