# ABOUTME: State storage provider plugin registration functions.
# ABOUTME: Provides built-in state storage providers for plugin registration.

from typing import Callable

import pluggy

from paise2.plugins.core.registry import hookimpl
from paise2.plugins.core.interfaces import StateStorageProvider
from paise2.state.providers import FileStateStorageProvider, MemoryStateStorageProvider


@hookimpl
def register_state_storage_provider(
    register: Callable[[StateStorageProvider], None],
) -> None:
    """Register the default file-based state storage provider."""
    register(FileStateStorageProvider())


@hookimpl
def register_state_storage_provider_memory(
    register: Callable[[StateStorageProvider], None],
) -> None:
    """Register the memory-based state storage provider for testing."""
    register(MemoryStateStorageProvider())
