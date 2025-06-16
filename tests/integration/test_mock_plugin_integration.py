# ABOUTME: End-to-end integration tests using mock plugins with the complete system
# ABOUTME: Validates that mock plugins work correctly in realistic scenarios

from __future__ import annotations

import pytest

from paise2.plugins.core.manager import PluginSystem
from paise2.profiles.factory import create_test_plugin_manager
from tests.fixtures import MockConfiguration, create_test_plugin_manager_with_mocks


class TestMockPluginSystemIntegration:
    """End-to-end integration tests using mock plugins."""

    def test_mock_plugins_register_correctly(self) -> None:
        """Test that mock plugins register correctly with the plugin system."""
        plugin_manager = create_test_plugin_manager_with_mocks()

        # Discover and load plugins
        plugin_manager.discover_plugins()
        plugin_manager.load_plugins()

        # Verify all mock providers are registered
        config_providers = plugin_manager.get_configuration_providers()
        assert len(config_providers) > 0

        data_storage_providers = plugin_manager.get_data_storage_providers()
        assert len(data_storage_providers) > 0

        task_queue_providers = plugin_manager.get_task_queue_providers()
        assert len(task_queue_providers) > 0

        state_storage_providers = plugin_manager.get_state_storage_providers()
        assert len(state_storage_providers) > 0

        cache_providers = plugin_manager.get_cache_providers()
        assert len(cache_providers) > 0

        # Verify content extension points are registered
        content_extractors = plugin_manager.get_content_extractors()
        assert len(content_extractors) > 0

        content_sources = plugin_manager.get_content_sources()
        assert len(content_sources) > 0

        content_fetchers = plugin_manager.get_content_fetchers()
        assert len(content_fetchers) > 0

        lifecycle_actions = plugin_manager.get_lifecycle_actions()
        assert len(lifecycle_actions) > 0

    def test_mock_plugin_system_startup_shutdown(self) -> None:
        """Test complete startup and shutdown using mock plugins."""
        test_plugin_manager = create_test_plugin_manager_with_mocks()
        plugin_system = PluginSystem(test_plugin_manager)

        try:
            # Bootstrap and start the system
            plugin_system.bootstrap()
            plugin_system.start()
            assert plugin_system.is_running()

            # Should have access to singletons
            singletons = plugin_system.get_singletons()
            assert singletons is not None
            assert singletons.logger is not None
            assert singletons.configuration is not None
            assert singletons.state_storage is not None
            assert hasattr(singletons, "task_queue")
            assert singletons.cache is not None
            assert singletons.data_storage is not None

        finally:
            # Should stop cleanly
            plugin_system.stop()
            assert not plugin_system.is_running()

    def test_mock_plugin_system_with_user_config(self) -> None:
        """Test plugin system startup with user configuration override."""
        test_plugin_manager = create_test_plugin_manager_with_mocks()
        plugin_system = PluginSystem(test_plugin_manager)

        # User configuration that overrides plugin defaults
        user_config = {
            "test_plugin": {"enabled": False, "max_items": 50, "log_level": "info"},
            "custom_setting": "user_value",
        }

        try:
            # Bootstrap and start with user configuration
            plugin_system.bootstrap()
            plugin_system.start(user_config)
            assert plugin_system.is_running()

            # Configuration should include user overrides
            config = plugin_system.get_singletons().configuration
            assert config.get("test_plugin.enabled") is False
            assert config.get("test_plugin.max_items") == 50
            assert config.get("custom_setting") == "user_value"

        finally:
            plugin_system.stop()

    def test_mock_plugin_validation_through_registry(self) -> None:
        """Test that mock plugins pass validation through the registry."""
        plugin_manager = create_test_plugin_manager()

        # Load mock plugins
        plugin_manager.discover_plugins()
        plugin_manager.load_plugins()

        # Get mock providers and verify they implement protocols correctly
        config_providers = plugin_manager.get_configuration_providers()
        for provider in config_providers:
            # Should have required methods
            assert hasattr(provider, "get_default_configuration")
            assert hasattr(provider, "get_configuration_id")

            # Should return correct types
            config = provider.get_default_configuration()
            assert isinstance(config, str)

            config_id = provider.get_configuration_id()
            assert isinstance(config_id, str)

        # Test other provider types have required interfaces
        data_providers = plugin_manager.get_data_storage_providers()
        for data_provider in data_providers:
            assert hasattr(data_provider, "create_data_storage")
            # Should be able to create storage
            storage = data_provider.create_data_storage(MockConfiguration({}))
            assert hasattr(storage, "add_item")
            assert hasattr(storage, "find_item")

    def test_mock_content_processing_workflow(self) -> None:
        """Test a complete content processing workflow using mock plugins."""
        test_plugin_manager = create_test_plugin_manager_with_mocks()
        plugin_system = PluginSystem(test_plugin_manager)

        try:
            plugin_system.bootstrap()
            plugin_system.start()

            # Get the mock content extractor and verify it works
            plugin_manager = plugin_system.get_plugin_manager()
            extractors = plugin_manager.get_content_extractors()

            # Should have at least one mock extractor
            assert len(extractors) > 0

            # Test the extractor can handle test URLs
            mock_extractor = extractors[0]
            assert mock_extractor.can_extract("test://document.txt")
            assert not mock_extractor.can_extract("http://example.com")

            # Test preferred MIME types
            mime_types = mock_extractor.preferred_mime_types()
            assert "text/test" in mime_types

            # Get mock content source and verify it works
            sources = plugin_manager.get_content_sources()
            assert len(sources) > 0

            # Get mock content fetcher and verify it works
            fetchers = plugin_manager.get_content_fetchers()
            assert len(fetchers) > 0

            mock_fetcher = fetchers[0]
            # Create a mock host to test can_fetch
            from unittest.mock import Mock

            mock_host = Mock()
            assert mock_fetcher.can_fetch(mock_host, "test://document.txt")
            assert not mock_fetcher.can_fetch(mock_host, "http://example.com")

        finally:
            plugin_system.stop()

    def test_mock_plugins_provide_working_examples(self) -> None:
        """Test that mock plugins serve as good examples for plugin authors."""
        plugin_manager = create_test_plugin_manager_with_mocks()
        plugin_manager.discover_plugins()
        plugin_manager.load_plugins()

        # Mock plugins should demonstrate all extension points
        assert len(plugin_manager.get_configuration_providers()) > 0
        assert len(plugin_manager.get_data_storage_providers()) > 0
        assert len(plugin_manager.get_task_queue_providers()) > 0
        assert len(plugin_manager.get_state_storage_providers()) > 0
        assert len(plugin_manager.get_cache_providers()) > 0
        assert len(plugin_manager.get_content_extractors()) > 0
        assert len(plugin_manager.get_content_sources()) > 0
        assert len(plugin_manager.get_content_fetchers()) > 0
        assert len(plugin_manager.get_lifecycle_actions()) > 0

        # Each mock plugin should implement its protocol correctly
        # (Protocol compliance is tested by the fact that registration succeeds)

    def test_mock_plugin_state_isolation(self) -> None:
        """Test that mock plugins demonstrate proper state isolation."""
        test_plugin_manager = create_test_plugin_manager_with_mocks()
        plugin_system = PluginSystem(test_plugin_manager)

        try:
            plugin_system.bootstrap()
            plugin_system.start()

            # Get state storage
            state_storage = plugin_system.get_singletons().state_storage

            # Simulate two different plugins storing state
            state_storage.store("plugin1", "key1", "value1")
            state_storage.store("plugin2", "key1", "value2")

            # State should be isolated
            assert state_storage.get("plugin1", "key1") == "value1"
            assert state_storage.get("plugin2", "key1") == "value2"
            assert state_storage.get("plugin3", "key1") is None

        finally:
            plugin_system.stop()

    @pytest.mark.asyncio
    async def test_mock_plugin_task_queue_integration(self) -> None:
        """Test that mock task queue provider works in integration."""
        test_plugin_manager = create_test_plugin_manager_with_mocks()
        plugin_system = PluginSystem(test_plugin_manager)

        try:
            plugin_system.bootstrap()
            await plugin_system.start_async()

            # Get task queue
            task_queue = plugin_system.get_singletons().task_queue

            # MockTaskQueueProvider returns MemoryHuey for immediate execution
            # This is expected behavior for test environment
            assert task_queue is not None  # MockTaskQueueProvider returns MemoryHuey
            from huey import MemoryHuey

            assert isinstance(task_queue, MemoryHuey)

        finally:
            plugin_system.stop()

    @pytest.mark.asyncio
    async def test_mock_plugin_cache_integration(self) -> None:
        """Test that mock cache provider works in integration."""
        test_plugin_manager = create_test_plugin_manager_with_mocks()
        plugin_system = PluginSystem(test_plugin_manager)

        try:
            plugin_system.bootstrap()
            await plugin_system.start_async()

            # Get cache
            cache = plugin_system.get_singletons().cache

            # Test cache operations
            cache_id = await cache.save("test_partition", "test content", ".txt")
            assert cache_id is not None

            # Retrieve content
            content = await cache.get(cache_id)
            assert content == "test content"

            # Test partition operations
            partition_ids = await cache.get_all("test_partition")
            assert cache_id in partition_ids

        finally:
            plugin_system.stop()

    @pytest.mark.asyncio
    async def test_mock_plugin_data_storage_integration(self) -> None:
        """Test that mock data storage provider works in integration."""
        test_plugin_manager = create_test_plugin_manager_with_mocks()
        plugin_system = PluginSystem(test_plugin_manager)

        try:
            plugin_system.bootstrap()
            await plugin_system.start_async()

            # Get data storage and a mock host
            storage = plugin_system.get_singletons().data_storage
            from tests.fixtures.mock_plugins import MockDataStorageHost

            host = MockDataStorageHost()

            # Test storage operations
            from paise2.models import Metadata

            metadata = Metadata(source_url="test://doc.txt", title="Test Document")

            item_id = await storage.add_item(host, "test content", metadata)
            assert item_id is not None

            # Find item
            found_metadata = await storage.find_item(item_id)
            assert found_metadata is not None
            assert found_metadata.source_url == "test://doc.txt"

        finally:
            plugin_system.stop()


