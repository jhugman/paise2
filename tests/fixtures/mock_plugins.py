# ABOUTME: Mock plugin implementations for testing the plugin registration system
# ABOUTME: Simple plugin implementations that demonstrate each extension point

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

import pluggy

from paise2.models import Metadata
from paise2.plugins.core.interfaces import Job

if TYPE_CHECKING:
    from paise2.plugins.core.interfaces import (
        CacheManager,
        Configuration,
        ContentExtractorHost,
        ContentFetcherHost,
        ContentSourceHost,
        DataStorage,
        JobQueue,
        LifecycleHost,
        StateStorage,
    )


# Test Configuration Provider
class MockConfigurationProvider:
    """Mock configuration provider for plugin registration testing."""

    def get_default_configuration(self) -> str:
        return """
# Test plugin configuration
test_plugin:
  enabled: true
  max_items: 100
  log_level: debug
"""

    def get_configuration_id(self) -> str:
        return "test_plugin"


# Test Content Extractor
class MockContentExtractor:
    """Test content extractor for plugin registration testing."""

    def can_extract(self, url: str, mime_type: str | None = None) -> bool:
        """Can extract test content from any URL."""
        return url.startswith("test://") or bool(mime_type and "test" in mime_type)

    def preferred_mime_types(self) -> list[str]:
        """Returns preferred MIME types."""
        return ["text/test", "application/test"]

    async def extract(
        self,
        host: ContentExtractorHost,
        content: bytes | str,
        metadata: Metadata | None = None,
    ) -> None:
        """Extract test content and store it."""
        if metadata is None:
            metadata = Metadata(source_url="test://unknown")

        # Simulate extraction by creating text content
        if isinstance(content, bytes):
            text_content = content.decode("utf-8", errors="ignore")
        else:
            text_content = content

        # Add extracted content to storage
        extracted_metadata = metadata.copy(
            title=f"Extracted: {metadata.source_url}", processing_state="completed"
        )

        await host.storage.add_item(host, text_content, extracted_metadata)


# Test Content Source
class MockContentSource:
    """Test content source for plugin registration testing."""

    async def start_source(self, host: ContentSourceHost) -> None:
        """Start the test content source and schedule some test URLs."""
        # Schedule some test content for fetching
        test_urls = [
            "test://document1.txt",
            "test://document2.txt",
            "test://document3.txt",
        ]

        for url in test_urls:
            metadata = Metadata(
                source_url=url,
                title=f"Test Document: {url}",
                processing_state="pending",
            )
            host.schedule_fetch(url, metadata)

    async def stop_source(self, host: ContentSourceHost) -> None:
        """Stop the test content source."""
        # Nothing to clean up for test source


# Test Content Fetcher
class MockContentFetcher:
    """Test content fetcher for plugin registration testing."""

    def can_fetch(self, host: ContentFetcherHost, url: str) -> bool:
        """Can fetch URLs that start with test://"""
        return url.startswith("test://")

    async def fetch(self, host: ContentFetcherHost, url: str) -> None:
        """Fetch test content and pass it to extraction."""
        # Simulate fetching content
        if "document1" in url:
            content = "This is test document 1 content"
        elif "document2" in url:
            content = "This is test document 2 content"
        elif "document3" in url:
            content = "This is test document 3 content"
        else:
            content = f"Generic test content for {url}"

        # Create metadata
        metadata = Metadata(
            source_url=url,
            title=f"Fetched: {url}",
            mime_type="text/test",
            processing_state="fetching",
        )

        # Pass to extraction
        host.extract_file(content, metadata)


# Test Lifecycle Action
class MockLifecycleAction:
    """Test lifecycle action for plugin registration testing."""

    async def on_start(self, host: LifecycleHost) -> None:
        """Handle system startup."""
        host.logger.info("Test lifecycle action: System starting up")

    async def on_stop(self, host: LifecycleHost) -> None:
        """Handle system shutdown."""
        host.logger.info("Test lifecycle action: System shutting down")


# Test Data Storage Provider
class MockDataStorageProvider:
    """Test data storage provider for plugin registration testing."""

    def create_data_storage(self, configuration: Configuration) -> DataStorage:
        """Create a test data storage implementation."""
        return MockDataStorage()


