# ABOUTME: Core plugin interfaces and protocols for the PAISE2 plugin system
# ABOUTME: Uses structural typing with Protocol classes for clean plugin architecture

from __future__ import annotations

from dataclasses import dataclass
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Dict,
    Protocol,
    runtime_checkable,
)

if TYPE_CHECKING:
    from datetime import datetime, timedelta

    from paise2.models import CacheId, Content, ItemId, JobId, Metadata

# Type aliases for clarity
ConfigurationDict = Dict[str, Any]


@dataclass(frozen=True)
class ConfigurationDiff:
    """
    Represents the differences between two configuration states.

    Used to track changes during configuration reloads so plugins
    can react efficiently to configuration changes.
    """

    added: ConfigurationDict  # New configuration keys/sections
    removed: ConfigurationDict  # Removed configuration keys/sections
    modified: ConfigurationDict  # Changed configuration values
    unchanged: ConfigurationDict  # Configuration that remained the same


@runtime_checkable
class Configuration(Protocol):
    """
    Protocol for configuration access interface.

    Provides a structured way to access configuration values with
    support for typed lookups and default values.
    """

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value by key.

        Args:
            key: Configuration key (can be dotted path like 'plugin.setting')
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        ...

    def get_section(self, section: str) -> ConfigurationDict:
        """
        Get an entire configuration section.

        Args:
            section: Section name

        Returns:
            Dictionary containing all values in the section
        """
        ...

    def addition(self, key: str, default: Any = None) -> Any:
        """
        Get the additions at the key path from the last configuration reload.

        Args:
            key: Configuration key (can be dotted path like 'plugin.setting')
            default: Default value if no additions exist at that path

        Returns:
            Added configuration value or default
        """
        ...

    def removal(self, key: str, default: Any = None) -> Any:
        """
        Get the removals at the key path from the last configuration reload.

        Args:
            key: Configuration key (can be dotted path like 'plugin.setting')
            default: Default value if no removals exist at that path

        Returns:
            Removed configuration value or default
        """
        ...

    def has_changed(self, key: str) -> bool:
        """
        Check if a specific configuration key changed in the last reload.

        Args:
            key: Configuration key to check

        Returns:
            True if the key changed, False otherwise
        """
        ...

    @property
    def last_diff(self) -> ConfigurationDiff | None:
        """
        Get the last configuration diff from a reload operation.

        Returns:
            ConfigurationDiff object or None if no diff available
        """
        ...


# =============================================================================
# Phase 2: Singleton-Contributing Extension Points
# =============================================================================


@runtime_checkable
class ConfigurationProvider(Protocol):
    """
    Provides default configuration for a plugin.

    Plugins can contribute default configuration files that are merged
    with user configuration. When the system reloads configuration,
    it looks for configuration for each provider, and if not found,
    uses the default.
    """

    def get_default_configuration(self) -> str:
        """
        Return the default configuration as a YAML string with comments.

        Returns:
            YAML string containing the default configuration
        """
        ...

    def get_configuration_id(self) -> str:
        """
        Return a unique identifier for this configuration.

        Returns:
            Unique string identifier for this configuration
        """
        ...


@runtime_checkable
class DataStorageProvider(Protocol):
    """
    Provides a data storage backend for the system.

    Plugins can contribute different storage implementations
    (e.g., SQLite, PostgreSQL, Elasticsearch) that will be used
    to store indexed content and metadata.
    """

    def create_data_storage(self, configuration: Configuration) -> DataStorage:
        """
        Create a data storage instance using the provided configuration.

        Args:
            configuration: System configuration dictionary

        Returns:
            DataStorage instance
        """
        ...


