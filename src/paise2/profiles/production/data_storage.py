# ABOUTME: Production profile plugins - persistent storage providers
# ABOUTME: Provides SQLite-based storage providers for production environments

from typing import Callable

from paise2.plugins.core.interfaces import DataStorageProvider
from paise2.plugins.core.registry import hookimpl
from paise2.storage.providers import SQLiteDataStorageProvider


@hookimpl
def register_data_storage_provider(
    register: Callable[[DataStorageProvider], None],
) -> None:
    """Register the SQLite-based data storage provider for production."""
    register(SQLiteDataStorageProvider())
