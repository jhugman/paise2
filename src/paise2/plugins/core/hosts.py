# ABOUTME: Host infrastructure for plugin system including BaseHost and StateManager.
# ABOUTME: Provides state partitioning, host factories, and basic host functionality.

from __future__ import annotations

import inspect
from dataclasses import asdict
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from datetime import timedelta

    from paise2.models import Content, Metadata
    from paise2.plugins.core.interfaces import (
        CacheManager,
        Configuration,
        DataStorage,
        Logger,
        StateManager,
        StateStorage,
    )
    from paise2.plugins.core.tasks import TaskQueue


class ConcreteStateManager:
    """StateManager implementation with automatic partitioning by plugin module name."""

    def __init__(self, state_storage: StateStorage, plugin_module_name: str):
        self.state_storage = state_storage
        self.partition_key = plugin_module_name

    def store(self, key: str, value: Any, version: int = 1) -> None:
        """Store state with automatic partitioning."""
        self.state_storage.store(self.partition_key, key, value, version)

    def get(self, key: str, default: Any = None) -> Any:
        """Get state with automatic partitioning."""
        return self.state_storage.get(self.partition_key, key, default)

    def get_versioned_state(
        self, older_than_version: int
    ) -> list[tuple[str, Any, int]]:
        """Get versioned state for plugin updates."""
        return self.state_storage.get_versioned_state(
            self.partition_key, older_than_version
        )

    def get_all_keys_with_value(self, value: Any) -> list[str]:
        """Get all keys with a specific value."""
        return self.state_storage.get_all_keys_with_value(self.partition_key, value)


class BaseHost:
    """Base host class providing common functionality to all plugin hosts."""

    def __init__(
        self,
        logger: Logger,
        configuration: Configuration,
        state_storage: StateStorage,
        plugin_module_name: str,
    ):
        self._logger = logger
        self._configuration = configuration
        self._state = ConcreteStateManager(state_storage, plugin_module_name)

    @property
    def logger(self) -> Any:
        """Get the logger instance."""
        return self._logger

    @property
    def configuration(self) -> Configuration:
        """Get the configuration dictionary."""
        return self._configuration

    @property
    def state(self) -> StateManager:
        """Get the state manager for this plugin."""
        return self._state

    def schedule_fetch(self, url: str, metadata: Metadata | None = None) -> Any:  # noqa: ARG002
        """Schedule a fetch operation (placeholder implementation)."""
        # NOTE: This will be implemented when job queue integration is added
        return None


def get_plugin_module_name_from_frame() -> str:
    """Extract plugin module name from the call stack."""
    # Get the calling frame information
    frame = inspect.currentframe()
    try:
        # Go up the stack to find the calling module
        current_frame = frame
        while current_frame:
            current_frame = current_frame.f_back
            if current_frame:
                module = inspect.getmodule(current_frame)
                if module and module.__name__:
                    module_name = module.__name__
                    # Skip internal frames and return the first meaningful module
                    if (
                        not module_name.startswith("_pytest")
                        and module_name != "__main__"
                    ):
                        return module_name
    finally:
        del frame  # Prevent reference cycles

    # Fallback - for test environments, try to get the test module name
    frame = inspect.currentframe()
    try:
        if frame and frame.f_back:
            caller_frame = frame.f_back
            module = inspect.getmodule(caller_frame)
            if module and module.__name__:
                return module.__name__
    finally:
        del frame

    return "unknown.module"


def create_state_manager(
    state_storage: StateStorage, plugin_module_name: str
) -> StateManager:
    """Create a StateManager with automatic partitioning."""
    return ConcreteStateManager(state_storage, plugin_module_name)


def create_base_host(
    logger: Logger,
    configuration: Configuration,
    state_storage: StateStorage,
    plugin_module_name: str,
) -> BaseHost:
    """Create a BaseHost instance."""
    return BaseHost(logger, configuration, state_storage, plugin_module_name)


