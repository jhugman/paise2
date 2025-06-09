# ABOUTME: Tests for configuration singleton creation and integration with hosts
# ABOUTME: Tests configuration factory patterns and host configuration injection

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import Mock

import yaml

from paise2.config.manager import ConfigurationManager, MergedConfiguration
from paise2.plugins.core.interfaces import ConfigurationProvider
from paise2.plugins.core.registry import PluginManager

if TYPE_CHECKING:
    from paise2.config.models import Configuration


class MockConfigProvider(ConfigurationProvider):
    """Mock configuration provider for testing."""

    def __init__(self, config_data: str, config_id: str = "test_config"):
        self._config_data = config_data
        self._config_id = config_id

    def get_default_configuration(self) -> str:
        return self._config_data

    def get_configuration_id(self) -> str:
        return self._config_id


class TestConfigurationSingleton:
    """Test configuration singleton creation and management."""

    def test_create_configuration_singleton_from_plugins(self):
        """Test creating a single configuration instance from multiple providers."""
        # Setup plugin manager with providers
        plugin_manager = PluginManager()

        provider1 = MockConfigProvider(
            "app:\n  name: MyApp\n  version: 1.0\n"
            "plugin1:\n  enabled: true\n  timeout: 30"
        )
        provider2 = MockConfigProvider(
            "app:\n  debug: false\nplugin2:\n  max_connections: 100\n  retries: 3"
        )

        # Register providers
        plugin_manager.register_configuration_provider(provider1)
        plugin_manager.register_configuration_provider(provider2)

        # Create configuration singleton
        config_manager = ConfigurationManager()
        providers = plugin_manager.get_configuration_providers()

        # Parse and merge configurations
        config_dicts = []
        for provider in providers:
            config_data = yaml.safe_load(provider.get_default_configuration())
            if config_data:
                config_dicts.append(config_data)

        merged_config = config_manager.merge_plugin_configurations(config_dicts)
        configuration = MergedConfiguration(merged_config)

        # Test the singleton configuration
        assert configuration.get("app.name") == "MyApp"
        assert configuration.get("app.version") == 1.0
        assert configuration.get("app.debug") is False
        assert configuration.get("plugin1.enabled") is True
        assert configuration.get("plugin1.timeout") == 30
        assert configuration.get("plugin2.max_connections") == 100
        assert configuration.get("plugin2.retries") == 3

    def test_configuration_singleton_with_user_overrides(self):
        """Test configuration singleton creation with user configuration file."""
        # Plugin configuration
        plugin_manager = PluginManager()
        provider = MockConfigProvider(
            "app:\n  debug: false\n  timeout: 30\n"
            "logging:\n  level: INFO\n  format: basic"
        )
        plugin_manager.register_configuration_provider(provider)

        # User configuration (simulates loaded from config file)
        user_config = {
            "app": {
                "debug": True,  # Override
                "port": 8080,  # New setting
            },
            "logging": {
                "level": "DEBUG"  # Override
            },
        }

        # Create configuration with overrides
        config_manager = ConfigurationManager()
        providers = plugin_manager.get_configuration_providers()

        # Parse plugin configs
        plugin_config_data = yaml.safe_load(providers[0].get_default_configuration())

        # Merge with user overrides
        merged_config = config_manager.merge_with_user_overrides(
            plugin_config_data, user_config
        )
        configuration = MergedConfiguration(merged_config)

        # Test merged values
        assert configuration.get("app.debug") is True  # User override
        assert configuration.get("app.timeout") == 30  # Plugin default kept
        assert configuration.get("app.port") == 8080  # User addition
        assert configuration.get("logging.level") == "DEBUG"  # User override
        assert configuration.get("logging.format") == "basic"  # Plugin default kept

    def test_configuration_factory_pattern(self):
        """Test factory pattern for configuration creation."""

        def create_application_configuration(
            plugin_manager: PluginManager, user_config_dict: dict | None = None
        ) -> Configuration:
            """Factory function to create application configuration."""
            config_manager = ConfigurationManager()
            providers = plugin_manager.get_configuration_providers()

            # Merge plugin configurations
            plugin_configs = []
            for provider in providers:
                config_data = yaml.safe_load(provider.get_default_configuration())
                if config_data:
                    plugin_configs.append(config_data)

            merged_plugins = config_manager.merge_plugin_configurations(plugin_configs)

            # Apply user overrides if provided
            if user_config_dict:
                final_config = config_manager.merge_with_user_overrides(
                    merged_plugins, user_config_dict
                )
            else:
                final_config = merged_plugins

            return MergedConfiguration(final_config)

        # Test the factory
        plugin_manager = PluginManager()
        provider = MockConfigProvider("test:\n  value: default")
        plugin_manager.register_configuration_provider(provider)

        # Without user config
        config1 = create_application_configuration(plugin_manager)
        assert config1.get("test.value") == "default"

        # With user config
        user_overrides = {"test": {"value": "overridden"}}
        config2 = create_application_configuration(plugin_manager, user_overrides)
        assert config2.get("test.value") == "overridden"


class TestHostConfigurationIntegration:
    """Test configuration integration with host creation."""

    def test_host_factory_with_configuration_injection(self):
        """Test host factory that injects configuration dependency."""
        from paise2.plugins.core.hosts import BaseHost

        def create_host_with_config(
            plugin_module_name: str,
            configuration: Configuration,
            logger=None,
            state_storage=None,
        ) -> BaseHost:
            """Factory to create host with configuration dependency injection."""
            return BaseHost(
                logger=logger or Mock(),
                configuration=configuration,
                state_storage=state_storage or Mock(),
                plugin_module_name=plugin_module_name,
            )

        # Create configuration
        config_data = {"plugin": {"setting": "value"}}
        configuration = MergedConfiguration(config_data)

        # Create host with injected configuration
        host = create_host_with_config("test.plugin", configuration)

        # Verify configuration is accessible
        assert host.configuration is configuration
        assert host.configuration.get("plugin.setting") == "value"

    def test_multiple_hosts_share_same_configuration(self):
        """Test that multiple hosts can share the same configuration singleton."""
        from paise2.plugins.core.hosts import BaseHost

        # Create single configuration instance
        config_data = {
            "global": {"debug": True, "timeout": 60},
            "plugin1": {"enabled": True},
            "plugin2": {"max_size": 1000},
        }
        configuration = MergedConfiguration(config_data)

        # Create multiple hosts with same configuration
        host1 = BaseHost(
            logger=Mock(),
            configuration=configuration,
            state_storage=Mock(),
            plugin_module_name="plugin1",
        )

        host2 = BaseHost(
            logger=Mock(),
            configuration=configuration,
            state_storage=Mock(),
            plugin_module_name="plugin2",
        )

        # Verify they share the same configuration instance
        assert host1.configuration is configuration
        assert host2.configuration is configuration
        assert host1.configuration is host2.configuration

        # Verify they can access their respective plugin sections
        assert host1.configuration.get("plugin1.enabled") is True
        assert host2.configuration.get("plugin2.max_size") == 1000

        # Verify they can access global configuration
        assert host1.configuration.get("global.debug") is True
        assert host2.configuration.get("global.timeout") == 60
