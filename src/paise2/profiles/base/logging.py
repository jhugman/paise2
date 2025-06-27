# ABOUTME: Base profile logging configuration provider
# ABOUTME: Provides profile-sensitive logging configuration

import sys
from typing import Callable

from paise2.config.providers import ProfileFileConfigurationProvider
from paise2.plugins.core.interfaces import ConfigurationProvider
from paise2.plugins.core.registry import hookimpl


@hookimpl
def register_configuration_provider(
    register: Callable[[ConfigurationProvider], None],
) -> None:
    """Register profile-sensitive logging configuration provider.

    This provider will look for logging.yaml in:
    - ../production/logging.yaml when PAISE2_PROFILE=production
    - ../development/logging.yaml when PAISE2_PROFILE=development
    - ../development/logging.yaml when PAISE2_PROFILE is not set (default)
    """
    register(
        ProfileFileConfigurationProvider(
            "logging.yaml", plugin_module=sys.modules[__name__]
        )
    )