class TestMockPluginDocumentationValue:
    """Test that mock plugins provide educational value for plugin authors."""

    def test_mock_plugins_show_hookimpl_pattern(self) -> None:
        """Test that mock plugins demonstrate the @hookimpl registration pattern."""
        # Import registration functions to verify they exist and are properly decorated
        from tests.fixtures.mock_plugins import (
            register_cache_provider,
            register_configuration_provider,
            register_content_extractor,
            register_content_fetcher,
            register_content_source,
            register_data_storage_provider,
            register_lifecycle_action,
            register_state_storage_provider,
            register_task_queue_provider,
        )

        # All should be callable functions
        registration_functions = [
            register_configuration_provider,
            register_content_extractor,
            register_content_source,
            register_content_fetcher,
            register_lifecycle_action,
            register_data_storage_provider,
            register_task_queue_provider,
            register_state_storage_provider,
            register_cache_provider,
        ]

        for func in registration_functions:
            assert callable(func)
            # They should all take a single 'register' parameter
            assert func.__code__.co_argcount == 1

    def test_mock_plugins_demonstrate_protocol_adherence(self) -> None:
        """Test that mock plugins show how to properly implement protocols."""
        from tests.fixtures.mock_plugins import (
            MockConfigurationProvider,
            MockContentExtractor,
            MockContentFetcher,
            MockContentSource,
        )

        # Configuration Provider
        config_provider = MockConfigurationProvider()
        config = config_provider.get_default_configuration()
        assert isinstance(config, str)
        assert len(config) > 0

        config_id = config_provider.get_configuration_id()
        assert isinstance(config_id, str)
        assert len(config_id) > 0

        # Content Extractor
        extractor = MockContentExtractor()
        assert isinstance(extractor.can_extract("test://doc.txt"), bool)
        assert isinstance(extractor.preferred_mime_types(), list)

        # Content Source
        source = MockContentSource()
        # Has required async methods
        assert hasattr(source, "start_source")
        assert hasattr(source, "stop_source")

        # Content Fetcher
        fetcher = MockContentFetcher()
        from unittest.mock import Mock

        mock_host = Mock()
        assert isinstance(fetcher.can_fetch(mock_host, "test://doc.txt"), bool)

    def test_mock_plugins_show_realistic_functionality(self) -> None:
        """Test that mock plugins provide realistic but simple examples."""
        from tests.fixtures.mock_plugins import MockContentExtractor, MockContentFetcher

        # Content Extractor shows realistic URL filtering
        extractor = MockContentExtractor()
        assert extractor.can_extract("test://document.txt")  # Handles test scheme
        assert extractor.can_extract("any://url", "text/test")  # Handles test MIME
        assert not extractor.can_extract("http://example.com")  # Rejects others

        # Content Fetcher shows realistic URL handling
        fetcher = MockContentFetcher()
        from unittest.mock import Mock

        mock_host = Mock()
        assert fetcher.can_fetch(
            mock_host, "test://document.txt"
        )  # Handles test scheme
        assert not fetcher.can_fetch(mock_host, "http://example.com")  # Rejects others
