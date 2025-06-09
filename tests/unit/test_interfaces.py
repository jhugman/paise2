# ABOUTME: Comprehensive tests for protocol interface compliance and functionality
# ABOUTME: Validates that all protocol interfaces are properly defined and testable

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import pytest

from paise2.models import CacheId, ItemId, JobId, Metadata
from paise2.plugins.core.interfaces import (
    # Host interfaces
    BaseHost,
    CacheManager,
    CacheProvider,
    # Phase 2 protocols
    ConfigurationProvider,
    # Phase 4 protocols
    ContentExtractor,
    ContentExtractorHost,
    ContentFetcher,
    ContentFetcherHost,
    ContentSource,
    ContentSourceHost,
    DataStorage,
    DataStorageHost,
    DataStorageProvider,
    Job,
    JobQueue,
    JobQueueProvider,
    LifecycleAction,
    LifecycleHost,
    StateManager,
    StateStorage,
    StateStorageProvider,
)


class TestPhase2Protocols:
    """Test Phase 2 singleton-contributing protocols."""

    def test_configuration_provider_protocol(self):
        """Test that ConfigurationProvider protocol is properly defined."""

        class TestConfigProvider:
            def get_default_configuration(self) -> str:
                return "test: value"

            def get_configuration_id(self) -> str:
                return "test-config"

        provider = TestConfigProvider()
        assert isinstance(provider, ConfigurationProvider)
        assert provider.get_default_configuration() == "test: value"
        assert provider.get_configuration_id() == "test-config"

    def test_data_storage_provider_protocol(self):
        """Test that DataStorageProvider protocol is properly defined."""

        class TestStorage:
            async def add_item(self, host, content: str, metadata: Metadata) -> ItemId:
                return "test-item-id"

            async def update_item(self, host, item_id: ItemId, content: str) -> None:
                pass

            async def update_metadata(
                self, host, item_id: ItemId, metadata: Metadata
            ) -> None:
                pass

            async def find_item_id(self, host, metadata: Metadata) -> ItemId | None:
                return None

            async def find_item(self, item_id: ItemId) -> Metadata | None:
                return None

            async def remove_item(self, host, item_id: ItemId) -> CacheId | None:
                return None

            async def remove_items_by_metadata(
                self, host, metadata: Metadata
            ) -> list[CacheId]:
                return []

            async def remove_items_by_url(self, host, url: str) -> list[CacheId]:
                return []

        class TestStorageProvider:
            def create_data_storage(self, configuration: dict[str, Any]) -> DataStorage:
                return TestStorage()

        provider = TestStorageProvider()
        assert isinstance(provider, DataStorageProvider)

        storage = provider.create_data_storage({})
        assert isinstance(storage, DataStorage)

    def test_job_dataclass(self):
        """Test that Job dataclass is properly defined."""
        now = datetime.now()
        job = Job(
            job_id="test-job",
            job_type="test_type",
            job_data={"key": "value"},
            priority=1,
            created_at=now,
            worker_id="test-worker",
        )

        assert job.job_id == "test-job"
        assert job.job_type == "test_type"
        assert job.job_data == {"key": "value"}
        assert job.priority == 1
        assert job.created_at == now
        assert job.worker_id == "test-worker"

    def test_job_queue_provider_protocol(self):
        """Test that JobQueueProvider protocol is properly defined."""

        class TestJobQueue:
            async def enqueue(
                self, job_type: str, job_data: dict[str, Any], priority: int = 0
            ) -> JobId:
                return "test-job-id"

            async def dequeue(self, worker_id: str) -> Job | None:
                return None

            async def complete(
                self, job_id: JobId, result: dict[str, Any] | None = None
            ) -> None:
                pass

            async def fail(self, job_id: JobId, error: str, retry: bool = True) -> None:
                pass

            async def get_incomplete_jobs(self) -> list[Job]:
                return []

        class TestJobQueueProvider:
            def create_job_queue(self, configuration: dict[str, Any]) -> JobQueue:
                return TestJobQueue()

        provider = TestJobQueueProvider()
        assert isinstance(provider, JobQueueProvider)

        queue = provider.create_job_queue({})
        assert isinstance(queue, JobQueue)

    def test_state_storage_protocol(self):
        """Test that StateStorage protocol is properly defined."""

        class TestStateStorage:
            def store(
                self, partition_key: str, key: str, value: Any, version: int = 1
            ) -> None:
                pass

            def get(self, partition_key: str, key: str, default: Any = None) -> Any:
                return default

            def get_versioned_state(
                self, partition_key: str, older_than_version: int
            ) -> list[tuple[str, Any, int]]:
                return []

            def get_all_keys_with_value(
                self, partition_key: str, value: Any
            ) -> list[str]:
                return []

        class TestStateStorageProvider:
            def create_state_storage(
                self, configuration: dict[str, Any]
            ) -> StateStorage:
                return TestStateStorage()

        provider = TestStateStorageProvider()
        assert isinstance(provider, StateStorageProvider)

        storage = provider.create_state_storage({})
        assert isinstance(storage, StateStorage)

    def test_state_manager_protocol(self):
        """Test that StateManager protocol is properly defined."""

        class TestStateManager:
            def store(self, key: str, value: Any, version: int = 1) -> None:
                pass

            def get(self, key: str, default: Any = None) -> Any:
                return default

            def get_versioned_state(
                self, older_than_version: int
            ) -> list[tuple[str, Any, int]]:
                return []

            def get_all_keys_with_value(self, value: Any) -> list[str]:
                return []

        manager = TestStateManager()
        assert isinstance(manager, StateManager)

    def test_cache_manager_protocol(self):
        """Test that CacheManager protocol is properly defined."""

        class TestCacheManager:
            async def save(
                self, partition_key: str, content: bytes | str
            ) -> CacheId:
                return "test-cache-id"

            async def get(
                self, partition_key: str, cache_id: CacheId
            ) -> bytes | str | None:
                return None

            async def remove(self, partition_key: str, cache_id: CacheId) -> bool:
                return False

            async def remove_all(
                self, partition_key: str, cache_ids: list[CacheId]
            ) -> list[CacheId]:
                return []

            async def get_all(self, partition_key: str) -> list[CacheId]:
                return []

        class TestCacheProvider:
            def create_cache(self, configuration: dict[str, Any]) -> CacheManager:
                return TestCacheManager()

        provider = TestCacheProvider()
        assert isinstance(provider, CacheProvider)

        cache = provider.create_cache({})
        assert isinstance(cache, CacheManager)