@runtime_checkable
class DataStorage(Protocol):
    """
    Interface for storing and retrieving indexed content and metadata.

    Handles the persistence of processed content with proper metadata
    management and supports deduplication and cleanup operations.
    """

    async def add_item(
        self, host: DataStorageHost, content: str, metadata: Metadata
    ) -> ItemId:
        """
        Add a new item to storage.

        Args:
            host: Host interface for system interaction
            content: Text content to store
            metadata: Associated metadata

        Returns:
            Unique identifier for the stored item
        """
        ...

    async def update_item(
        self, host: DataStorageHost, item_id: ItemId, content: str
    ) -> None:
        """
        Update the content of an existing item.

        Args:
            host: Host interface for system interaction
            item_id: Identifier of item to update
            content: New content
        """
        ...

    async def update_metadata(
        self, host: DataStorageHost, item_id: ItemId, metadata: Metadata
    ) -> None:
        """
        Update the metadata of an existing item.

        Args:
            host: Host interface for system interaction
            item_id: Identifier of item to update
            metadata: New metadata
        """
        ...

    async def find_item_id(
        self, host: DataStorageHost, metadata: Metadata
    ) -> ItemId | None:
        """
        Find an item by its metadata.

        Args:
            host: Host interface for system interaction
            metadata: Metadata to search for

        Returns:
            Item ID if found, None otherwise
        """
        ...

    async def find_item(self, item_id: ItemId) -> Metadata | None:
        """
        Retrieve metadata for an item by its ID.

        Args:
            item_id: Identifier of item to retrieve

        Returns:
            Metadata if found, None otherwise
        """
        ...

    async def remove_item(
        self, host: DataStorageHost, item_id: ItemId
    ) -> CacheId | None:
        """
        Remove an item from storage.

        Args:
            host: Host interface for system interaction
            item_id: Identifier of item to remove

        Returns:
            Cache ID for cleanup, if any
        """
        ...

    async def remove_items_by_metadata(
        self, host: DataStorageHost, metadata: Metadata
    ) -> list[CacheId]:
        """
        Remove all items matching the given metadata.

        Args:
            host: Host interface for system interaction
            metadata: Metadata pattern to match

        Returns:
            List of cache IDs for cleanup
        """
        ...

    async def remove_items_by_url(
        self, host: DataStorageHost, url: str
    ) -> list[CacheId]:
        """
        Remove all items associated with a given URL.

        Args:
            host: Host interface for system interaction
            url: URL to match

        Returns:
            List of cache IDs for cleanup
        """
        ...


@dataclass(frozen=True)
class Job:
    """
    Represents a job in the job queue system.

    Jobs are the primary unit of work in the system, handling
    content fetching, extraction, and storage operations.
    """

    job_id: JobId
    job_type: str
    job_data: dict[str, Any]
    priority: int
    created_at: datetime
    worker_id: str | None = None


@runtime_checkable
class JobQueueProvider(Protocol):
    """
    Provides job queue implementation for the system.

    Plugins can contribute different job queue backends
    (e.g., synchronous, SQLite-based, Redis-based) for handling
    asynchronous work processing.
    """

    def create_job_queue(
        self, configuration: Configuration, job_executor: JobExecutor | None = None
    ) -> JobQueue:
        """
        Create a job queue instance using the provided configuration.

        Args:
            configuration: System configuration dictionary
            job_executor: Optional job executor for immediate execution
                         (required for synchronous queues, ignored for persistent)

        Returns:
            JobQueue instance
        """
        ...


@runtime_checkable
class JobQueue(Protocol):
    """
    Interface for job queue operations.

    Handles queueing, dequeuing, and tracking of jobs for
    asynchronous processing of content operations.
    """

    async def enqueue(
        self, job_type: str, job_data: dict[str, Any], priority: int = 0
    ) -> JobId:
        """
        Add a new job to the queue.

        Args:
            job_type: Type of job (e.g., 'fetch_content', 'extract_content')
            job_data: Job-specific data
            priority: Job priority (higher numbers = higher priority)

        Returns:
            Unique identifier for the enqueued job
        """
        ...

    async def dequeue(self, worker_id: str) -> Job | None:
        """
        Get the next job from the queue for processing.

        Args:
            worker_id: Identifier of the worker requesting the job

        Returns:
            Next job to process, or None if queue is empty
        """
        ...

    async def complete(
        self, job_id: JobId, result: dict[str, Any] | None = None
    ) -> None:
        """
        Mark a job as completed.

        Args:
            job_id: Identifier of the completed job
            result: Optional result data from job processing
        """
        ...

    async def fail(self, job_id: JobId, error: str, retry: bool = True) -> None:
        """
        Mark a job as failed.

        Args:
            job_id: Identifier of the failed job
            error: Error message describing the failure
            retry: Whether the job should be retried
        """
        ...

    async def get_incomplete_jobs(self) -> list[Job]:
        """
        Get all jobs that are not yet completed.

        Returns:
            List of incomplete jobs
        """
        ...


