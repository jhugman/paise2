# ABOUTME: Unit tests for worker configuration provider and worker settings validation
# ABOUTME: Tests worker configuration loading, merging, and profile-specific behavior

from __future__ import annotations

import yaml

from paise2.config.factory import ConfigurationFactory
from paise2.config.providers import FileConfigurationProvider
from paise2.plugins.core.interfaces import ConfigurationProvider
from paise2.plugins.core.registry import PluginManager
from paise2.profiles.common.workers.configuration import worker_config_provider


class TestWorkerConfigurationProvider:
    """Test worker configuration provider functionality."""

    def test_worker_configuration_provider_is_file_provider(self) -> None:
        """Test that worker configuration uses FileConfigurationProvider."""
        assert isinstance(worker_config_provider, FileConfigurationProvider)
        assert isinstance(worker_config_provider, ConfigurationProvider)

    def test_worker_configuration_provider_id(self) -> None:
        """Test that provider returns correct configuration ID."""
        config_id = worker_config_provider.get_configuration_id()
        assert config_id == "worker-config.yaml"

    def test_worker_configuration_yaml_structure(self) -> None:
        """Test that worker config YAML has required sections and sensible defaults."""
        config_yaml = worker_config_provider.get_default_configuration()
        config_data = yaml.safe_load(config_yaml)

        # Should be valid YAML
        assert config_data is not None
        assert isinstance(config_data, dict)

        # Should have worker section with expected structure
        assert "worker" in config_data
        worker = config_data["worker"]
        assert worker["concurrency"] == 4  # Reasonable default
        assert worker["retry"]["max_retries"] == 3  # Conservative retry count
        assert worker["retry"]["retry_delay"] == 60  # 1 minute delay
        assert worker["monitoring"]["enable"] is True  # Monitoring enabled

        # Should have task_queue section with expected structure
        assert "task_queue" in config_data
        task_queue = config_data["task_queue"]

        # SQLite config
        sqlite = task_queue["sqlite"]
        assert sqlite["path"] == "~/.local/share/paise2/tasks.db"  # Standard path
        assert sqlite["immediate"] is False  # Queued by default

        # Redis config
        redis = task_queue["redis"]
        assert redis["host"] == "localhost"  # Local redis by default
        assert redis["port"] == 6379  # Standard redis port
        assert redis["db"] == 0  # Default redis database


class TestWorkerConfigurationIntegration:
    """Test worker configuration integration with the plugin system."""

    def test_worker_configuration_can_be_registered(self) -> None:
        """Test that worker config provider can be registered with plugin system."""
        plugin_manager = PluginManager()

        result = plugin_manager.register_configuration_provider(worker_config_provider)
        assert result is True

        registered_providers = plugin_manager.get_configuration_providers()
        assert len(registered_providers) >= 1
        assert any(
            isinstance(p, FileConfigurationProvider) for p in registered_providers
        )

    def test_worker_configuration_integrates_with_config_factory(self) -> None:
        """Test that worker config integrates properly with ConfigurationFactory."""
        plugin_manager = PluginManager()
        plugin_manager.register_configuration_provider(worker_config_provider)

        factory = ConfigurationFactory()
        config = factory.create_configuration(plugin_manager)

        # Should be able to access worker configuration
        assert config.get("worker.concurrency") == 4
        assert config.get("worker.retry.max_retries") == 3
        assert config.get("task_queue.sqlite.path") == "~/.local/share/paise2/tasks.db"

    def test_worker_configuration_supports_user_overrides(self) -> None:
        """Test that worker configuration can be overridden by user config."""
        plugin_manager = PluginManager()
        plugin_manager.register_configuration_provider(worker_config_provider)

        # User overrides
        user_config = {
            "worker": {"concurrency": 8, "retry": {"max_retries": 5}},
            "task_queue": {"sqlite": {"immediate": True}},
        }

        factory = ConfigurationFactory()
        config = factory.create_configuration(
            plugin_manager, user_config_dict=user_config
        )

        # Test user overrides take precedence
        assert config.get("worker.concurrency") == 8  # User override
        assert config.get("worker.retry.max_retries") == 5  # User override
        assert config.get("worker.retry.retry_delay") == 60  # Plugin default
        assert config.get("task_queue.sqlite.immediate") is True  # User override


class TestWorkerConfigurationDefaults:
    """Test worker configuration default values are sensible for production use."""

    def test_worker_defaults_are_production_ready(self) -> None:
        """Test that worker configuration defaults are appropriate for production."""
        config_yaml = worker_config_provider.get_default_configuration()
        config_data = yaml.safe_load(config_yaml)

        worker = config_data["worker"]

        # Concurrency should be reasonable but not excessive
        assert 1 <= worker["concurrency"] <= 16

        # Retry settings should be conservative
        assert 1 <= worker["retry"]["max_retries"] <= 10
        assert worker["retry"]["retry_delay"] >= 30  # At least 30 seconds

        # Monitoring should be enabled by default
        assert worker["monitoring"]["enable"] is True

        # Task queue defaults should point to reasonable locations
        task_queue = config_data["task_queue"]
        assert task_queue["sqlite"]["path"].startswith("~/.local/share/")
        assert task_queue["redis"]["host"] in ["localhost", "127.0.0.1"]
        assert 1024 <= task_queue["redis"]["port"] <= 65535

    def test_worker_configuration_yaml_is_well_formatted(self) -> None:
        """Test that the YAML configuration is properly formatted with comments."""
        config_yaml = worker_config_provider.get_default_configuration()

        # Should have section comments
        assert "# Worker Configuration" in config_yaml
        assert "# Task Queue Configuration" in config_yaml

        # Should be properly indented and not have trailing whitespace
        lines = config_yaml.split("\n")
        for line in lines:
            assert line == line.rstrip()  # No trailing whitespace