class TestPhase4Protocols:
    """Test Phase 4 singleton-using protocols."""

    def test_content_extractor_protocol(self):
        """Test that ContentExtractor protocol is properly defined."""

        class TestContentExtractor:
            def can_extract(self, url: str, mime_type: str | None = None) -> bool:
                return True

            def preferred_mime_types(self) -> list[str]:
                return ["text/plain"]

            async def extract(
                self,
                host,
                content: bytes | str,
                metadata: Metadata | None = None,
            ) -> None:
                pass

        extractor = TestContentExtractor()
        assert isinstance(extractor, ContentExtractor)
        assert extractor.can_extract("test.txt")
        assert extractor.preferred_mime_types() == ["text/plain"]

    def test_content_source_protocol(self):
        """Test that ContentSource protocol is properly defined."""

        class TestContentSource:
            async def start_source(self, host) -> None:
                pass

            async def stop_source(self, host) -> None:
                pass

        source = TestContentSource()
        assert isinstance(source, ContentSource)

    def test_content_fetcher_protocol(self):
        """Test that ContentFetcher protocol is properly defined."""

        class TestContentFetcher:
            def can_fetch(self, host, url: str) -> bool:
                return True

            async def fetch(self, host, url: str) -> None:
                pass

        fetcher = TestContentFetcher()
        assert isinstance(fetcher, ContentFetcher)
        assert fetcher.can_fetch(None, "http://test.com")

    def test_lifecycle_action_protocol(self):
        """Test that LifecycleAction protocol is properly defined."""

        class TestLifecycleAction:
            async def on_start(self, host) -> None:
                pass

            async def on_stop(self, host) -> None:
                pass

        action = TestLifecycleAction()
        assert isinstance(action, LifecycleAction)


