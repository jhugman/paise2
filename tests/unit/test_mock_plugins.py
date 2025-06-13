# ABOUTME: Integration tests for mock plugin implementations with the plugin system
# ABOUTME: Validates that mock plugins work correctly in an end-to-end scenario

from __future__ import annotations

import pytest

from paise2.models import Metadata
from tests.fixtures import (
    MockConfiguration,
    MockContentExtractorHost,
    MockContentFetcherHost,
    MockContentSourceHost,
    MockLifecycleHost,
)
from tests.fixtures.mock_plugins import (
    MockCacheProvider,
    MockConfigurationProvider,
    MockContentExtractor,
    MockContentFetcher,
    MockContentSource,
    MockDataStorageHost,
    MockDataStorageProvider,
    MockJobQueueProvider,
    MockLifecycleAction,
    MockStateStorageProvider,
)


class TestMockPluginIntegration:
    """Integration tests for mock plugins working with the plugin system."""

    def test_mock_configuration_provider_works(self) -> None:
        """Test that MockConfigurationProvider works correctly."""
        provider = MockConfigurationProvider()

        # Should provide valid YAML configuration
        config = provider.get_default_configuration()
        assert isinstance(config, str)
        assert "test_plugin:" in config

        # Should provide consistent configuration ID
        config_id = provider.get_configuration_id()
        assert config_id == "test_plugin"

    @pytest.mark.asyncio
    async def test_mock_content_extractor_workflow(self) -> None:
        """Test MockContentExtractor in a realistic workflow."""
        extractor = MockContentExtractor()

        # Test can_extract logic
        assert extractor.can_extract("test://document.txt")
        assert not extractor.can_extract("http://example.com")

        # Test preferred MIME types
        mime_types = extractor.preferred_mime_types()
        assert "text/test" in mime_types

        # Test extraction with test double host
        test_host = MockContentExtractorHost()

        metadata = Metadata(source_url="test://document.txt")
        await extractor.extract(test_host, "Test content", metadata)

        # Verify extraction worked by checking the stored content
        assert len(test_host.extracted_content) == 1
        content, stored_metadata = test_host.extracted_content[0]
        assert content == "Test content"
        assert stored_metadata.title == "Extracted: test://document.txt"

    @pytest.mark.asyncio
    async def test_mock_content_source_workflow(self) -> None:
        """Test MockContentSource in a realistic workflow."""
        source = MockContentSource()

        # Test with mock host
        mock_host = MockContentSourceHost()

        # Start source should schedule URLs
        await source.start_source(mock_host)

        # Should have scheduled 3 test URLs
        assert len(mock_host.scheduled_urls) == 3

        # Check that the URLs are what we expect
        scheduled_urls = [url for url, _ in mock_host.scheduled_urls]
        assert "test://document1.txt" in scheduled_urls
        assert "test://document2.txt" in scheduled_urls
        assert "test://document3.txt" in scheduled_urls

        # Stop should complete without error
        await source.stop_source(mock_host)

    @pytest.mark.asyncio
    async def test_mock_content_fetcher_workflow(self) -> None:
        """Test MockContentFetcher in a realistic workflow."""
        fetcher = MockContentFetcher()

        # Test can_fetch logic
        mock_host = MockContentFetcherHost()
        assert fetcher.can_fetch(mock_host, "test://document.txt")
        assert not fetcher.can_fetch(mock_host, "http://example.com")

        # Test fetching
        await fetcher.fetch(mock_host, "test://document1.txt")

        # Should have stored fetched content
        assert len(mock_host.fetched_content) == 1
        url, content, metadata = mock_host.fetched_content[0]
        assert url == "test://document1.txt"
        content_str = content if isinstance(content, str) else str(content)
        assert "This is test document 1 content" in content_str

    @pytest.mark.asyncio
    async def test_mock_lifecycle_action_workflow(self) -> None:
        """Test MockLifecycleAction in a realistic workflow."""
        action = MockLifecycleAction()

        # Test with mock host and logger
        mock_host = MockLifecycleHost()
        mock_logger = mock_host.logger

        # Test startup
        await action.on_start(mock_host)

        # Verify logger was called with startup message
        assert len(mock_logger.messages) > 0
        assert any("starting up" in msg.lower() for msg in mock_logger.messages)

        # Test shutdown
        mock_logger.clear()
        await action.on_stop(mock_host)

        # Verify logger was called with shutdown message
        assert len(mock_logger.messages) > 0
        assert any("shutting down" in msg.lower() for msg in mock_logger.messages)

    def test_mock_provider_creation(self) -> None:
        """Test that mock providers create working implementations."""
        config = MockConfiguration({})

        # Test DataStorageProvider
        data_provider = MockDataStorageProvider()
        data_storage = data_provider.create_data_storage(config)
        assert hasattr(data_storage, "add_item")

        # Test JobQueueProvider
        job_provider = MockJobQueueProvider()
        job_queue = job_provider.create_job_queue(config)
        assert hasattr(job_queue, "enqueue")

        # Test StateStorageProvider
        state_provider = MockStateStorageProvider()
        state_storage = state_provider.create_state_storage(config)
        assert hasattr(state_storage, "store")

        # Test CacheProvider
        cache_provider = MockCacheProvider()
        cache_manager = cache_provider.create_cache(config)
        assert hasattr(cache_manager, "save")

    @pytest.mark.asyncio
    async def test_mock_job_queue_operations(self) -> None:
        """Test MockJobQueue basic operations."""
        job_provider = MockJobQueueProvider()
        queue = job_provider.create_job_queue(MockConfiguration({}))

        # Test job lifecycle
        job_id = await queue.enqueue("test_job", {"data": "test"}, priority=1)
        assert job_id.startswith("test_job_")

        # Check incomplete jobs
        incomplete = await queue.get_incomplete_jobs()
        assert len(incomplete) == 1

        # Dequeue and complete
        job = await queue.dequeue("worker1")
        assert job is not None
        await queue.complete(job.job_id)

        # Should be no incomplete jobs
        incomplete = await queue.get_incomplete_jobs()
        assert len(incomplete) == 0

    @pytest.mark.asyncio
    async def test_mock_cache_operations(self) -> None:
        """Test MockCacheManager basic operations."""
        cache_provider = MockCacheProvider()
        cache = cache_provider.create_cache(MockConfiguration({}))

        # Test save and retrieve
        cache_id = await cache.save("test_partition", "test content", ".txt")
        content = await cache.get(cache_id)
        assert content == "test content"

        # Test remove
        removed = await cache.remove(cache_id)
        assert removed is True

        # Should not be able to get removed content
        with pytest.raises(KeyError):
            await cache.get(cache_id)

    def test_mock_state_storage_operations(self) -> None:
        """Test MockStateStorage basic operations."""
        state_provider = MockStateStorageProvider()
        storage = state_provider.create_state_storage(MockConfiguration({}))

        # Test store and retrieve
        storage.store("plugin1", "key1", "value1", version=1)
        value = storage.get("plugin1", "key1")
        assert value == "value1"

        # Test partitioning
        storage.store("plugin2", "key1", "value2", version=1)
        value2 = storage.get("plugin2", "key1")
        assert value2 == "value2"

        # Should be isolated
        assert storage.get("plugin1", "key1") != storage.get("plugin2", "key1")

    @pytest.mark.asyncio
    async def test_mock_data_storage_operations(self) -> None:
        """Test MockDataStorage basic operations."""
        data_provider = MockDataStorageProvider()
        storage = data_provider.create_data_storage(MockConfiguration({}))

        # Test add item
        mock_host = MockDataStorageHost()
        metadata = Metadata(source_url="test://doc.txt")
        item_id = await storage.add_item(mock_host, "content", metadata)
        assert item_id.startswith("test_item_")

        # Test find item
        found_metadata = await storage.find_item(item_id)
        assert found_metadata is not None
        assert found_metadata.source_url == "test://doc.txt"

        # Test remove item
        cache_id = await storage.remove_item(mock_host, item_id)
        assert cache_id is not None
        assert cache_id.startswith("cache_")


