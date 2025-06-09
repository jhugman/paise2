# ABOUTME: Tests for configuration integration with plugin system
# ABOUTME: Validates plugin registration, singleton creation, and configuration access

from __future__ import annotations

from unittest.mock import Mock

import pytest

from paise2.config.manager import ConfigurationManager, MergedConfiguration
from paise2.plugins.core.interfaces import ConfigurationProvider
from paise2.plugins.core.registry import PluginManager


class MockConfigurationProvider(ConfigurationProvider):
    """Mock configuration provider for testing."""

    def __init__(self, config_data: str, config_id: str = "test_config"):
        self._config_data = config_data
        self._config_id = config_id

    def get_default_configuration(self) -> str:
        return self._config_data

    def get_configuration_id(self) -> str:
        return self._config_id


class TestConfigurationProviderRegistration:
    """Test configuration provider registration with plugin system."""

    def test_plugin_manager_accepts_configuration_provider(self):
        """Test that plugin manager can register configuration providers."""
        manager = PluginManager()
        provider = MockConfigurationProvider("test: value")

        # Test registration through the manager's public API
        success = manager.register_configuration_provider(provider)
        assert success

        providers = manager.get_configuration_providers()
        assert len(providers) == 1
        assert providers[0] is provider

    def test_get_configuration_providers(self):
        """Test getting registered configuration providers."""
        manager = PluginManager()
        provider1 = MockConfigurationProvider("config1: value1", "config1")
        provider2 = MockConfigurationProvider("config2: value2", "config2")

        # Register multiple providers
        manager.register_configuration_provider(provider1)
        manager.register_configuration_provider(provider2)

        providers = manager.get_configuration_providers()
        assert len(providers) == 2
        assert provider1 in providers
        assert provider2 in providers

    def test_configuration_provider_validation(self):
        """Test that configuration providers are validated."""
        manager = PluginManager()

        # Valid provider should not raise
        valid_provider = MockConfigurationProvider("test: value")
        manager.validate_configuration_provider(valid_provider)

        # Invalid provider should raise
        invalid_provider = Mock()
        del invalid_provider.get_default_configuration  # Remove required method

        with pytest.raises(AttributeError):
            manager.validate_configuration_provider(invalid_provider)


class TestConfigurationSingletonCreation:
    """Test configuration singleton creation logic."""

    def test_create_configuration_from_providers(self):
        """Test creating configuration singleton from providers."""
        # Setup providers
        provider1 = MockConfigurationProvider(
            "plugin1:\n  setting1: value1\n  setting2: default2"
        )
        provider2 = MockConfigurationProvider(
            "plugin1:\n  setting2: value2\nplugin2:\n  setting3: value3"
        )

        providers = [provider1, provider2]

        # Create configuration manager and merge
        config_manager = ConfigurationManager()

        # Parse YAML configs from providers
        import yaml

        config_dicts = []
        for provider in providers:
            config_data = yaml.safe_load(provider.get_default_configuration())
            if config_data:
                config_dicts.append(config_data)

        # Merge configurations
        merged_config = config_manager.merge_plugin_configurations(config_dicts)
        configuration = MergedConfiguration(merged_config)

        # Test merged configuration
        assert configuration.get("plugin1.setting1") == "value1"
        assert configuration.get("plugin1.setting2") == "value2"  # Later provider wins
        assert configuration.get("plugin2.setting3") == "value3"

    def test_create_configuration_with_user_overrides(self):
        """Test configuration creation with user overrides."""
        # Plugin default config
        provider = MockConfigurationProvider("app:\n  debug: false\n  timeout: 30")

        # User override config
        user_config = {
            "app": {
                "debug": True,  # Override
                "max_connections": 100,  # New setting
            }
        }

        # Create configuration
        config_manager = ConfigurationManager()

        import yaml

        plugin_config = yaml.safe_load(provider.get_default_configuration())

        # Merge with user overrides
        merged_config = config_manager.merge_with_user_overrides(
            plugin_config or {}, user_config
        )
        configuration = MergedConfiguration(merged_config)

        # Test values
        assert configuration.get("app.debug") is True  # User override
        assert configuration.get("app.timeout") == 30  # Plugin default kept
        assert configuration.get("app.max_connections") == 100  # User addition


class TestBaseHostConfigurationAccess:
    """Test configuration access through BaseHost."""

    def test_base_host_has_configuration_property(self):
        """Test that BaseHost provides configuration access."""
        from paise2.plugins.core.hosts import BaseHost

        # Mock dependencies
        mock_logger = Mock()
        mock_config = Mock()
        mock_state_storage = Mock()

        # Create BaseHost
        host = BaseHost(
            logger=mock_logger,
            configuration=mock_config,
            state_storage=mock_state_storage,
            plugin_module_name="test.plugin",
        )

        # Test configuration access
        assert host.configuration is mock_config

    def test_base_host_configuration_access_patterns(self):
        """Test common configuration access patterns through BaseHost."""
        from paise2.plugins.core.hosts import BaseHost

        # Create configuration with test data
        config_data = {
            "plugin": {"setting1": "value1", "setting2": 42},
            "global": {"debug": True},
        }
        configuration = MergedConfiguration(config_data)

        # Mock other dependencies
        mock_logger = Mock()
        mock_state_storage = Mock()

        # Create BaseHost
        host = BaseHost(
            logger=mock_logger,
            configuration=configuration,
            state_storage=mock_state_storage,
            plugin_module_name="test.plugin",
        )

        # Test configuration access patterns
        assert host.configuration.get("plugin.setting1") == "value1"
        assert host.configuration.get("plugin.setting2") == 42
        assert host.configuration.get("global.debug") is True
        assert host.configuration.get("nonexistent.key", "default") == "default"

        # Test section access
        plugin_section = host.configuration.get_section("plugin")
        assert plugin_section["setting1"] == "value1"
        assert plugin_section["setting2"] == 42
