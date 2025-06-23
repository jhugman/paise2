# ABOUTME: Worker configuration provider for PAISE2 worker system
# ABOUTME: Provides default worker settings integrated with existing config system

import sys
from typing import Callable

from paise2.config.providers import FileConfigurationProvider
from paise2.plugins.core.interfaces import ConfigurationProvider
from paise2.plugins.core.registry import hookimpl

# Get current module for relative path resolution
current_module = sys.modules[__name__]

# Create file-based configuration provider for worker config
worker_config_provider = FileConfigurationProvider(
    "worker-config.yaml", plugin_module=current_module
)


@hookimpl
def register_configuration_provider(
    register: Callable[[ConfigurationProvider], None],
) -> None:
    """Register the worker configuration provider."""
    register(worker_config_provider)
