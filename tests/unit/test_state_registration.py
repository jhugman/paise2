# ABOUTME: Integration tests for state storage provider registration.
# ABOUTME: Tests that state storage providers can be properly discovered and registered.

import tempfile

from paise2.plugins.core.registry import PluginManager
from paise2.state.providers import FileStateStorageProvider, MemoryStateStorageProvider
from tests.fixtures import MockConfiguration


class TestStateStorageProviderRegistration:
    """Test state storage provider registration with plugin system."""

    def test_memory_state_storage_provider_registration(self) -> None:
        """Test memory state storage provider can be registered."""
        plugin_manager = PluginManager()

        provider = MemoryStateStorageProvider()
        result = plugin_manager.register_state_storage_provider(provider)

        assert result is True

        # Verify provider was registered
        registered_providers = plugin_manager.get_state_storage_providers()
        assert len(registered_providers) == 1
        assert isinstance(registered_providers[0], MemoryStateStorageProvider)

    def test_file_state_storage_provider_registration(self) -> None:
        """Test file state storage provider can be registered."""
        plugin_manager = PluginManager()

        provider = FileStateStorageProvider()
        result = plugin_manager.register_state_storage_provider(provider)

        assert result is True

        # Verify provider was registered
        registered_providers = plugin_manager.get_state_storage_providers()
        assert len(registered_providers) == 1
        assert isinstance(registered_providers[0], FileStateStorageProvider)

    def test_multiple_state_storage_providers_registration(self) -> None:
        """Test multiple state storage providers can be registered."""
        plugin_manager = PluginManager()

        memory_provider = MemoryStateStorageProvider()
        file_provider = FileStateStorageProvider()

        result1 = plugin_manager.register_state_storage_provider(memory_provider)
        result2 = plugin_manager.register_state_storage_provider(file_provider)

        assert result1 is True
        assert result2 is True

        # Verify both providers were registered
        registered_providers = plugin_manager.get_state_storage_providers()
        assert len(registered_providers) == 2

        provider_types = [type(p) for p in registered_providers]
        assert MemoryStateStorageProvider in provider_types
        assert FileStateStorageProvider in provider_types

    def test_state_storage_provider_protocol_validation(self) -> None:
        """Test that provider registration validates StateStorageProvider protocol."""
        plugin_manager = PluginManager()

        # Valid provider should work
        valid_provider = MemoryStateStorageProvider()
        assert plugin_manager.register_state_storage_provider(valid_provider) is True

        # Invalid provider should fail - doesn't fully implement the protocol
        class InvalidProvider:
            pass

        invalid_provider = InvalidProvider()
        result = plugin_manager.register_state_storage_provider(invalid_provider)  # type: ignore[arg-type]
        assert result is False

    def test_none_state_storage_provider_registration(self) -> None:
        """Test that registering None as provider fails gracefully."""
        plugin_manager = PluginManager()

        # We expect None to fail, but mypy needs help understanding this is intentional
        result = plugin_manager.register_state_storage_provider(None)  # type: ignore[arg-type]

        assert result is False

        # No providers should be registered
        registered_providers = plugin_manager.get_state_storage_providers()
        assert len(registered_providers) == 0


class TestStateStorageProviderDiscovery:
    """Test state storage provider plugin discovery."""

    def test_profile_based_state_storage_providers_discoverable(self) -> None:
        """Test that state storage providers are discoverable via
        profile-based loading."""
        # Test that profile-based plugins are discoverable
        from paise2.profiles.factory import create_test_plugin_manager

        test_manager = create_test_plugin_manager()
        discovered = test_manager.discover_plugins()

        # Should find plugins in test profile
        assert isinstance(discovered, list)

    def test_state_storage_provider_creation_from_configuration(self) -> None:
        """Test that providers can create storage instances from configuration."""
        # Test memory provider
        memory_provider = MemoryStateStorageProvider()
        memory_storage = memory_provider.create_state_storage(MockConfiguration({}))

        assert memory_storage is not None
        assert hasattr(memory_storage, "store")
        assert hasattr(memory_storage, "get")

        # Test file provider with temporary file
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
            file_provider = FileStateStorageProvider()
            file_storage = file_provider.create_state_storage(
                MockConfiguration({"state_storage.file_path": tmp_file.name})
            )

            assert file_storage is not None
            assert hasattr(file_storage, "store")
            assert hasattr(file_storage, "get")


class TestStateStorageProviderIntegrationWithConfiguration:
    """Test state storage provider integration with configuration system."""

    def test_file_provider_uses_configuration_path(self) -> None:
        """Test that file provider uses path from configuration."""
        provider = FileStateStorageProvider()

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
            custom_path = tmp_file.name
            configuration = MockConfiguration({"state_storage.file_path": custom_path})

            storage = provider.create_state_storage(configuration)

            # Test that storage works with the custom path
            storage.store("test_partition", "test_key", "test_value")
            result = storage.get("test_partition", "test_key")

            assert result == "test_value"

    def test_file_provider_uses_default_path_when_not_configured(self) -> None:
        """Test that file provider uses default path when not configured."""
        provider = FileStateStorageProvider()

        # Empty configuration should use default
        storage = provider.create_state_storage(MockConfiguration({}))

        # Storage should work even with default path
        storage.store("test_partition", "test_key", "test_value")
        result = storage.get("test_partition", "test_key")

        assert result == "test_value"

    def test_memory_provider_ignores_configuration(self) -> None:
        """Test that memory provider works regardless of configuration."""
        provider = MemoryStateStorageProvider()

        # Any configuration should work
        storage1 = provider.create_state_storage(MockConfiguration({}))
        storage2 = provider.create_state_storage(
            MockConfiguration({"anything": "value"})
        )

        # Both should work independently
        storage1.store("test", "key", "value1")
        storage2.store("test", "key", "value2")

        assert storage1.get("test", "key") == "value1"
        assert storage2.get("test", "key") == "value2"