class MockDataStorage:
    """Test data storage implementation."""

    def __init__(self) -> None:
        self._items: dict[str, tuple[str, Metadata]] = {}
        self._next_id = 1

    async def add_item(self, host: Any, content: str, metadata: Metadata) -> str:
        """Add an item to test storage."""
        item_id = f"test_item_{self._next_id}"
        self._next_id += 1
        self._items[item_id] = (content, metadata)
        return item_id

    async def update_item(self, host: Any, item_id: str, content: str) -> None:
        """Update an item in test storage."""
        if item_id in self._items:
            _, metadata = self._items[item_id]
            self._items[item_id] = (content, metadata)

    async def update_metadata(
        self, host: Any, item_id: str, metadata: Metadata
    ) -> None:
        """Update metadata for an item."""
        if item_id in self._items:
            content, _ = self._items[item_id]
            self._items[item_id] = (content, metadata)

    async def find_item_id(self, host: Any, metadata: Metadata) -> str | None:
        """Find item ID by metadata."""
        for item_id, (_, stored_metadata) in self._items.items():
            if stored_metadata.source_url == metadata.source_url:
                return item_id
        return None

    async def find_item(self, item_id: str) -> Metadata:
        """Find item metadata by ID."""
        if item_id in self._items:
            _, metadata = self._items[item_id]
            return metadata
        msg = f"Item not found: {item_id}"
        raise KeyError(msg)

    async def remove_item(self, host: Any, item_id: str) -> str | None:
        """Remove an item from storage."""
        if item_id in self._items:
            del self._items[item_id]
            return f"cache_{item_id}"  # Return cache ID for cleanup
        return None

    async def remove_items_by_metadata(
        self, host: Any, metadata: Metadata
    ) -> list[str]:
        """Remove items by metadata criteria."""
        to_remove = []
        cache_ids = []
        for item_id, (_, stored_metadata) in self._items.items():
            if stored_metadata.source_url == metadata.source_url:
                to_remove.append(item_id)
                cache_ids.append(f"cache_{item_id}")

        for item_id in to_remove:
            del self._items[item_id]

        return cache_ids

    async def remove_items_by_url(self, host: Any, url: str) -> list[str]:
        """Remove items by URL."""
        metadata = Metadata(source_url=url)
        return await self.remove_items_by_metadata(host, metadata)


# Test Job Queue Provider
class MockJobQueueProvider:
    """Test job queue provider for plugin registration testing."""

    def create_job_queue(self, configuration: Configuration) -> JobQueue:
        """Create a test job queue implementation."""
        return MockJobQueue()


class MockJobQueue:
    """Test job queue implementation (synchronous for testing)."""

    def __init__(self) -> None:
        self._jobs: list[Job] = []
        self._next_id = 1

    async def enqueue(self, job_type: str, job_data: dict, priority: int = 0) -> str:
        """Enqueue a job for testing."""
        job_id = f"test_job_{self._next_id}"
        self._next_id += 1

        job = Job(
            job_id=job_id,
            job_type=job_type,
            job_data=job_data,
            priority=priority,
            created_at=datetime.now(),
        )
        self._jobs.append(job)
        return job_id

    async def dequeue(self, worker_id: str) -> Job | None:
        """Dequeue a job for processing."""
        for job in self._jobs:
            if not hasattr(job, "worker_id") or job.worker_id is None:
                # Create a new Job with worker_id since Job is frozen
                updated_job = Job(
                    job_id=job.job_id,
                    job_type=job.job_type,
                    job_data=job.job_data,
                    priority=job.priority,
                    created_at=job.created_at,
                    worker_id=worker_id,
                )
                # Replace in the list
                job_index = self._jobs.index(job)
                self._jobs[job_index] = updated_job
                return updated_job
        return None

    async def complete(self, job_id: str, result: dict | None = None) -> None:
        """Mark a job as completed."""
        # Remove completed jobs from the list for simplicity in tests
        self._jobs = [job for job in self._jobs if job.job_id != job_id]

    async def fail(self, job_id: str, error: str, retry: bool = True) -> None:
        """Handle job failure."""
        # For testing, just remove failed jobs
        self._jobs = [job for job in self._jobs if job.job_id != job_id]

    async def get_incomplete_jobs(self) -> list[Job]:
        """Get all incomplete jobs."""
        return [job for job in self._jobs if job.worker_id is None]


# Test State Storage Provider
class MockStateStorageProvider:
    """Test state storage provider for plugin registration testing."""

    def create_state_storage(self, configuration: Configuration) -> StateStorage:
        """Create a test state storage implementation."""
        return MockStateStorage()