@runtime_checkable
class JobExecutor(Protocol):
    """
    Interface for executing jobs by routing them to appropriate handlers.

    Provides the core job execution logic that can be used by both
    synchronous queues (immediate execution) and persistent queues
    (worker-based execution).
    """

    async def execute_job(self, job: Job) -> dict[str, Any]:
        """
        Execute a job and return the result.

        Args:
            job: Job to execute

        Returns:
            Job execution result data

        Raises:
            ValueError: If no handler is registered for the job type
            Exception: Any exception from the job handler
        """
        ...

    def register_handler(
        self,
        job_type: str,
        handler: Callable[[dict[str, Any]], Awaitable[dict[str, Any]]],
    ) -> None:
        """
        Register a handler function for a specific job type.

        Args:
            job_type: Type of job this handler can process
            handler: Async function that takes job_data and returns result
        """
        ...

    def get_registered_types(self) -> list[str]:
        """
        Get list of job types that have registered handlers.

        Returns:
            List of job types with handlers
        """
        ...


@runtime_checkable
class StateStorageProvider(Protocol):
    """
    Provides state storage implementation for plugin persistence.

    Plugins can contribute different state storage backends
    for persisting plugin state between system runs.
    """

    def create_state_storage(self, configuration: Configuration) -> StateStorage:
        """
        Create a state storage instance using the provided configuration.

        Args:
            configuration: System configuration dictionary

        Returns:
            StateStorage instance
        """
        ...


@runtime_checkable
class StateStorage(Protocol):
    """
    Interface for plugin state persistence.

    Provides versioned state storage with automatic partitioning
    by plugin module name for isolation.
    """

    def store(self, partition_key: str, key: str, value: Any, version: int = 1) -> None:
        """
        Store a value with versioning support.

        Args:
            partition_key: Partition identifier (typically plugin module name)
            key: Key to store value under
            value: Value to store
            version: Version number for migration support
        """
        ...

    def get(self, partition_key: str, key: str, default: Any = None) -> Any:
        """
        Retrieve a stored value.

        Args:
            partition_key: Partition identifier
            key: Key to retrieve
            default: Default value if not found

        Returns:
            Stored value or default
        """
        ...

    def get_versioned_state(
        self, partition_key: str, older_than_version: int
    ) -> list[tuple[str, Any, int]]:
        """
        Get all state entries older than a specific version.

        Args:
            partition_key: Partition identifier
            older_than_version: Version threshold

        Returns:
            List of (key, value, version) tuples
        """
        ...

    def get_all_keys_with_value(self, partition_key: str, value: Any) -> list[str]:
        """
        Find all keys that have a specific value.

        Args:
            partition_key: Partition identifier
            value: Value to search for

        Returns:
            List of keys with the specified value
        """
        ...


@runtime_checkable
class StateManager(Protocol):
    """
    Provides convenient state management with automatic partitioning.

    Wraps StateStorage with automatic partitioning by plugin module name,
    providing a clean interface for plugins to manage their state.
    """

    def store(self, key: str, value: Any, version: int = 1) -> None:
        """
        Store a value in the plugin's partition.

        Args:
            key: Key to store value under
            value: Value to store
            version: Version number for migration support
        """
        ...

    def get(self, key: str, default: Any = None) -> Any:
        """
        Retrieve a value from the plugin's partition.

        Args:
            key: Key to retrieve
            default: Default value if not found

        Returns:
            Stored value or default
        """
        ...

    def get_versioned_state(
        self, older_than_version: int
    ) -> list[tuple[str, Any, int]]:
        """
        Get all state entries older than a specific version.

        Args:
            older_than_version: Version threshold

        Returns:
            List of (key, value, version) tuples
        """
        ...

    def get_all_keys_with_value(self, value: Any) -> list[str]:
        """
        Find all keys that have a specific value.

        Args:
            value: Value to search for

        Returns:
            List of keys with the specified value
        """
        ...


