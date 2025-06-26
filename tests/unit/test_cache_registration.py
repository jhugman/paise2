# ABOUTME: Integration tests for cache provider registration.
# ABOUTME: Tests that cache providers can be properly discovered and registered.

from __future__ import annotations

import tempfile
from pathlib import Path

from paise2.plugins.core.registry import PluginManager
from paise2.plugins.providers.cache import (
    FileCacheProvider,
    MemoryCacheProvider,
)
from tests.fixtures import MockConfiguration


class TestCacheProviderRegistration:
    """Test cache provider registration with plugin system."""

    def test_memory_cache_provider_registration(self) -> None:
        """Test memory cache provider can be registered."""
        plugin_manager = PluginManager()

        provider = MemoryCacheProvider()
        result = plugin_manager.register_cache_provider(provider)

        assert result is True

        # Verify provider was registered
        registered_providers = plugin_manager.get_cache_providers()
        assert len(registered_providers) == 1
        assert isinstance(registered_providers[0], MemoryCacheProvider)

    def test_file_cache_provider_registration(self) -> None:
        """Test file cache provider can be registered."""
        plugin_manager = PluginManager()

        provider = FileCacheProvider()
        result = plugin_manager.register_cache_provider(provider)

        assert result is True

        # Verify provider was registered
        registered_providers = plugin_manager.get_cache_providers()
        assert len(registered_providers) == 1
        assert isinstance(registered_providers[0], FileCacheProvider)

    def test_multiple_cache_providers_registration(self) -> None:
        """Test multiple cache providers can be registered."""
        plugin_manager = PluginManager()

        memory_provider = MemoryCacheProvider()
        file_provider = FileCacheProvider()

        result1 = plugin_manager.register_cache_provider(memory_provider)
        result2 = plugin_manager.register_cache_provider(file_provider)

        assert result1 is True
        assert result2 is True

        # Verify both providers were registered
        registered_providers = plugin_manager.get_cache_providers()
        assert len(registered_providers) == 2

        provider_types = [type(p) for p in registered_providers]
        assert MemoryCacheProvider in provider_types
        assert FileCacheProvider in provider_types

    def test_cache_provider_protocol_validation(self) -> None:
        """Test that provider registration validates CacheProvider protocol."""
        plugin_manager = PluginManager()

        # Valid provider should work
        valid_provider = MemoryCacheProvider()
        assert plugin_manager.register_cache_provider(valid_provider) is True

        # Invalid provider should fail - doesn't fully implement the protocol
        class InvalidProvider:
            pass

        invalid_provider = InvalidProvider()
        result = plugin_manager.register_cache_provider(invalid_provider)  # type: ignore[arg-type]
        assert result is False

    def test_none_cache_provider_registration(self) -> None:
        """Test that registering None as provider fails gracefully."""
        plugin_manager = PluginManager()

        result = plugin_manager.register_cache_provider(None)  # type: ignore[arg-type]
        assert result is False

        # Verify no providers were registered
        registered_providers = plugin_manager.get_cache_providers()
        assert len(registered_providers) == 0


class TestCacheProviderDiscovery:
    """Test cache provider plugin discovery."""

    def test_cache_provider_creation_from_configuration(self) -> None:
        """Test that providers can create cache instances from configuration."""
        # Test memory provider (configuration independent)
        memory_provider = MemoryCacheProvider()
        memory_cache = memory_provider.create_cache(MockConfiguration({}))

        assert memory_cache is not None
        assert hasattr(memory_cache, "save")
        assert hasattr(memory_cache, "get")

        # Test file provider with temporary directory
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_provider = FileCacheProvider()
            file_cache = file_provider.create_cache(
                MockConfiguration({"cache.file_path": tmp_dir})
            )

            assert file_cache is not None
            assert hasattr(file_cache, "save")
            assert hasattr(file_cache, "get")

    def test_memory_provider_ignores_configuration(self) -> None:
        """Test that memory provider works regardless of configuration."""
        provider = MemoryCacheProvider()

        # Any configuration should work
        cache1 = provider.create_cache(MockConfiguration({}))
        cache2 = provider.create_cache(
            MockConfiguration({"cache.file_path": "/some/path"})
        )

        # Both should work independently
        assert cache1 is not None
        assert cache2 is not None


class TestCacheProviderIntegrationWithConfiguration:
    """Test cache provider integration with configuration system."""

    def test_file_provider_uses_configuration_path(self) -> None:
        """Test that file provider uses path from configuration."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            provider = FileCacheProvider()
            cache = provider.create_cache(
                MockConfiguration({"cache.file_path": tmp_dir})
            )

            assert cache is not None
            # Should be FileCacheManager instance with configured directory
            assert hasattr(cache, "cache_dir")
            assert str(cache.cache_dir) == str(Path(tmp_dir).resolve())

    def test_file_provider_uses_default_path_when_not_configured(self) -> None:
        """Test that file provider uses default path when not configured."""
        provider = FileCacheProvider()
        cache = provider.create_cache(MockConfiguration({}))

        assert cache is not None
        assert hasattr(cache, "cache_dir")
        # Should use the default path
        default_path = Path("~/.local/share/paise2/cache").expanduser().resolve()
        assert cache.cache_dir == default_path

    def test_file_provider_handles_memory_special_case(self) -> None:
        """Test file provider handles :memory: special case."""
        provider = FileCacheProvider()
        cache = provider.create_cache(
            MockConfiguration({"cache.file_path": ":memory:"})
        )

        assert cache is not None
        # Should return MemoryCacheManager for :memory: special case
        assert type(cache).__name__ == "MemoryCacheManager"

    def test_file_provider_handles_path_expansion(self) -> None:
        """Test file provider handles path expansion (~ for home directory)."""
        provider = FileCacheProvider()
        cache = provider.create_cache(
            MockConfiguration({"cache.file_path": "~/test_cache"})
        )

        assert cache is not None
        assert hasattr(cache, "cache_dir")

        # Should expand ~ to home directory
        expected_path = Path("~/test_cache").expanduser().resolve()
        assert cache.cache_dir == expected_path