class TestHostInterfaces:
    """Test host interface protocols."""

    def test_base_host_protocol(self):
        """Test that BaseHost protocol is properly defined."""

        class TestStateManager:
            def store(self, key: str, value: Any, version: int = 1) -> None:
                pass

            def get(self, key: str, default: Any = None) -> Any:
                return default

            def get_versioned_state(
                self, older_than_version: int
            ) -> list[tuple[str, Any, int]]:
                return []

            def get_all_keys_with_value(self, value: Any) -> list[str]:
                return []

        class TestBaseHost:
            @property
            def logger(self) -> Any:
                return None

            @property
            def configuration(self) -> dict[str, Any]:
                return {}

            @property
            def state(self) -> StateManager:
                return TestStateManager()

            def schedule_fetch(
                self, url: str, metadata: Metadata | None = None
            ) -> None:
                pass

        host = TestBaseHost()
        assert isinstance(host, BaseHost)
        assert host.configuration == {}
        assert isinstance(host.state, StateManager)

    def test_content_extractor_host_protocol(self):
        """Test that ContentExtractorHost protocol is properly defined."""

        class TestStorage:
            async def add_item(self, host, content: str, metadata: Metadata) -> ItemId:
                return "test-item"

            async def update_item(self, host, item_id: ItemId, content: str) -> None:
                pass

            async def update_metadata(
                self, host, item_id: ItemId, metadata: Metadata
            ) -> None:
                pass

            async def find_item_id(self, host, metadata: Metadata) -> ItemId | None:
                return None

            async def find_item(self, item_id: ItemId) -> Metadata | None:
                return None

            async def remove_item(self, host, item_id: ItemId) -> CacheId | None:
                return None

            async def remove_items_by_metadata(
                self, host, metadata: Metadata
            ) -> list[CacheId]:
                return []

            async def remove_items_by_url(self, host, url: str) -> list[CacheId]:
                return []

        class TestCacheManager:
            async def save(
                self, partition_key: str, content: bytes | str
            ) -> CacheId:
                return "test-cache-id"

            async def get(
                self, partition_key: str, cache_id: CacheId
            ) -> bytes | str | None:
                return None

            async def remove(self, partition_key: str, cache_id: CacheId) -> bool:
                return False

            async def remove_all(
                self, partition_key: str, cache_ids: list[CacheId]
            ) -> list[CacheId]:
                return []

            async def get_all(self, partition_key: str) -> list[CacheId]:
                return []

        class TestStateManager:
            def store(self, key: str, value: Any, version: int = 1) -> None:
                pass

            def get(self, key: str, default: Any = None) -> Any:
                return default

            def get_versioned_state(
                self, older_than_version: int
            ) -> list[tuple[str, Any, int]]:
                return []

            def get_all_keys_with_value(self, value: Any) -> list[str]:
                return []

        class TestContentExtractorHost:
            @property
            def logger(self) -> Any:
                return None

            @property
            def configuration(self) -> dict[str, Any]:
                return {}

            @property
            def state(self) -> StateManager:
                return TestStateManager()

            def schedule_fetch(
                self, url: str, metadata: Metadata | None = None
            ) -> None:
                pass

            @property
            def storage(self) -> DataStorage:
                return TestStorage()

            @property
            def cache(self) -> CacheManager:
                return TestCacheManager()

            def extract_file(
                self, content: bytes | str, metadata: Metadata
            ) -> None:
                pass

        host = TestContentExtractorHost()
        assert isinstance(host, ContentExtractorHost)
        assert isinstance(host, BaseHost)
        assert isinstance(host.storage, DataStorage)
        assert isinstance(host.cache, CacheManager)

    def test_content_source_host_protocol(self):
        """Test that ContentSourceHost protocol is properly defined."""

        class TestCacheManager:
            async def save(
                self, partition_key: str, content: bytes | str
            ) -> CacheId:
                return "test-cache-id"

            async def get(
                self, partition_key: str, cache_id: CacheId
            ) -> bytes | str | None:
                return None

            async def remove(self, partition_key: str, cache_id: CacheId) -> bool:
                return False

            async def remove_all(
                self, partition_key: str, cache_ids: list[CacheId]
            ) -> list[CacheId]:
                return []

            async def get_all(self, partition_key: str) -> list[CacheId]:
                return []

        class TestStateManager:
            def store(self, key: str, value: Any, version: int = 1) -> None:
                pass

            def get(self, key: str, default: Any = None) -> Any:
                return default

            def get_versioned_state(
                self, older_than_version: int
            ) -> list[tuple[str, Any, int]]:
                return []

            def get_all_keys_with_value(self, value: Any) -> list[str]:
                return []

        class TestContentSourceHost:
            @property
            def logger(self) -> Any:
                return None

            @property
            def configuration(self) -> dict[str, Any]:
                return {}

            @property
            def state(self) -> StateManager:
                return TestStateManager()

            def schedule_fetch(
                self, url: str, metadata: Metadata | None = None
            ) -> None:
                pass

            @property
            def cache(self) -> CacheManager:
                return TestCacheManager()

            def schedule_next_run(self, time_interval: timedelta) -> None:
                pass

        host = TestContentSourceHost()
        assert isinstance(host, ContentSourceHost)
        assert isinstance(host, BaseHost)
        assert isinstance(host.cache, CacheManager)

    def test_content_fetcher_host_protocol(self):
        """Test that ContentFetcherHost protocol is properly defined."""

        class TestCacheManager:
            async def save(
                self, partition_key: str, content: bytes | str
            ) -> CacheId:
                return "test-cache-id"

            async def get(
                self, partition_key: str, cache_id: CacheId
            ) -> bytes | str | None:
                return None

            async def remove(self, partition_key: str, cache_id: CacheId) -> bool:
                return False

            async def remove_all(
                self, partition_key: str, cache_ids: list[CacheId]
            ) -> list[CacheId]:
                return []

            async def get_all(self, partition_key: str) -> list[CacheId]:
                return []

        class TestStateManager:
            def store(self, key: str, value: Any, version: int = 1) -> None:
                pass

            def get(self, key: str, default: Any = None) -> Any:
                return default

            def get_versioned_state(
                self, older_than_version: int
            ) -> list[tuple[str, Any, int]]:
                return []

            def get_all_keys_with_value(self, value: Any) -> list[str]:
                return []

        class TestContentFetcherHost:
            @property
            def logger(self) -> Any:
                return None

            @property
            def configuration(self) -> dict[str, Any]:
                return {}

            @property
            def state(self) -> StateManager:
                return TestStateManager()

            def schedule_fetch(
                self, url: str, metadata: Metadata | None = None
            ) -> None:
                pass

            @property
            def cache(self) -> CacheManager:
                return TestCacheManager()

            def extract_file(
                self, content: bytes | str, metadata: Metadata
            ) -> None:
                pass

        host = TestContentFetcherHost()
        assert isinstance(host, ContentFetcherHost)
        assert isinstance(host, BaseHost)
        assert isinstance(host.cache, CacheManager)

    def test_data_storage_host_protocol(self):
        """Test that DataStorageHost protocol is properly defined."""

        class TestStateManager:
            def store(self, key: str, value: Any, version: int = 1) -> None:
                pass

            def get(self, key: str, default: Any = None) -> Any:
                return default

            def get_versioned_state(
                self, older_than_version: int
            ) -> list[tuple[str, Any, int]]:
                return []

            def get_all_keys_with_value(self, value: Any) -> list[str]:
                return []

        class TestDataStorageHost:
            @property
            def logger(self) -> Any:
                return None

            @property
            def configuration(self) -> dict[str, Any]:
                return {}

            @property
            def state(self) -> StateManager:
                return TestStateManager()

            def schedule_fetch(
                self, url: str, metadata: Metadata | None = None
            ) -> None:
                pass

        host = TestDataStorageHost()
        assert isinstance(host, DataStorageHost)
        assert isinstance(host, BaseHost)

    def test_lifecycle_host_protocol(self):
        """Test that LifecycleHost protocol is properly defined."""

        class TestStateManager:
            def store(self, key: str, value: Any, version: int = 1) -> None:
                pass

            def get(self, key: str, default: Any = None) -> Any:
                return default

            def get_versioned_state(
                self, older_than_version: int
            ) -> list[tuple[str, Any, int]]:
                return []

            def get_all_keys_with_value(self, value: Any) -> list[str]:
                return []

        class TestLifecycleHost:
            @property
            def logger(self) -> Any:
                return None

            @property
            def configuration(self) -> dict[str, Any]:
                return {}

            @property
            def state(self) -> StateManager:
                return TestStateManager()

            def schedule_fetch(
                self, url: str, metadata: Metadata | None = None
            ) -> None:
                pass

        host = TestLifecycleHost()
        assert isinstance(host, LifecycleHost)
        assert isinstance(host, BaseHost)


