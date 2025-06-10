# ABOUTME: State storage package for plugin state persistence.
# ABOUTME: Provides implementations of StateStorage and StateStorageProvider protocols.

# Import registration functions to ensure they're discoverable
from . import plugin_registration  # noqa: F401
from .models import StateEntry
from .providers import (
    FileStateStorage,
    FileStateStorageProvider,
    MemoryStateStorage,
    MemoryStateStorageProvider,
)

__all__ = [
    "FileStateStorage",
    "FileStateStorageProvider",
    "MemoryStateStorage",
    "MemoryStateStorageProvider",
    "StateEntry",
]
