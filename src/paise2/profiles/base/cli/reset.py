from typing import Any, Callable

from paise2.plugins.cli.reset_commands import ResetCliPlugin
from paise2.plugins.core.registry import hookimpl


@hookimpl
def register_plugin(register: Callable[[Any], None]) -> None:
    register(ResetCliPlugin())
