# ABOUTME: Test profile plugins - memory-only providers for fast testing
# ABOUTME: Provides only memory-based data storage for unit tests and CI

from typing import Callable

from paise2.plugins.core.interfaces import DataStorageProvider
from paise2.plugins.core.registry import hookimpl
from paise2.storage.providers import MemoryDataStorageProvider


@hookimpl
def register_data_storage_provider(
    register: Callable[[DataStorageProvider], None],
) -> None:
    """Register the memory-based data storage provider for testing."""
    register(MemoryDataStorageProvider())