@runtime_checkable
class CacheProvider(Protocol):
    """
    Provides cache implementation for temporary storage.

    Plugins can contribute different caching backends
    for storing temporary data and fetched content.
    """

    def create_cache(self, configuration: Configuration) -> CacheManager:
        """
        Create a cache manager instance using the provided configuration.

        Args:
            configuration: System configuration dictionary

        Returns:
            CacheManager instance
        """
        ...


@runtime_checkable
class CacheManager(Protocol):
    """
    Interface for cache operations.

    Provides partitioned caching with automatic cleanup
    and content management.
    """

    async def save(
        self, partition_key: str, content: Content, file_extension: str = ""
    ) -> CacheId:
        """
        Save content to cache and return a cache ID.

        Args:
            partition_key: Partition identifier (typically plugin module name)
            content: Content to cache

        Returns:
            Unique cache identifier
        """
        ...

    async def get(self, cache_id: CacheId) -> Content | None:
        """
        Retrieve content from cache by ID.

        Args:
            cache_id: Cache identifier

        Returns:
            Cached content if found, None otherwise
        """
        ...

    async def remove(self, cache_id: CacheId) -> bool:
        """
        Remove content from cache.

        Args:
            cache_id: Cache identifier

        Returns:
            True if removed, False if not found
        """
        ...

    async def remove_all(self, cache_ids: list[CacheId]) -> list[CacheId]:
        """
        Remove multiple cache entries.

        Args:
            cache_ids: List of cache identifiers to remove

        Returns:
            List of cache IDs that were not removed
        """
        ...

    async def get_all(self, partition_key: str) -> list[CacheId]:
        """
        Get all cache IDs for a partition.

        Args:
            partition_key: Partition identifier

        Returns:
            List of all cache IDs in the partition
        """
        ...


# =============================================================================
# Phase 4: Singleton-Using Extension Points
# =============================================================================


@runtime_checkable
class ContentExtractor(Protocol):
    """
    Extracts content from files or data streams.

    ContentExtractors know how to extract one or more content items
    from a given file. They are called after content is fetched,
    with the host system identifying the best extension based on
    file extension, MIME type, and heuristics.
    """

    def can_extract(self, url: str, mime_type: str | None = None) -> bool:
        """
        Determine if this extractor can handle the given content.

        Args:
            url: Source URL or path
            mime_type: Optional MIME type of the content

        Returns:
            True if this extractor can handle the content
        """
        ...

    def preferred_mime_types(self) -> list[str]:
        """
        Return list of MIME types this extractor prefers to handle.

        Returns:
            List of MIME type strings
        """
        ...

    async def extract(
        self,
        host: ContentExtractorHost,
        content: bytes | str,
        metadata: Metadata | None = None,
    ) -> None:
        """
        Extract content and add it to the system.

        Args:
            host: Host interface for system interaction
            content: Content to extract from
            metadata: Optional metadata about the content
        """
        ...


@runtime_checkable
class ContentSource(Protocol):
    """
    Generates lists of content to be fetched and indexed.

    ContentSources extract lists of files or URLs from human-writable
    local configuration. They take app configuration (YAML files) and
    derive a list of files to fetch, using the host to schedule those
    files for fetching.
    """

    async def start_source(self, host: ContentSourceHost) -> None:
        """
        Start the content source and begin scheduling content for fetching.

        Args:
            host: Host interface for system interaction
        """
        ...

    async def stop_source(self, host: ContentSourceHost) -> None:
        """
        Stop the content source and clean up any resources.

        Args:
            host: Host interface for system interaction
        """
        ...