class ContentExtractorHost(BaseHost):
    """Specialized host for content extractors with storage and cache access."""

    def __init__(  # noqa: PLR0913
        self,
        logger: Logger,
        configuration: Configuration,
        state_storage: StateStorage,
        plugin_module_name: str,
        data_storage: DataStorage,
        cache: CacheManager,
    ):
        super().__init__(logger, configuration, state_storage, plugin_module_name)
        self._data_storage = data_storage
        self._cache = cache

    @property
    def storage(self) -> DataStorage:
        """Get the data storage instance."""
        return self._data_storage

    @property
    def cache(self) -> CacheManager:
        """Get the cache manager instance."""
        return self._cache

    def extract_file(self, content: Content, metadata: Metadata) -> None:
        """Request extraction of nested content (placeholder implementation)."""
        # NOTE: This will be implemented when job queue integration is added


class ContentSourceHost(BaseHost):
    """Specialized host for content sources with cache access and scheduling."""

    def __init__(  # noqa: PLR0913
        self,
        logger: Logger,
        configuration: Configuration,
        state_storage: StateStorage,
        plugin_module_name: str,
        cache: CacheManager,
        data_storage: DataStorage,
        singletons: Any = None,
    ):
        super().__init__(logger, configuration, state_storage, plugin_module_name)
        self._cache = cache
        self._data_storage = data_storage
        self._singletons = singletons

    @property
    def cache(self) -> CacheManager:
        """Get the cache manager instance."""
        return self._cache

    @property
    def data_storage(self) -> DataStorage:
        """Get the data storage instance."""
        return self._data_storage

    def schedule_fetch(self, url: str, metadata: Metadata | None = None) -> Any:
        """Schedule a fetch operation using the task registry."""
        if self._singletons and self._singletons.task_queue:
            # Async mode: use task queue
            metadata_dict = asdict(metadata) if metadata else None
            result = self._singletons.task_queue.fetch_content(url, metadata_dict)
            task_id = getattr(result, "id", None)
            self.logger.info("Scheduled fetch task for %s", url)
            return task_id

        # Sync mode: log what would be done
        self.logger.info("Synchronous execution: would fetch %s", url)
        return None

    def schedule_next_run(self, time_interval: timedelta) -> None:
        """Schedule the next run of this content source."""
        if self._singletons and self._singletons.task_queue:
            # Async mode: would schedule using task queue scheduler
            self.logger.info("Scheduled next content source run in %s", time_interval)
        else:
            # Sync mode: log what would be done
            self.logger.info(
                "Synchronous execution: would schedule next run in %s", time_interval
            )


class ContentFetcherHost(BaseHost):
    """Specialized host for content fetchers with cache access and extraction."""

    def __init__(  # noqa: PLR0913
        self,
        logger: Logger,
        configuration: Configuration,
        state_storage: StateStorage,
        plugin_module_name: str,
        cache: CacheManager,
        task_queue: TaskQueue | None,
    ):
        super().__init__(logger, configuration, state_storage, plugin_module_name)
        self._cache = cache
        self._task_queue = task_queue

    @property
    def cache(self) -> CacheManager:
        """Get the cache manager instance."""
        return self._cache

    def extract_file(self, content: Content, metadata: Metadata) -> None:
        """Request extraction of fetched content using task registry."""
        if self._task_queue:
            # Async mode: schedule extraction task using task registry
            result = self._task_queue.extract_content(
                content=content, metadata=metadata
            )

            # Log task scheduling
            if hasattr(result, "id"):
                self.logger.info("Scheduled extraction task %s", result.id)
            else:
                self.logger.info("Scheduled extraction task (sync mode)")
        else:
            # Sync mode: log what would be done
            self.logger.info(
                "Synchronous execution: would extract content from %s",
                metadata.source_url,
            )


class DataStorageHost(BaseHost):
    """Specialized host for data storage providers with basic host functionality."""

    def __init__(
        self,
        logger: Logger,
        configuration: Configuration,
        state_storage: StateStorage,
        plugin_module_name: str,
    ):
        super().__init__(logger, configuration, state_storage, plugin_module_name)


