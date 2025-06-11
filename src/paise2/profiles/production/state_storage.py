# ABOUTME: Production profile plugins - persistent storage providers
# ABOUTME: Provides file-based storage providers for production environments

from typing import Callable

from paise2.plugins.core.interfaces import StateStorageProvider
from paise2.plugins.core.registry import hookimpl
from paise2.state.providers import FileStateStorageProvider


@hookimpl
def register_state_storage_provider(
    register: Callable[[StateStorageProvider], None],
) -> None:
    """Register the file-based state storage provider for production."""
    register(FileStateStorageProvider())
