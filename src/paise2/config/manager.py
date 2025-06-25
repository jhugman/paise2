# ABOUTME: Configuration manager for merging and managing plugin configurations
# ABOUTME: Provides ConfigurationManager for handling plugin defaults and user overrides

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from paise2.plugins.core.interfaces import Configuration, StateStorage

    from .models import ConfigurationDict

__all__ = ["ConfigurationManager"]


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
        self,
        plugin_config: ConfigurationDict,
        user_config: ConfigurationDict,
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

    def merge_with_user_overrides(
        self, plugin_config: ConfigurationDict, user_config: ConfigurationDict
    ) -> ConfigurationDict:
        """
        Merge plugin configuration with user overrides.

        This is an alias for merge_configurations for backward compatibility.

        Args:
            plugin_config: Plugin default configuration
            user_config: User override configuration

        Returns:
            Merged configuration with user overrides taking precedence
        """
        return self.merge_configurations(plugin_config, user_config)

    def get_config_dir(self) -> str:
        """
        Get the configuration directory from PAISE_CONFIG_DIR environment variable.

        Returns:
            Configuration directory path with user home expansion
        """
        config_dir = os.environ.get("PAISE_CONFIG_DIR", "~/.config/paise2")
        return str(Path(config_dir).expanduser())

    def get_config_file(self, config_id: str) -> str:
        return str(Path(self.get_config_dir()) / f"{config_id}.yaml")

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

    def create_configuration_with_diffing(
        self,
        current_config: ConfigurationDict,
        state_storage: StateStorage,
    ) -> Configuration:
        """
        Create configuration with startup diffing support.

        Compares current configuration against previous run's configuration
        and creates an annotated configuration with diff information.

        Args:
            current_config: Current merged configuration
            state_storage: State storage for retrieving/storing previous config

        Returns:
            Configuration instance with diff information
        """
        from .diffing import ConcreteConfiguration, ConfigurationDiffer

        # Load previous configuration from state storage
        previous_config = self._load_previous_configuration(state_storage)

        # Calculate diff between previous and current
        diff = None
        if previous_config:
            diff = ConfigurationDiffer.calculate_diff(previous_config, current_config)

        # Save current configuration for next startup
        self._save_current_configuration(state_storage, current_config)

        # Create configuration with diff annotation
        return ConcreteConfiguration(current_config, diff)

    def _load_previous_configuration(
        self, state_storage: StateStorage
    ) -> ConfigurationDict | None:
        """
        Load the previous configuration from state storage.

        Args:
            state_storage: State storage instance

        Returns:
            Previous configuration dictionary or None if not found
        """
        system_partition = "_system.configuration"
        config_key = "last_merged"

        config = state_storage.get(system_partition, config_key)
        if config and isinstance(config, dict):
            return config

        return None

    def _save_current_configuration(
        self, state_storage: StateStorage, config: ConfigurationDict
    ) -> None:
        """
        Save the current configuration to state storage for next startup.

        Args:
            state_storage: State storage instance
            config: Current configuration to save
        """
        system_partition = "_system.configuration"
        config_key = "last_merged"

        # Store configuration directly (state storage should handle serialization)
        state_storage.store(system_partition, config_key, config, version=1)
