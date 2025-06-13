# ABOUTME: Configuration factory for creating application-wide configuration singletons
# ABOUTME: Integrates plugin manager with configuration system for complete setup

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import yaml

from .diffing import ConcreteConfiguration
from .manager import ConfigurationManager

if TYPE_CHECKING:
    from paise2.plugins.core.interfaces import Configuration, StateStorage
    from paise2.plugins.core.registry import PluginManager

    from .models import ConfigurationDict

__all__ = ["ConfigurationFactory"]


class ConfigurationFactory:
    """
    Factory for creating application configuration singletons.

    Handles the complete configuration creation process:
    1. Collects configurations from registered plugins
    2. Merges plugin configurations using defined rules
    3. Applies user configuration overrides
    4. Returns a single Configuration instance for the application
    """

    def __init__(self, config_manager: ConfigurationManager | None = None):
        """
        Initialize configuration factory.

        Args:
            config_manager: Configuration manager instance (creates new if None)
        """
        self._config_manager = config_manager or ConfigurationManager()

    def load_initial_configuration(
        self,
        plugin_manager: PluginManager,
        config_dir: str | None = None,
        user_config_dict: dict[str, Any] | None = None,
    ) -> Configuration:
        """
        Load initial configuration from plugin providers and config directory.

        This is the proper configuration loading sequence:
        1. Collect configurations from registered plugin providers
        2. Merge plugin configurations using defined rules
        3. Load and merge YAML files found in config directory
        4. Apply config directory overrides to plugin defaults
        5. Apply optional user config overrides (for testing)

        Args:
            plugin_manager: Plugin manager with registered configuration providers
            config_dir: Configuration directory path (uses PAISE_CONFIG_DIR if None)
            user_config_dict: Optional user config overrides (primarily for testing)

        Returns:
            Configuration instance with merged settings (without diff information)
        """
        # Step 1: Collect plugin configurations
        plugin_configs = self._collect_plugin_configurations(plugin_manager)

        # Step 2: Merge plugin configurations
        merged_plugins = self._config_manager.merge_plugin_configurations(
            plugin_configs
        )

        # Step 3: Load user configurations from config directory
        if config_dir is None:
            config_dir = self._config_manager.get_config_dir()

        user_config = self._load_config_directory(config_dir)

        # Step 4: Apply user overrides to plugin defaults
        config_with_dir_overrides = self._config_manager.merge_with_user_overrides(
            merged_plugins, user_config
        )

        # Step 5: Apply optional user config dict (for testing)
        if user_config_dict:
            final_config = self._config_manager.merge_with_user_overrides(
                config_with_dir_overrides, user_config_dict
            )
        else:
            final_config = config_with_dir_overrides

        # Step 6: Create configuration instance (without diff)
        return ConcreteConfiguration(final_config)

    def complete_configuration(
        self,
        initial_configuration: Configuration,
        state_storage: StateStorage,
    ) -> Configuration:
        """
        Complete configuration with startup state persistence and change detection.

        Compares current configuration against previous run's configuration
        and creates an annotated configuration with diff information.

        Args:
            initial_configuration: Initial configuration to complete
            state_storage: State storage for retrieving/storing previous config

        Returns:
            Configuration instance with diff information from previous run
        """
        # Extract configuration data for comparison
        # Since we need all sections, access the underlying data from
        # ConcreteConfiguration
        from .diffing import ConcreteConfiguration

        if isinstance(initial_configuration, ConcreteConfiguration):
            # Access the complete configuration data directly
            current_config = initial_configuration._config_data  # noqa: SLF001
        else:
            # Fallback: try to reconstruct from known sections
            current_config_fallback: dict[str, Any] = {}
            for section in ["app", "logging", "plugins"]:
                section_data = initial_configuration.get_section(section)
                if section_data:
                    current_config_fallback[section] = section_data
            current_config = current_config_fallback

        # Use ConfigurationManager to handle state persistence and diffing
        return self._config_manager.create_configuration_with_diffing(
            current_config, state_storage
        )

    def create_configuration(
        self,
        plugin_manager: PluginManager,
        user_config_dict: dict[str, Any] | None = None,
        config_file_path: str | None = None,
    ) -> Configuration:
        """
        Create application configuration from plugins and user overrides.

        Args:
            plugin_manager: Plugin manager with registered configuration providers
            user_config_dict: User configuration overrides (optional)
            config_file_path: Path to user configuration file (optional)

        Returns:
            Configuration instance with merged plugin and user settings

        Note:
            If both user_config_dict and config_file_path are provided,
            user_config_dict takes precedence.
        """
        # Step 1: Collect plugin configurations
        plugin_configs = self._collect_plugin_configurations(plugin_manager)

        # Step 2: Merge plugin configurations
        merged_plugins = self._config_manager.merge_plugin_configurations(
            plugin_configs
        )

        # Step 3: Apply user overrides if provided
        final_config = self._apply_user_overrides(
            merged_plugins, user_config_dict, config_file_path
        )

        # Step 4: Create configuration instance
        return ConcreteConfiguration(final_config)

    def _collect_plugin_configurations(
        self, plugin_manager: PluginManager
    ) -> list[ConfigurationDict | None]:
        """
        Collect configuration dictionaries from all registered providers.

        Args:
            plugin_manager: Plugin manager with configuration providers

        Returns:
            List of parsed configuration dictionaries
        """
        providers = plugin_manager.get_configuration_providers()
        config_dicts: list[ConfigurationDict | None] = []

        for provider in providers:
            config_yaml = provider.get_default_configuration()
            try:
                config_data = yaml.safe_load(config_yaml)
                if config_data is not None:
                    config_dicts.append(config_data)
            except yaml.YAMLError:
                # Log error but continue with other providers
                continue

        return config_dicts

    def _load_config_directory(self, config_dir: str) -> dict[str, Any]:
        """
        Load and merge all YAML configuration files from a directory.

        Args:
            config_dir: Directory containing configuration files

        Returns:
            Merged configuration from all YAML files in directory
        """
        from pathlib import Path

        config_path = Path(config_dir)
        if not config_path.exists() or not config_path.is_dir():
            return {}

        # Find all YAML files in the directory
        yaml_files = list(config_path.glob("*.yaml")) + list(config_path.glob("*.yml"))

        if not yaml_files:
            return {}

        # Load and merge all configuration files
        config_dicts: list[ConfigurationDict | None] = []
        for yaml_file in sorted(yaml_files):  # Sort for deterministic order
            file_config = self._load_config_file_safe(str(yaml_file))
            if file_config:
                config_dicts.append(file_config)

        # Merge all loaded configurations
        return self._config_manager.merge_plugin_configurations(config_dicts)

    def _load_config_file_safe(self, file_path: str) -> dict[str, Any] | None:
        """
        Safely load a configuration file, returning None on error.

        Args:
            file_path: Path to configuration file

        Returns:
            Configuration dictionary or None if loading fails
        """
        try:
            return self._config_manager.load_configuration_file(file_path)
        except (OSError, yaml.YAMLError):
            # Log error but continue processing
            return None

    def _apply_user_overrides(
        self,
        plugin_config: dict[str, Any],
        user_config_dict: dict[str, Any] | None,
        config_file_path: str | None,
    ) -> dict[str, Any]:
        """
        Apply user configuration overrides to plugin configuration.

        Args:
            plugin_config: Merged plugin configuration
            user_config_dict: User configuration dictionary (optional)
            config_file_path: Path to user configuration file (optional)

        Returns:
            Configuration with user overrides applied
        """
        if user_config_dict:
            # Use provided dictionary
            return self._config_manager.merge_with_user_overrides(
                plugin_config, user_config_dict
            )

        if config_file_path:
            # Load from file
            user_config = self._load_config_file_safe(config_file_path)
            if user_config:
                return self._config_manager.merge_with_user_overrides(
                    plugin_config, user_config
                )

        # No user overrides
        return plugin_config
