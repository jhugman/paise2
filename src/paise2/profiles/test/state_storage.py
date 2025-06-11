# ABOUTME: Test profile plugins - memory-only providers for fast testing
# ABOUTME: Provides only memory-based storage for unit tests and CI

from typing import Callable

from paise2.plugins.core.interfaces import StateStorageProvider
from paise2.plugins.core.registry import hookimpl
from paise2.state.providers import MemoryStateStorageProvider


@hookimpl
def register_state_storage_provider(
    register: Callable[[StateStorageProvider], None],
) -> None:
    """Register the memory-based state storage provider for testing."""
    register(MemoryStateStorageProvider())
