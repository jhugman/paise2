import sys
from typing import Callable

from paise2.config.providers import FileConfigurationProvider
from paise2.plugins.core.interfaces import ConfigurationProvider
from paise2.plugins.core.registry import hookimpl


@hookimpl
def register_configuration_provider(
    register: Callable[[ConfigurationProvider], None],
) -> None:
    register(
        FileConfigurationProvider("logging.yaml", plugin_module=sys.modules[__name__])
    )