@runtime_checkable
class ContentFetcher(Protocol):
    """
    Fetches content from URLs or file paths.

    ContentFetchers transform URLs or file paths into content for the
    ContentExtractor system. The host system chooses the best extension
    using scheme, URL patterns, or extension-specific methods.
    """

    def can_fetch(self, host: ContentFetcherHost, url: str) -> bool:
        """
        Determine if this fetcher can handle the given URL.

        Args:
            host: Host interface for system interaction
            url: URL to potentially fetch

        Returns:
            True if this fetcher can handle the URL
        """
        ...

    async def fetch(self, host: ContentFetcherHost, url: str) -> None:
        """
        Fetch content from URL and pass it to extraction.

        Args:
            host: Host interface for system interaction
            url: URL to fetch content from
        """
        ...


@runtime_checkable
class LifecycleAction(Protocol):
    """
    Receives notifications about system lifecycle events.

    LifecycleActions are informed about system events like
    startup and shutdown, allowing plugins to perform initialization
    and cleanup tasks.
    """

    async def on_start(self, host: LifecycleHost) -> None:
        """
        Called when the system starts up.

        Args:
            host: Host interface for system interaction
        """
        ...

    async def on_stop(self, host: LifecycleHost) -> None:
        """
        Called when the system shuts down.

        Args:
            host: Host interface for system interaction
        """
        ...


# =============================================================================
# Host Interfaces
# =============================================================================


@runtime_checkable
class BaseHost(Protocol):
    """
    Base interface for all plugin hosts.

    Provides common functionality that all plugin hosts share,
    including logging, configuration access, state management,
    and basic content scheduling.
    """

    @property
    def logger(self) -> Any:  # Will be Logger when implemented
        """
        System logger for plugin use.

        Returns:
            Logger instance
        """
        ...

    @property
    def configuration(self) -> Configuration:
        """
        Merged system configuration.

        Returns:
            Configuration instance
        """
        ...

    @property
    def state(self) -> StateManager:
        """
        State manager with automatic plugin partitioning.

        Returns:
            StateManager instance for this plugin
        """
        ...

    def schedule_fetch(self, url: str, metadata: Metadata | None = None) -> None:
        """
        Schedule content to be fetched.

        Args:
            url: URL to fetch
            metadata: Optional metadata about the content
        """
        ...


@runtime_checkable
class ContentExtractorHost(BaseHost, Protocol):
    """
    Host interface for content extractors.

    Provides content extractors with access to storage and cache
    for persisting extracted content.
    """

    @property
    def storage(self) -> DataStorage:
        """
        Data storage for persisting extracted content.

        Returns:
            DataStorage instance
        """
        ...

    @property
    def cache(self) -> CacheManager:
        """
        Cache manager for temporary storage.

        Returns:
            CacheManager instance
        """
        ...

    def extract_file(self, content: bytes | str, metadata: Metadata) -> None:
        """
        Request extraction of nested content.

        Args:
            content: Content to extract
            metadata: Metadata about the content
        """
        ...


@runtime_checkable
class ContentSourceHost(BaseHost, Protocol):
    """
    Host interface for content sources.

    Provides content sources with cache access and scheduling
    capabilities for periodic operations.
    """

    @property
    def cache(self) -> CacheManager:
        """
        Cache manager for temporary storage.

        Returns:
            CacheManager instance
        """
        ...

    def schedule_next_run(self, time_interval: timedelta) -> None:
        """
        Schedule the next run of this content source.

        Args:
            time_interval: Time until next run
        """
        ...


@runtime_checkable
class ContentFetcherHost(BaseHost, Protocol):
    """
    Host interface for content fetchers.

    Provides content fetchers with cache access and extraction
    capabilities for processing fetched content.
    """

    @property
    def cache(self) -> CacheManager:
        """
        Cache manager for temporary storage.

        Returns:
            CacheManager instance
        """
        ...

    def extract_file(self, content: bytes | str, metadata: Metadata) -> None:
        """
        Request extraction of fetched content.

        Args:
            content: Content to extract
            metadata: Metadata about the content
        """
        ...


@runtime_checkable
class DataStorageHost(BaseHost, Protocol):
    """
    Host interface for data storage providers.

    Provides data storage implementations with basic host functionality.
    """


@runtime_checkable
class LifecycleHost(BaseHost, Protocol):
    """
    Host interface for lifecycle actions.

    Provides lifecycle actions with basic host functionality.
    """
