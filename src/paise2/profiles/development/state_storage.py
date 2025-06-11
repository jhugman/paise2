# ABOUTME: Development profile plugins - both storage providers for flexibility
# ABOUTME: Provides both memory and file-based storage for development convenience

from typing import Callable

from paise2.plugins.core.interfaces import StateStorageProvider
from paise2.plugins.core.registry import hookimpl
from paise2.state.providers import FileStateStorageProvider, MemoryStateStorageProvider

# Note: We need two separate modules or classes to register multiple providers
# since hookimpl functions with the same name can't exist in the same module.
# This approach uses a simple workaround with different variable names but same hook.

memory_provider = MemoryStateStorageProvider()
file_provider = FileStateStorageProvider()


@hookimpl
def register_state_storage_provider(
    register: Callable[[StateStorageProvider], None],
) -> None:
    """Register both memory and file-based state storage providers for development."""
    register(memory_provider)
    register(file_provider)
