# ABOUTME: Enhanced configuration management with diffing and state persistence
# ABOUTME: Provides ConfigurationDiffer for tracking changes and enhanced config

from __future__ import annotations

import copy
from typing import Any

from paise2.plugins.core.interfaces import ConfigurationDiff

from .models import Configuration, ConfigurationDict

__all__ = ["ConfigurationDiffer", "EnhancedMergedConfiguration"]


class ConfigurationDiffer:
    """
    Utility class for calculating differences between configuration states.

    Supports deep comparison of nested dictionaries and lists to provide
    detailed diff information for configuration reload operations.
    """

    @staticmethod
    def calculate_diff(  # noqa: C901, PLR0912
        old_config: ConfigurationDict, new_config: ConfigurationDict
    ) -> ConfigurationDiff:
        """
        Calculate the differences between two configuration states.

        When values change, the old value appears in 'removed' and the new value
        appears in 'added'. This provides a cleaner API than a separate 'modified'
        category.

        Args:
            old_config: Previous configuration state
            new_config: New configuration state

        Returns:
            ConfigurationDiff with added, removed, modified, and unchanged values
        """
        added: dict[str, Any] = {}
        removed: dict[str, Any] = {}
        # Keep for backwards compatibility, but will be empty
        modified: dict[str, Any] = {}
        unchanged: dict[str, Any] = {}

        # Find added and changed keys
        for key, new_value in new_config.items():
            if key not in old_config:
                added[key] = copy.deepcopy(new_value)
            else:
                old_value = old_config[key]
                if ConfigurationDiffer._values_equal(old_value, new_value):
                    unchanged[key] = copy.deepcopy(new_value)
                # For nested dictionaries, calculate nested diff and merge
                elif isinstance(old_value, dict) and isinstance(new_value, dict):
                    nested_diff = ConfigurationDiffer._calculate_nested_diff(
                        old_value, new_value
                    )
                    # Merge nested changes into top-level added/removed
                    if "added" in nested_diff:
                        if key not in added:
                            added[key] = {}
                        added[key].update(nested_diff["added"])
                    if "removed" in nested_diff:
                        if key not in removed:
                            removed[key] = {}
                        removed[key].update(nested_diff["removed"])
                    if "unchanged" in nested_diff:
                        if key not in unchanged:
                            unchanged[key] = {}
                        unchanged[key].update(nested_diff["unchanged"])
                else:
                    # Simple value change: old goes to removed, new goes to added
                    removed[key] = copy.deepcopy(old_value)
                    added[key] = copy.deepcopy(new_value)

        # Find removed keys
        for key, old_value in old_config.items():
            if key not in new_config:
                removed[key] = copy.deepcopy(old_value)

        return ConfigurationDiff(
            added=added, removed=removed, modified=modified, unchanged=unchanged
        )

    @staticmethod
    def _values_equal(value1: Any, value2: Any) -> bool:
        """Check if two configuration values are equal."""
        return bool(value1 == value2)

    @staticmethod
    def _calculate_nested_diff(  # noqa: C901, PLR0912
        old_dict: dict[str, Any], new_dict: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Calculate diff for nested dictionaries.

        Returns a dict with 'added', 'removed', and 'unchanged' sections.
        No 'modified' section - changes are represented as removed + added.
        """
        added: dict[str, Any] = {}
        removed: dict[str, Any] = {}
        unchanged: dict[str, Any] = {}

        # Find added and changed in new_dict
        for key, new_value in new_dict.items():
            if key not in old_dict:
                added[key] = copy.deepcopy(new_value)
            else:
                old_value = old_dict[key]
                if ConfigurationDiffer._values_equal(old_value, new_value):
                    unchanged[key] = copy.deepcopy(new_value)
                elif isinstance(old_value, dict) and isinstance(new_value, dict):
                    # Recursively handle nested dicts
                    nested_diff = ConfigurationDiffer._calculate_nested_diff(
                        old_value, new_value
                    )
                    # Merge nested changes
                    if "added" in nested_diff:
                        if key not in added:
                            added[key] = {}
                        added[key].update(nested_diff["added"])
                    if "removed" in nested_diff:
                        if key not in removed:
                            removed[key] = {}
                        removed[key].update(nested_diff["removed"])
                    if "unchanged" in nested_diff:
                        if key not in unchanged:
                            unchanged[key] = {}
                        unchanged[key].update(nested_diff["unchanged"])
                else:
                    # Value changed: old goes to removed, new goes to added
                    removed[key] = copy.deepcopy(old_value)
                    added[key] = copy.deepcopy(new_value)

        # Find removed in old_dict
        for key, old_value in old_dict.items():
            if key not in new_dict:
                removed[key] = copy.deepcopy(old_value)

        # Only return a diff if there are actual changes
        result = {}
        if added:
            result["added"] = added
        if removed:
            result["removed"] = removed
        if unchanged:
            result["unchanged"] = unchanged

        return result

    @staticmethod
    def has_path_changed(diff: ConfigurationDiff, path: str) -> bool:
        """
        Check if a specific dotted path has changed.

        A path is considered changed if it appears in either added or removed sections.

        Args:
            diff: Configuration diff to check
            path: Dotted path (e.g., 'plugin.setting')

        Returns:
            True if the path changed, False otherwise
        """
        path_parts = path.split(".")

        # Check if path was added or removed
        return ConfigurationDiffer._path_exists_in_dict(
            diff.added, path_parts
        ) or ConfigurationDiffer._path_exists_in_dict(diff.removed, path_parts)

    @staticmethod
    def _path_exists_in_dict(d: dict[str, Any], path_parts: list[str]) -> bool:
        """Check if a dotted path exists in a dictionary."""
        current = d
        for part in path_parts:
            if not isinstance(current, dict) or part not in current:
                return False
            current = current[part]
        return True

    @staticmethod
    def get_path_value_from_diff_dict(
        d: dict[str, Any], path_parts: list[str], default: Any = None
    ) -> Any:
        """Get a value from a diff dictionary using a dotted path."""
        current = d
        for part in path_parts:
            if not isinstance(current, dict) or part not in current:
                return default
            current = current[part]
        return current


class EnhancedMergedConfiguration(Configuration):
    """
    Enhanced implementation of Configuration protocol with diff support.

    Supports configuration diffing, change detection, and provides
    access to added/removed configuration values.
    """

    def __init__(
        self, config_data: ConfigurationDict, diff: ConfigurationDiff | None = None
    ):
        """
        Initialize with merged configuration data and optional diff.

        Args:
            config_data: Merged configuration dictionary
            diff: Optional configuration diff from last reload
        """
        self._config_data = config_data
        self._last_diff = diff

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value by key with optional default.

        Supports dotted path access like 'plugin.section.key'.

        Args:
            key: Configuration key (supports dotted paths)
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        # Handle dotted path access
        keys = key.split(".")
        current = self._config_data

        for k in keys:
            if not isinstance(current, dict) or k not in current:
                return default
            current = current[k]

        return current

    def get_section(self, section: str) -> ConfigurationDict:
        """
        Get an entire configuration section.

        Args:
            section: Section name

        Returns:
            Configuration section as dictionary
        """
        section_data = self._config_data.get(section, {})
        if isinstance(section_data, dict):
            return section_data
        return {}

    def addition(self, key: str, default: Any = None) -> Any:
        """
        Get the additions at the key path from the last configuration reload.

        Args:
            key: Configuration key (can be dotted path like 'plugin.setting')
            default: Default value if no additions exist at that path

        Returns:
            Added configuration value or default
        """
        if not self._last_diff:
            return default

        path_parts = key.split(".")
        return ConfigurationDiffer.get_path_value_from_diff_dict(
            self._last_diff.added, path_parts, default
        )

    def removal(self, key: str, default: Any = None) -> Any:
        """
        Get the removals at the key path from the last configuration reload.

        Args:
            key: Configuration key (can be dotted path like 'plugin.setting')
            default: Default value if no removals exist at that path

        Returns:
            Removed configuration value or default
        """
        if not self._last_diff:
            return default

        path_parts = key.split(".")
        return ConfigurationDiffer.get_path_value_from_diff_dict(
            self._last_diff.removed, path_parts, default
        )

    def has_changed(self, key: str) -> bool:
        """
        Check if a specific configuration key changed in the last reload.

        Args:
            key: Configuration key to check

        Returns:
            True if the key changed, False otherwise
        """
        if not self._last_diff:
            return False

        return ConfigurationDiffer.has_path_changed(self._last_diff, key)

    @property
    def last_diff(self) -> ConfigurationDiff | None:
        """
        Get the last configuration diff from a reload operation.

        Returns:
            ConfigurationDiff object or None if no diff available
        """
        return self._last_diff
