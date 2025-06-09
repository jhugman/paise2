# ABOUTME: Configuration manager for merging and managing plugin configurations
# ABOUTME: Provides ConfigurationManager for handling plugin defaults and user overrides

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, cast

import yaml

from .models import Configuration, ConfigurationDict

__all__ = ["ConfigurationManager", "MergedConfiguration"]


class MergedConfiguration(Configuration):
    """
    Implementation of Configuration protocol that provides merged configuration access.

    Supports dotted path access and section-based retrieval from merged
    configuration data.
    """

    def __init__(self, config_data: ConfigurationDict):
        """
        Initialize with merged configuration data.

        Args:
            config_data: Merged configuration dictionary
        """
        self._config_data = config_data

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
            Dictionary containing section configuration
        """
        return cast("ConfigurationDict", self._config_data.get(section, {}))


class ConfigurationManager:
    """
    Manager for merging plugin configurations and user overrides.

    Handles configuration merging with specific rules:
    - Scalar values: last wins (override)
    - Lists: concatenate all values
    - Dictionaries: recursive merge
    """

    def __init__(self) -> None:
        """Initialize ConfigurationManager."""

    def merge_plugin_configurations(
        self, configs: list[ConfigurationDict | None]
    ) -> ConfigurationDict:
        """
        Merge multiple plugin configurations.

        Args:
            configs: List of configuration dictionaries (may contain None values)

        Returns:
            Merged configuration dictionary
        """
        if not configs:
            return {}

        # Filter out None values
        valid_configs = [config for config in configs if config is not None]

        if not valid_configs:
            return {}

        # Start with first config
        result = self._deep_copy_dict(valid_configs[0])

        # Merge subsequent configs
        for config in valid_configs[1:]:
            result = self._merge_dicts(result, config)

        return result

    def merge_configurations(
        self, plugin_config: ConfigurationDict, user_config: ConfigurationDict
    ) -> ConfigurationDict:
        """
        Merge plugin defaults with user overrides.

        User configuration completely overrides plugin configuration for same keys.

        Args:
            plugin_config: Plugin default configuration
            user_config: User override configuration

        Returns:
            Merged configuration with user overrides taking precedence
        """
        result = self._deep_copy_dict(plugin_config)
        return self._merge_dicts(result, user_config)

    def get_config_dir(self) -> str:
        """
        Get the configuration directory from PAISE_CONFIG_DIR environment variable.

        Returns:
            Configuration directory path with user home expansion
        """
        config_dir = os.environ.get("PAISE_CONFIG_DIR", "~/.config/paise2")
        return str(Path(config_dir).expanduser())

    def load_configuration_file(self, file_path: str) -> ConfigurationDict:
        """
        Load configuration from a YAML file.

        Args:
            file_path: Path to YAML configuration file

        Returns:
            Configuration dictionary

        Raises:
            Exception: If YAML is invalid or file cannot be read
        """
        try:
            path = Path(file_path)
            with path.open(encoding="utf-8") as f:
                data = yaml.safe_load(f)
                return data if data is not None else {}
        except yaml.YAMLError as e:
            msg = f"Invalid YAML in {file_path}: {e}"
            raise yaml.YAMLError(msg) from e
        except OSError as e:
            msg = f"Cannot read configuration file {file_path}: {e}"
            raise OSError(msg) from e

    def _merge_dicts(
        self, dict1: ConfigurationDict, dict2: ConfigurationDict
    ) -> ConfigurationDict:
        """
        Recursively merge two dictionaries with specific merging rules.

        Args:
            dict1: Base dictionary
            dict2: Dictionary to merge into base

        Returns:
            Merged dictionary
        """
        result = dict1.copy()

        for key, value in dict2.items():
            if key not in result:
                # New key, just add it
                result[key] = self._deep_copy_value(value)
            else:
                existing_value = result[key]

                # Apply merging rules based on type
                if isinstance(existing_value, dict) and isinstance(value, dict):
                    # Recursive dictionary merge
                    result[key] = self._merge_dicts(existing_value, value)
                elif isinstance(existing_value, list) and isinstance(value, list):
                    # List concatenation
                    result[key] = existing_value + value
                else:
                    # Scalar override - last wins
                    result[key] = self._deep_copy_value(value)

        return result

    def _deep_copy_dict(self, d: ConfigurationDict) -> ConfigurationDict:
        """
        Create a deep copy of a configuration dictionary.

        Args:
            d: Dictionary to copy

        Returns:
            Deep copy of dictionary
        """
        result = {}
        for key, value in d.items():
            result[key] = self._deep_copy_value(value)
        return result

    def _deep_copy_value(self, value: Any) -> Any:
        """
        Create a deep copy of a configuration value.

        Args:
            value: Value to copy

        Returns:
            Deep copy of value
        """
        if isinstance(value, dict):
            return self._deep_copy_dict(value)
        if isinstance(value, list):
            return [self._deep_copy_value(item) for item in value]
        return value