class MockStateStorage:
    """Test state storage implementation."""

    def __init__(self) -> None:
        self._state: dict[str, dict[str, tuple]] = {}

    def store(self, partition_key: str, key: str, value: Any, version: int = 1) -> None:
        """Store state with partitioning."""
        if partition_key not in self._state:
            self._state[partition_key] = {}
        self._state[partition_key][key] = (value, version)

    def get(self, partition_key: str, key: str, default: Any = None) -> Any:
        """Get state value."""
        if partition_key in self._state and key in self._state[partition_key]:
            value, _ = self._state[partition_key][key]
            return value
        return default

    def get_versioned_state(
        self, partition_key: str, older_than_version: int
    ) -> list[tuple[str, Any, int]]:
        """Get state entries older than specified version."""
        result = []
        if partition_key in self._state:
            for key, (value, version) in self._state[partition_key].items():
                if version < older_than_version:
                    result.append((key, value, version))
        return result

    def get_all_keys_with_value(self, partition_key: str, value: Any) -> list[str]:
        """Get all keys that have the specified value."""
        result = []
        if partition_key in self._state:
            for key, (stored_value, _) in self._state[partition_key].items():
                if stored_value == value:
                    result.append(key)
        return result


class MockStateManager:
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


# Test Cache Provider
class MockCacheProvider:
    """Test cache provider for plugin registration testing."""

    def create_cache(self, configuration: Configuration) -> CacheManager:
        """Create a test cache manager implementation."""
        return MockCacheManager()


class MockCacheManager:
    """Test cache manager implementation."""

    def __init__(self) -> None:
        self._cache: dict[str, bytes | str] = {}
        self._next_id = 1

    def _prefix(self, partition_key: str) -> str:
        return f"cache_{partition_key}_"

    async def save(
        self, partition_key: str, content: bytes | str, file_extension: str = ""
    ) -> str:
        """Save content to cache."""
        prefix = self._prefix(partition_key)
        cache_id = f"{prefix}{self._next_id}"
        self._next_id += 1
        self._cache[cache_id] = content
        return cache_id

    async def get(self, cache_id: str) -> bytes | str:
        """Get content from cache."""
        if cache_id in self._cache:
            return self._cache[cache_id]
        msg = f"Cache entry not found: {cache_id}"
        raise KeyError(msg)

    async def remove(self, cache_id: str) -> bool:
        """Remove content from cache."""
        if cache_id in self._cache:
            del self._cache[cache_id]
            return True
        return False

    async def remove_all(self, cache_ids: list[str]) -> list[str]:
        """Remove multiple cache entries."""
        unremoved = []
        for cache_id in cache_ids:
            if cache_id in self._cache:
                del self._cache[cache_id]
            else:
                unremoved.append(cache_id)
        return unremoved

    async def get_all(self, partition_key: str) -> list[str]:
        """Get all cache IDs for a partition."""
        prefix = self._prefix(partition_key)
        return [k for k in self._cache if k.startswith(prefix)]


# Plugin registration functions using @hookimpl
hookimpl = pluggy.HookimplMarker("paise2")


@hookimpl
def register_configuration_provider(register: Any) -> None:
    """Register mock configuration provider."""
    register(MockConfigurationProvider())


@hookimpl
def register_content_extractor(register: Any) -> None:
    """Register mock content extractor."""
    register(MockContentExtractor())


@hookimpl
def register_content_source(register: Any) -> None:
    """Register mock content source."""
    register(MockContentSource())


@hookimpl
def register_content_fetcher(register: Any) -> None:
    """Register mock content fetcher."""
    register(MockContentFetcher())


@hookimpl
def register_lifecycle_action(register: Any) -> None:
    """Register mock lifecycle action."""
    register(MockLifecycleAction())


@hookimpl
def register_data_storage_provider(register: Any) -> None:
    """Register mock data storage provider."""
    register(MockDataStorageProvider())


@hookimpl
def register_job_queue_provider(register: Any) -> None:
    """Register mock job queue provider."""
    register(MockJobQueueProvider())


@hookimpl
def register_state_storage_provider(register: Any) -> None:
    """Register mock state storage provider."""
    register(MockStateStorageProvider())


@hookimpl
def register_cache_provider(register: Any) -> None:
    """Register mock cache provider."""
    register(MockCacheProvider())
