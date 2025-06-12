# ABOUTME: Development profile plugins - both storage providers for flexibility
# ABOUTME: Provides both memory and SQLite-based storage for development convenience

from typing import Callable

from paise2.plugins.core.interfaces import DataStorageProvider
from paise2.plugins.core.registry import hookimpl
from paise2.storage.providers import (
    MemoryDataStorageProvider,
    SQLiteDataStorageProvider,
)

# Note: We need two separate modules or classes to register multiple providers
# since hookimpl functions with the same name can't exist in the same module.
# This approach uses a simple workaround with different variable names but same hook.

memory_provider = MemoryDataStorageProvider()
sqlite_provider = SQLiteDataStorageProvider()


@hookimpl
def register_data_storage_provider(
    register: Callable[[DataStorageProvider], None],
) -> None:
    """Register both memory and SQLite-based data storage providers for development."""
    register(memory_provider)
    register(sqlite_provider)