class TestProtocolInheritance:
    """Test that protocol inheritance works correctly."""

    def test_host_inheritance_chain(self):
        """Test that host protocols properly inherit from BaseHost."""

        # Create a comprehensive test implementation
        class TestStateManager:
            def store(self, key: str, value: Any, version: int = 1) -> None:
                pass

            def get(self, key: str, default: Any = None) -> Any:
                return default

            def get_versioned_state(
                self, older_than_version: int
            ) -> list[tuple[str, Any, int]]:
                return []

            def get_all_keys_with_value(self, value: Any) -> list[str]:
                return []

        class TestStorage:
            async def add_item(self, host, content: str, metadata: Metadata) -> ItemId:
                return "test-item"

            async def update_item(self, host, item_id: ItemId, content: str) -> None:
                pass

            async def update_metadata(
                self, host, item_id: ItemId, metadata: Metadata
            ) -> None:
                pass

            async def find_item_id(self, host, metadata: Metadata) -> ItemId | None:
                return None

            async def find_item(self, item_id: ItemId) -> Metadata | None:
                return None

            async def remove_item(self, host, item_id: ItemId) -> CacheId | None:
                return None

            async def remove_items_by_metadata(
                self, host, metadata: Metadata
            ) -> list[CacheId]:
                return []

            async def remove_items_by_url(self, host, url: str) -> list[CacheId]:
                return []

        class TestCacheManager:
            async def save(
                self, partition_key: str, content: bytes | str
            ) -> CacheId:
                return "test-cache-id"

            async def get(
                self, partition_key: str, cache_id: CacheId
            ) -> bytes | str | None:
                return None

            async def remove(self, partition_key: str, cache_id: CacheId) -> bool:
                return False

            async def remove_all(
                self, partition_key: str, cache_ids: list[CacheId]
            ) -> list[CacheId]:
                return []

            async def get_all(self, partition_key: str) -> list[CacheId]:
                return []

        class ComprehensiveHost:
            @property
            def logger(self) -> Any:
                return None

            @property
            def configuration(self) -> dict[str, Any]:
                return {}

            @property
            def state(self) -> StateManager:
                return TestStateManager()

            def schedule_fetch(
                self, url: str, metadata: Metadata | None = None
            ) -> None:
                pass

            @property
            def storage(self) -> DataStorage:
                return TestStorage()

            @property
            def cache(self) -> CacheManager:
                return TestCacheManager()

            def extract_file(
                self, content: bytes | str, metadata: Metadata
            ) -> None:
                pass

            def schedule_next_run(self, time_interval: timedelta) -> None:
                pass

        host = ComprehensiveHost()

        # Test that the comprehensive host satisfies all host interfaces
        assert isinstance(host, BaseHost)
        assert isinstance(host, ContentExtractorHost)
        assert isinstance(host, ContentSourceHost)
        assert isinstance(host, ContentFetcherHost)
        assert isinstance(host, DataStorageHost)
        assert isinstance(host, LifecycleHost)


