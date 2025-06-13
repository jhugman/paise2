# ABOUTME: Core data models for the PAISE2 plugin system
# ABOUTME: Defines immutable data structures used throughout the system

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any, Union

if TYPE_CHECKING:
    from datetime import datetime
    from pathlib import Path

# Type aliases for system identifiers
ItemId = str
JobId = str
CacheId = str

# Content type alias
Content = Union[bytes, str]


@dataclass(frozen=True)
class Metadata:
    """Immutable metadata for content items.

    This class represents metadata for a content item in the PAISE2 system.
    It supports immutable operations via copy() and merge() methods.
    """

    source_url: str  # A natural or synthetic URL
    location: CacheId | Path | None = None
    title: str | None = None
    parent_id: ItemId | None = None  # For hierarchical content
    description: str | None = None
    processing_state: str = "pending"  # For resumability
    indexed_at: datetime | None = None
    created_at: datetime | None = None
    modified_at: datetime | None = None
    author: str | None = None
    tags: list[str] = field(default_factory=list)
    mime_type: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def copy(self, **changes: Any) -> Metadata:
        """Create a new Metadata instance with specified changes.

        Args:
            **changes: Fields to change in the new instance

        Returns:
            New Metadata instance with changes applied
        """
        current_dict = asdict(self)
        current_dict.update(changes)
        return Metadata(**current_dict)

    def merge(self, patch: Metadata) -> Metadata:
        """Create a new Metadata instance merged with patch.

        Merge rules:
        - Scalar values: patch overrides base (unless patch value is None)
        - Lists: concatenated (base + patch)
        - Dicts: recursively merged

        Args:
            patch: Metadata instance to merge with this one

        Returns:
            New Metadata instance with patch applied
        """
        current_dict = asdict(self)
        patch_dict = asdict(patch)

        merged = {}
        all_keys = set(current_dict.keys()) | set(patch_dict.keys())

        for key in all_keys:
            current_value = current_dict.get(key)
            patch_value = patch_dict.get(key)

            if patch_value is None:
                # None in patch doesn't override base value
                merged[key] = current_value
            elif (
                key in current_dict
                and isinstance(current_value, list)
                and isinstance(patch_value, list)
            ):
                # Lists are concatenated
                merged[key] = current_value + patch_value
            elif (
                key in current_dict
                and isinstance(current_value, dict)
                and isinstance(patch_value, dict)
            ):
                # Dicts are recursively merged
                merged[key] = self._merge_dicts(current_value, patch_value)
            else:
                # Scalar values: patch overrides base
                merged[key] = patch_value

        # Type ignore needed due to mypy's strict dict unpacking rules
        return Metadata(**merged)  # type: ignore[arg-type]

    def _merge_dicts(
        self, base: dict[str, Any], patch: dict[str, Any]
    ) -> dict[str, Any]:
        """Recursively merge two dictionaries.

        Args:
            base: Base dictionary
            patch: Patch dictionary to merge into base

        Returns:
            Merged dictionary
        """
        merged = base.copy()

        for key, patch_value in patch.items():
            if (
                key in merged
                and isinstance(merged[key], dict)
                and isinstance(patch_value, dict)
            ):
                # Recursively merge nested dicts
                merged[key] = self._merge_dicts(merged[key], patch_value)
            else:
                # Override with patch value
                merged[key] = patch_value

        return merged
