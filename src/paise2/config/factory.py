# ABOUTME: Configuration factory for creating application-wide configuration singletons
# ABOUTME: Integrates plugin manager with configuration system for complete setup

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import yaml

from .diffing import ConcreteConfiguration
from .manager import ConfigurationManager

if TYPE_CHECKING:
    from paise2.plugins.core.interfaces import Configuration
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
            plugin_configs  # type: ignore[arg-type]
        )

        # Step 3: Apply user overrides if provided
        final_config = self._apply_user_overrides(
            merged_plugins, user_config_dict, config_file_path
        )

        # Step 4: Create configuration instance
        return ConcreteConfiguration(final_config)

    def _collect_plugin_configurations(
        self, plugin_manager: PluginManager
    ) -> list[ConfigurationDict]:
        """
        Collect configuration dictionaries from all registered providers.

        Args:
            plugin_manager: Plugin manager with configuration providers

        Returns:
            List of parsed configuration dictionaries
        """
        providers = plugin_manager.get_configuration_providers()
        config_dicts: list[ConfigurationDict] = []

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
            try:
                user_config = self._config_manager.load_configuration_file(
                    config_file_path
                )
                return self._config_manager.merge_with_user_overrides(
                    plugin_config, user_config
                )
            except (OSError, yaml.YAMLError):
                # If file loading fails, return plugin config only
                # This is expected behavior for optional configuration files
                pass

        # No user overrides
        return plugin_config