class TestMockPluginDocumentation:
    """Test that mock plugins serve as good examples for plugin authors."""

    def test_mock_plugins_demonstrate_protocol_implementation(self) -> None:
        """Test that mock plugins show how to implement protocols correctly."""
        # ConfigurationProvider protocol
        config_provider = MockConfigurationProvider()
        assert hasattr(config_provider, "get_default_configuration")
        assert hasattr(config_provider, "get_configuration_id")

        # ContentExtractor protocol
        extractor = MockContentExtractor()
        assert hasattr(extractor, "can_extract")
        assert hasattr(extractor, "preferred_mime_types")
        assert hasattr(extractor, "extract")

        # ContentSource protocol
        source = MockContentSource()
        assert hasattr(source, "start_source")
        assert hasattr(source, "stop_source")

        # ContentFetcher protocol
        fetcher = MockContentFetcher()
        assert hasattr(fetcher, "can_fetch")
        assert hasattr(fetcher, "fetch")

    def test_mock_plugins_show_proper_registration_pattern(self) -> None:
        """Test that mock plugins demonstrate proper @hookimpl registration."""
        # Import the registration functions to verify they exist
        from tests.fixtures.mock_plugins import (
            register_cache_provider,
            register_configuration_provider,
            register_content_extractor,
            register_content_fetcher,
            register_content_source,
            register_data_storage_provider,
            register_job_queue_provider,
            register_lifecycle_action,
            register_state_storage_provider,
        )

        # All registration functions should be callable
        assert callable(register_configuration_provider)
        assert callable(register_content_extractor)
        assert callable(register_content_source)
        assert callable(register_content_fetcher)
        assert callable(register_lifecycle_action)
        assert callable(register_data_storage_provider)
        assert callable(register_job_queue_provider)
        assert callable(register_state_storage_provider)
        assert callable(register_cache_provider)

    def test_mock_plugins_show_realistic_functionality(self) -> None:
        """Test that mock plugins provide realistic but simple functionality."""
        # Configuration provider provides valid YAML
        config_provider = MockConfigurationProvider()
        config = config_provider.get_default_configuration()
        assert "test_plugin:" in config
        assert "enabled:" in config

        # Content extractor handles specific URL patterns
        extractor = MockContentExtractor()
        assert extractor.can_extract("test://document.txt")
        assert not extractor.can_extract("http://example.com")

        # Content fetcher generates different content for different URLs
        fetcher = MockContentFetcher()
        mock_host = MockContentFetcherHost()
        assert fetcher.can_fetch(mock_host, "test://document1.txt")
        assert fetcher.can_fetch(mock_host, "test://document2.txt")
        assert not fetcher.can_fetch(mock_host, "http://example.com")
