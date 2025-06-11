# ABOUTME: State storage package for plugin state persistence.
# ABOUTME: Provides implementations of StateStorage and StateStorageProvider protocols.

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