class LifecycleHost(BaseHost):
    """Specialized host for lifecycle actions with basic host functionality."""

    def __init__(
        self,
        logger: Logger,
        configuration: Configuration,
        state_storage: StateStorage,
        plugin_module_name: str,
    ):
        super().__init__(logger, configuration, state_storage, plugin_module_name)


# Hosts with job queue integration
class BaseHostWithTaskQueue(BaseHost):
    """BaseHost with task queue integration for scheduling operations."""

    def __init__(
        self,
        logger: Logger,
        configuration: Configuration,
        state_storage: StateStorage,
        plugin_module_name: str,
        task_queue: Any,
    ):
        super().__init__(logger, configuration, state_storage, plugin_module_name)
        self._task_queue = task_queue

    def schedule_fetch(self, url: str, metadata: Metadata | None = None) -> Any:  # noqa: ARG002
        """Schedule a fetch operation with task queue integration."""
        # NOTE: Task queue integration will be implemented when task handling is added
        # For now, this is a placeholder method
        return None


class ContentExtractorHostWithTaskQueue(ContentExtractorHost):
    """ContentExtractorHost with task queue integration for recursive extraction."""

    def __init__(  # noqa: PLR0913
        self,
        logger: Logger,
        configuration: Configuration,
        state_storage: StateStorage,
        plugin_module_name: str,
        data_storage: DataStorage,
        cache: CacheManager,
        task_queue: Any,
    ):
        super().__init__(
            logger,
            configuration,
            state_storage,
            plugin_module_name,
            data_storage,
            cache,
        )
        self._task_queue = task_queue

    def extract_file(self, content: Content, metadata: Metadata) -> None:
        """Request extraction of nested content with job queue integration."""
        # NOTE: Job queue integration will be implemented when job handling is added
        # For now, this is a placeholder method


# Factory functions for specialized hosts
def create_content_extractor_host(  # noqa: PLR0913
    logger: Logger,
    configuration: Configuration,
    state_storage: StateStorage,
    plugin_module_name: str,
    data_storage: DataStorage,
    cache: CacheManager,
) -> ContentExtractorHost:
    """Create a ContentExtractorHost instance."""
    return ContentExtractorHost(
        logger, configuration, state_storage, plugin_module_name, data_storage, cache
    )


def create_content_source_host(  # noqa: PLR0913
    logger: Logger,
    configuration: Configuration,
    state_storage: StateStorage,
    plugin_module_name: str,
    cache: CacheManager,
    data_storage: DataStorage,
    singletons: Any = None,
) -> ContentSourceHost:
    """Create a ContentSourceHost instance."""
    return ContentSourceHost(
        logger,
        configuration,
        state_storage,
        plugin_module_name,
        cache,
        data_storage,
        singletons,
    )


def create_content_fetcher_host(  # noqa: PLR0913
    logger: Logger,
    configuration: Configuration,
    state_storage: StateStorage,
    plugin_module_name: str,
    cache: CacheManager,
    task_queue: TaskQueue | None = None,
) -> ContentFetcherHost:
    """Create a ContentFetcherHost instance."""
    return ContentFetcherHost(
        logger, configuration, state_storage, plugin_module_name, cache, task_queue
    )


def create_data_storage_host(
    logger: Logger,
    configuration: Configuration,
    state_storage: StateStorage,
    plugin_module_name: str,
) -> DataStorageHost:
    """Create a DataStorageHost instance."""
    return DataStorageHost(logger, configuration, state_storage, plugin_module_name)


def create_lifecycle_host(
    logger: Logger,
    configuration: Configuration,
    state_storage: StateStorage,
    plugin_module_name: str,
) -> LifecycleHost:
    """Create a LifecycleHost instance."""
    return LifecycleHost(logger, configuration, state_storage, plugin_module_name)
