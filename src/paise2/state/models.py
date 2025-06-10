"""ABOUTME: Data models for state storage system.
ABOUTME: Defines core data structures for persisting plugin state with versioning."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class StateEntry:
    """
    Represents a versioned state entry.

    Immutable data structure for storing plugin state with version information
    for migration support.
    """

    partition_key: str
    key: str
    value: Any
    version: int = 1

    def with_value(self, new_value: Any) -> StateEntry:
        """Create a new StateEntry with updated value, preserving other fields."""
        return StateEntry(
            partition_key=self.partition_key,
            key=self.key,
            value=new_value,
            version=self.version,
        )

    def with_version(self, new_version: int) -> StateEntry:
        """Create a new StateEntry with updated version, preserving other fields."""
        return StateEntry(
            partition_key=self.partition_key,
            key=self.key,
            value=self.value,
            version=new_version,
        )
