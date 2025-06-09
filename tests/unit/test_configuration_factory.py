# ABOUTME: Tests for configuration factory functionality
# ABOUTME: Tests configuration creation patterns and plugin integration

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import Mock

import yaml

from paise2.config.factory import ConfigurationFactory
from paise2.config.manager import ConfigurationManager
from paise2.plugins.core.interfaces import ConfigurationProvider
from paise2.plugins.core.registry import PluginManager


class MockConfigProvider(ConfigurationProvider):
    """Mock configuration provider for testing."""

    def __init__(self, config_yaml: str, config_id: str = "test"):
        self._config_yaml = config_yaml
        self._config_id = config_id

    def get_default_configuration(self) -> str:
        return self._config_yaml

    def get_configuration_id(self) -> str:
        return self._config_id


class TestConfigurationFactory:
    """Test configuration factory functionality."""

    def test_configuration_factory_creation(self):
        """Test basic configuration factory creation."""
        factory = ConfigurationFactory()
        assert factory is not None

    def test_configuration_factory_with_custom_manager(self):
        """Test configuration factory with custom configuration manager."""
        custom_manager = ConfigurationManager()
        factory = ConfigurationFactory(custom_manager)
        assert factory is not None

    def test_create_configuration_from_plugins_only(self):
        """Test creating configuration from plugins without user overrides."""
        # Setup
        plugin_manager = PluginManager()
        provider1 = MockConfigProvider(
            "app:\n  name: TestApp\n  version: 1.0", "provider1"
        )
        provider2 = MockConfigProvider(
            "app:\n  debug: false\nfeatures:\n  - auth\n  - logging", "provider2"
        )

        plugin_manager.register_configuration_provider(provider1)
        plugin_manager.register_configuration_provider(provider2)

        # Create configuration
        factory = ConfigurationFactory()
        config = factory.create_configuration(plugin_manager)

        # Test merged configuration
        assert config.get("app.name") == "TestApp"
        assert config.get("app.version") == 1.0
        assert config.get("app.debug") is False
        assert config.get("features") == ["auth", "logging"]

    def test_create_configuration_with_user_dict_override(self):
        """Test creating configuration with user dictionary overrides."""
        # Setup plugins
        plugin_manager = PluginManager()
        provider = MockConfigProvider(
            "app:\n  debug: false\n  timeout: 30\nlogging:\n  level: INFO"
        )
        plugin_manager.register_configuration_provider(provider)

        # User overrides
        user_config = {
            "app": {"debug": True, "port": 8080},
            "logging": {"level": "DEBUG"},
        }

        # Create configuration
        factory = ConfigurationFactory()
        config = factory.create_configuration(
            plugin_manager, user_config_dict=user_config
        )

        # Test merged values
        assert config.get("app.debug") is True  # User override
        assert config.get("app.timeout") == 30  # Plugin default
        assert config.get("app.port") == 8080  # User addition
        assert config.get("logging.level") == "DEBUG"  # User override

    def test_create_configuration_with_file_override(self):
        """Test creating configuration with user configuration file."""
        # Setup plugins
        plugin_manager = PluginManager()
        provider = MockConfigProvider("database:\n  host: localhost\n  timeout: 5000")
        plugin_manager.register_configuration_provider(provider)

        # Create temporary config file
        user_config_data = {"database": {"host": "prod-server", "pool_size": 10}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(user_config_data, f)
            config_file_path = f.name

        try:
            # Create configuration
            factory = ConfigurationFactory()
            config = factory.create_configuration(
                plugin_manager, config_file_path=config_file_path
            )

            # Test merged values
            assert config.get("database.host") == "prod-server"  # File override
            assert config.get("database.timeout") == 5000  # Plugin default
            assert config.get("database.pool_size") == 10  # File addition

        finally:
            Path(config_file_path).unlink()

    def test_user_dict_takes_precedence_over_file(self):
        """Test that user dictionary takes precedence over configuration file."""
        # Setup plugins
        plugin_manager = PluginManager()
        provider = MockConfigProvider("app:\n  name: DefaultApp")
        plugin_manager.register_configuration_provider(provider)

        # Create config file
        file_config = {"app": {"name": "FileApp"}}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(file_config, f)
            config_file_path = f.name

        # User dict config (should win)
        dict_config = {"app": {"name": "DictApp"}}

        try:
            factory = ConfigurationFactory()
            config = factory.create_configuration(
                plugin_manager,
                user_config_dict=dict_config,
                config_file_path=config_file_path,
            )

            # Dictionary should take precedence
            assert config.get("app.name") == "DictApp"

        finally:
            Path(config_file_path).unlink()

    def test_configuration_factory_handles_invalid_yaml(self):
        """Test that factory handles invalid YAML gracefully."""
        plugin_manager = PluginManager()

        # Provider with invalid YAML
        invalid_provider = MockConfigProvider("invalid: yaml: content: ::::")
        # Provider with valid YAML
        valid_provider = MockConfigProvider("app:\n  name: ValidApp")

        plugin_manager.register_configuration_provider(invalid_provider)
        plugin_manager.register_configuration_provider(valid_provider)

        factory = ConfigurationFactory()
        config = factory.create_configuration(plugin_manager)

        # Should still work with valid provider
        assert config.get("app.name") == "ValidApp"

    def test_configuration_factory_handles_missing_config_file(self):
        """Test that factory handles missing configuration file gracefully."""
        plugin_manager = PluginManager()
        provider = MockConfigProvider("app:\n  name: TestApp")
        plugin_manager.register_configuration_provider(provider)

        factory = ConfigurationFactory()
        config = factory.create_configuration(
            plugin_manager, config_file_path="/nonexistent/config.yaml"
        )

        # Should use plugin config only
        assert config.get("app.name") == "TestApp"

    def test_configuration_factory_empty_plugin_manager(self):
        """Test factory with empty plugin manager."""
        plugin_manager = PluginManager()  # No providers registered

        factory = ConfigurationFactory()
        config = factory.create_configuration(plugin_manager)

        # Should return empty configuration
        assert config.get("any.key", "default") == "default"


class TestConfigurationFactoryIntegration:
    """Test configuration factory integration patterns."""

    def test_application_configuration_setup_pattern(self):
        """Test typical application configuration setup pattern."""

        def setup_application_configuration(config_file_path: str | None = None):
            """Typical application setup function."""
            # 1. Create plugin manager and discover plugins
            plugin_manager = PluginManager()
            plugin_manager.discover_plugins()
            plugin_manager.load_plugins()

            # 2. Create configuration factory
            factory = ConfigurationFactory()

            # 3. Create application configuration
            return factory.create_configuration(
                plugin_manager, config_file_path=config_file_path
            )

        # Mock a plugin for testing
        plugin_manager = PluginManager()
        provider = MockConfigProvider("app:\n  initialized: true")
        plugin_manager.register_configuration_provider(provider)

        # Create factory and configuration
        factory = ConfigurationFactory()
        config = factory.create_configuration(plugin_manager)

        assert config.get("app.initialized") is True

    def test_configuration_factory_with_host_creation(self):
        """Test using configuration factory with host creation."""
        from paise2.plugins.core.hosts import BaseHost

        # Setup configuration
        plugin_manager = PluginManager()
        provider = MockConfigProvider("host:\n  timeout: 5000\n  retries: 3")
        plugin_manager.register_configuration_provider(provider)

        factory = ConfigurationFactory()
        config = factory.create_configuration(plugin_manager)

        # Create host with configuration
        host = BaseHost(
            logger=Mock(),
            configuration=config,
            state_storage=Mock(),
            plugin_module_name="test.plugin",
        )

        # Verify host can access configuration
        assert host.configuration.get("host.timeout") == 5000
        assert host.configuration.get("host.retries") == 3