@pytest.mark.asyncio
class TestAsyncProtocolMethods:
    """Test that async protocol methods work correctly."""

    async def test_data_storage_async_methods(self):
        """Test that DataStorage async methods work."""

        class TestDataStorage:
            async def add_item(self, host, content: str, metadata: Metadata) -> ItemId:
                return "test-item-id"

            async def update_item(self, host, item_id: ItemId, content: str) -> None:
                pass

            async def update_metadata(
                self, host, item_id: ItemId, metadata: Metadata
            ) -> None:
                pass

            async def find_item_id(self, host, metadata: Metadata) -> ItemId | None:
                return "found-item"

            async def find_item(self, item_id: ItemId) -> Metadata | None:
                return Metadata(source_url="test://example.com")

            async def remove_item(self, host, item_id: ItemId) -> CacheId | None:
                return "cache-id"

            async def remove_items_by_metadata(
                self, host, metadata: Metadata
            ) -> list[CacheId]:
                return ["cache1", "cache2"]

            async def remove_items_by_url(self, host, url: str) -> list[CacheId]:
                return ["cache3"]

        storage = TestDataStorage()
        metadata = Metadata(source_url="test://example.com")

        # Test async operations
        item_id = await storage.add_item(None, "test content", metadata)
        assert item_id == "test-item-id"

        found_id = await storage.find_item_id(None, metadata)
        assert found_id == "found-item"

        found_metadata = await storage.find_item(item_id)
        assert found_metadata is not None
        assert found_metadata.source_url == "test://example.com"

        cache_id = await storage.remove_item(None, item_id)
        assert cache_id == "cache-id"

        cache_ids = await storage.remove_items_by_metadata(None, metadata)
        assert cache_ids == ["cache1", "cache2"]

        url_cache_ids = await storage.remove_items_by_url(None, "test://example.com")
        assert url_cache_ids == ["cache3"]

    async def test_content_extractor_async_methods(self):
        """Test that ContentExtractor async methods work."""

        class TestContentExtractor:
            def can_extract(self, url: str, mime_type: str | None = None) -> bool:
                return url.endswith(".txt")

            def preferred_mime_types(self) -> list[str]:
                return ["text/plain"]

            async def extract(
                self,
                host,
                content: bytes | str,
                metadata: Metadata | None = None,
            ) -> None:
                # Simulate extraction
                pass

        extractor = TestContentExtractor()

        assert extractor.can_extract("test.txt")
        assert not extractor.can_extract("test.pdf")
        assert extractor.preferred_mime_types() == ["text/plain"]

        # Test async extraction
        await extractor.extract(
            None, "test content", Metadata(source_url="test://example.com")
        )
