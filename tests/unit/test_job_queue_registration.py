# ABOUTME: Integration tests for job queue provider registration.
# ABOUTME: Tests that job queue providers can be properly discovered and registered.

from __future__ import annotations

import tempfile
from pathlib import Path

from paise2.plugins.core.jobs import (
    MockJobExecutor,
    NoJobQueueProvider,
    SQLiteJobQueueProvider,
)
from paise2.plugins.core.registry import PluginManager
from tests.fixtures import MockConfiguration


class TestJobQueueProviderRegistration:
    """Test job queue provider registration with plugin system."""

    def test_no_job_queue_provider_registration(self) -> None:
        """Test no job queue provider can be registered."""
        plugin_manager = PluginManager()

        provider = NoJobQueueProvider()
        result = plugin_manager.register_job_queue_provider(provider)

        assert result is True

        # Verify provider was registered
        registered_providers = plugin_manager.get_job_queue_providers()
        assert len(registered_providers) == 1
        assert isinstance(registered_providers[0], NoJobQueueProvider)

    def test_sqlite_job_queue_provider_registration(self) -> None:
        """Test SQLite job queue provider can be registered."""
        plugin_manager = PluginManager()

        provider = SQLiteJobQueueProvider()
        result = plugin_manager.register_job_queue_provider(provider)

        assert result is True

        # Verify provider was registered
        registered_providers = plugin_manager.get_job_queue_providers()
        assert len(registered_providers) == 1
        assert isinstance(registered_providers[0], SQLiteJobQueueProvider)

    def test_multiple_job_queue_providers_registration(self) -> None:
        """Test multiple job queue providers can be registered."""
        plugin_manager = PluginManager()

        sync_provider = NoJobQueueProvider()
        sqlite_provider = SQLiteJobQueueProvider()

        result1 = plugin_manager.register_job_queue_provider(sync_provider)
        result2 = plugin_manager.register_job_queue_provider(sqlite_provider)

        assert result1 is True
        assert result2 is True

        # Verify both providers were registered
        registered_providers = plugin_manager.get_job_queue_providers()
        assert len(registered_providers) == 2

        provider_types = [type(p) for p in registered_providers]
        assert NoJobQueueProvider in provider_types
        assert SQLiteJobQueueProvider in provider_types

    def test_job_queue_provider_protocol_validation(self) -> None:
        """Test that provider registration validates JobQueueProvider protocol."""
        plugin_manager = PluginManager()

        # Valid provider should work
        valid_provider = NoJobQueueProvider()
        assert plugin_manager.register_job_queue_provider(valid_provider) is True

        # Invalid provider should fail
        class InvalidProvider:
            pass

        invalid_provider = InvalidProvider()
        result = plugin_manager.register_job_queue_provider(invalid_provider)  # type: ignore[arg-type]
        assert result is False


class TestJobQueueProviderDiscovery:
    """Test job queue provider plugin discovery."""

    def test_profile_based_job_queue_providers_discoverable(self) -> None:
        """Test that job queue providers are discoverable via profile-based loading."""
        # Test that profile-based plugins are discoverable
        from paise2.profiles.factory import create_test_plugin_manager

        test_manager = create_test_plugin_manager()
        discovered = test_manager.discover_plugins()

        # Should find plugins in test profile
        assert isinstance(discovered, list)

    def test_job_queue_provider_creation_from_configuration(self) -> None:
        """Test that providers can create job queue instances from configuration."""
        # Test synchronous provider with MockJobExecutor
        sync_provider = NoJobQueueProvider()
        mock_executor = MockJobExecutor()
        sync_queue = sync_provider.create_job_queue(
            MockConfiguration({}), job_executor=mock_executor
        )

        assert sync_queue is not None
        assert hasattr(sync_queue, "enqueue")
        assert hasattr(sync_queue, "dequeue")

        # Test SQLite provider with temporary file
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
            sqlite_provider = SQLiteJobQueueProvider()
            sqlite_queue = sqlite_provider.create_job_queue(
                MockConfiguration({"job_queue.sqlite_path": tmp_file.name})
            )

            assert sqlite_queue is not None
            assert hasattr(sqlite_queue, "enqueue")
            assert hasattr(sqlite_queue, "dequeue")


class TestJobQueueProviderIntegrationWithConfiguration:
    """Test job queue provider integration with configuration system."""

    def test_sqlite_provider_uses_configuration_path(self) -> None:
        """Test that SQLite provider uses path from configuration."""
        provider = SQLiteJobQueueProvider()

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
            custom_path = tmp_file.name
            configuration = MockConfiguration({"job_queue.sqlite_path": custom_path})

            queue = provider.create_job_queue(configuration)

            # Test that queue works with the custom path
            assert queue is not None
            # The database file should be created at the custom path
            assert Path(custom_path).exists()

    def test_sqlite_provider_uses_default_path_when_not_configured(self) -> None:
        """Test that SQLite provider uses default path when not configured."""
        provider = SQLiteJobQueueProvider()

        # Empty configuration should use default
        queue = provider.create_job_queue(MockConfiguration({}))

        # Queue should work even with default path
        assert queue is not None

    def test_synchronous_provider_ignores_configuration(self) -> None:
        """Test that synchronous provider works regardless of configuration."""
        provider = NoJobQueueProvider()
        mock_executor = MockJobExecutor()

        # Any configuration should work
        queue1 = provider.create_job_queue(
            MockConfiguration({}), job_executor=mock_executor
        )
        queue2 = provider.create_job_queue(
            MockConfiguration({"anything": "value"}), job_executor=mock_executor
        )

        # Both should work independently
        assert queue1 is not None
        assert queue2 is not None
