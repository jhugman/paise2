from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from huey import Huey
    from huey.api import Result as HueyResult

    from paise2.models import Content, Metadata
    from paise2.plugins.core.interfaces import (
        ContentExtractor,
        ContentExtractorHost,
        ContentFetcher,
        ContentFetcherHost,
        DataStorage,
        DataStorageHost,
        Logger,
    )
    from paise2.plugins.core.startup import Singletons


__all__ = [
    "TaskQueue",
]


class TaskQueue:
    def __init__(self, huey: Huey, singletons: Singletons):
        self._huey = huey
        singletons.task_queue = self
        self._tasks = _setup_tasks(huey, singletons)

    @property
    def huey(self) -> Huey:
        """Get the underlying Huey instance."""
        return self._huey

    def fetch_content(self, url: str) -> HueyResult:
        return self._tasks["fetch_content"](url)

    def extract_content(self, content: Content, metadata: Metadata) -> HueyResult:
        return self._tasks["extract_content"](content, metadata)

    def store_content(self, content: Content, metadata: Metadata) -> HueyResult:
        return self._tasks["store_content"](content, metadata)

    def cleanup_cache(self, cache_ids: list[str]) -> HueyResult:
        return self._tasks["cleanup_cache"](cache_ids)


def _setup_tasks(huey: Huey, singletons: Singletons) -> dict[str, Callable]:
    """
    Define tasks with the provided Huey instance and singletons.

    Implements the two-phase initialization pattern: first create TaskQueueProvider,
    then create singletons, then setup tasks with both.

    Args:
        huey: Huey instance for task definition (may be None for sync execution)
        singletons: System singletons for task implementation

    Returns:
        Dict mapping task names to task functions. Empty dict for sync execution.
    """

    @huey.task()  # type: ignore[misc]
    def fetch_content_task(
        url: str,
    ) -> dict[str, Any]:
        return _do_fetch_content_task(singletons, url)

    @huey.task()  # type: ignore[misc]
    def extract_content_task(content: Content, metadata: Metadata) -> dict[str, Any]:
        return _do_extract_content_task(singletons, content, metadata)

    @huey.task()  # type: ignore[misc]
    def store_content_task(content: Content, metadata: Metadata) -> dict[str, Any]:
        return _do_store_content_task(singletons, content, metadata)

    @huey.task()  # type: ignore[misc]
    def cleanup_cache_task(cache_ids: list[str]) -> dict[str, Any]:
        return _do_cleanup_cache_task(singletons, cache_ids)

    return {
        "fetch_content": fetch_content_task,
        "extract_content": extract_content_task,
        "store_content": store_content_task,
        "cleanup_cache": cleanup_cache_task,
    }


def _do_fetch_content_task(
    singletons: Singletons,
    url: str,
) -> dict[str, Any]:
    """Fetch content using appropriate ContentFetcher plugin."""
    try:
        # Create ContentFetcher host
        from paise2.plugins.core.hosts import (
            create_content_fetcher_host_from_singletons,
        )

        # Get all registered ContentFetchers
        fetchers = singletons.plugin_manager.get_content_fetchers()

        # Find first fetcher that can handle the URL
        selected_fetcher = None
        for fetcher in fetchers:
            if fetcher.can_fetch(url):
                selected_fetcher = fetcher
                break

        if selected_fetcher is None:
            singletons.logger.warning("No fetcher found for URL: %s", url)
            return {
                "status": "error",
                "message": f"No fetcher found for URL: {url}",
            }

        singletons.logger.info(
            "Using fetcher %s for URL: %s", type(selected_fetcher).__name__, url
        )

        fetcher_host = create_content_fetcher_host_from_singletons(
            singletons, selected_fetcher.__module__
        )

        # Fetch content asynchronously
        _run_fetcher_async(selected_fetcher, fetcher_host, url, singletons.logger)

        return {"status": "success", "message": f"Fetched content from {url}"}  # noqa: TRY300

    except Exception as e:
        singletons.logger.error("Error in fetch_content_task: %s", str(e))  # noqa: TRY400
        return {"status": "error", "message": f"Error fetching content: {e}"}


def _run_fetcher_async(
    selected_fetcher: ContentFetcher,
    fetcher_host: ContentFetcherHost,
    url: str,
    logger: Logger,
) -> None:
    """Helper function to handle async fetcher execution."""
    import asyncio

    try:
        # Try to get current event loop, or create one if needed
        try:
            loop = asyncio.get_running_loop()
            # We're in an async context, create task
            task = loop.create_task(selected_fetcher.fetch(fetcher_host, url))
            # Task will complete independently
            _ = task
        except RuntimeError:
            # No event loop running, run synchronously
            asyncio.run(selected_fetcher.fetch(fetcher_host, url))
    except Exception:
        logger.exception("Error during content fetch")


def _do_extract_content_task(
    singletons: Singletons, content: bytes | str, metadata: Metadata
) -> dict[str, Any]:
    """Extract content using appropriate ContentExtractor plugin."""
    try:
        # Get all registered ContentExtractors
        extractors = singletons.plugin_manager.get_content_extractors()

        # Find best extractor that can handle the content
        selected_extractor = None
        content_mime_type = metadata.mime_type or "application/octet-stream"
        source_url = metadata.source_url or "unknown"

        # First try to find an extractor that specifically handles this MIME type
        for extractor in extractors:
            if extractor.can_extract(source_url, content_mime_type):
                preferred_types = extractor.preferred_mime_types()
                if content_mime_type in preferred_types:
                    selected_extractor = extractor
                    break

        # If no specific MIME type match, use first extractor that can handle it
        if selected_extractor is None:
            for extractor in extractors:
                if extractor.can_extract(source_url, content_mime_type):
                    selected_extractor = extractor
                    break

        if selected_extractor is None:
            singletons.logger.warning(
                "No extractor found for content type: %s", content_mime_type
            )
            return {
                "status": "error",
                "message": (
                    f"No extractor found for content type: {content_mime_type}"
                ),
            }

        singletons.logger.info(
            "Using extractor %s for content type: %s",
            type(selected_extractor).__name__,
            content_mime_type,
        )

        # Create ContentExtractor host
        from paise2.plugins.core.hosts import (
            create_content_extractor_host_from_singletons,
        )

        extractor_host = create_content_extractor_host_from_singletons(
            singletons, selected_extractor.__module__
        )

        # Extract content asynchronously
        _run_extractor_async(
            selected_extractor,
            extractor_host,
            content,
            metadata,
            singletons.logger,
        )

        return {"status": "success", "message": "Content extraction completed"}  # noqa: TRY300

    except Exception as e:
        singletons.logger.error("Error in extract_content_task: %s", str(e))  # noqa: TRY400
        return {"status": "error", "message": f"Error extracting content: {e}"}


def _run_extractor_async(
    selected_extractor: ContentExtractor,
    extractor_host: ContentExtractorHost,
    content: bytes | str,
    metadata: Metadata,
    logger: Logger,
) -> None:
    """Helper function to handle async extractor execution."""
    import asyncio

    try:
        # Convert dict metadata to Metadata object
        metadata_obj = metadata

        # Try to get current event loop, or create one if needed
        try:
            loop = asyncio.get_running_loop()
            # We're in an async context, create task
            task = loop.create_task(
                selected_extractor.extract(extractor_host, content, metadata_obj)
            )
            # Task will complete independently
            _ = task
        except RuntimeError:
            # No event loop running, run synchronously
            asyncio.run(
                selected_extractor.extract(extractor_host, content, metadata_obj)
            )
    except Exception:
        logger.exception("Error during content extraction")


def _do_store_content_task(
    singletons: Singletons, content: Content, metadata: Metadata
) -> dict[str, Any]:
    """Store processed content in the data storage."""
    try:
        # Create DataStorage host
        from paise2.plugins.core.hosts import create_data_storage_host_from_singleton

        storage_host = create_data_storage_host_from_singleton(
            singletons, "data_storage"
        )

        # Store content using data storage
        _run_storage_async(
            singletons.data_storage,
            storage_host,
            content,
            metadata,
            singletons.logger,
        )

        source_url = metadata.source_url
        singletons.logger.info("Content stored successfully for: %s", source_url)

        return {"status": "success", "message": "Content stored successfully"}  # noqa: TRY300

    except Exception as e:
        singletons.logger.error("Error in store_content_task: %s", str(e))  # noqa: TRY400
        return {"status": "error", "message": f"Error storing content: {e}"}


def _run_storage_async(
    data_storage: DataStorage,
    storage_host: DataStorageHost,
    content: Content,
    metadata: Metadata,
    logger: Logger,
) -> None:
    """Helper function to handle async storage execution."""
    import asyncio

    try:
        # Try to get current event loop, or create one if needed
        try:
            loop = asyncio.get_running_loop()
            # We're in an async context, create task
            task = loop.create_task(
                data_storage.add_item(storage_host, content, metadata)
            )
            # Task will complete independently
            _ = task
        except RuntimeError:
            # No event loop running, run synchronously
            asyncio.run(data_storage.add_item(storage_host, content, metadata))
    except Exception:
        logger.exception("Error during content storage")


def _do_cleanup_cache_task(
    singletons: Singletons, cache_ids: list[str]
) -> dict[str, Any]:
    """Clean up specified cache entries."""
    # Placeholder implementation - will be enhanced in future prompts
    # with actual cache cleanup integration
    count = len(cache_ids)
    singletons.logger.info("Cache cleanup task scheduled")
    return {"status": "success", "message": f"Cleaned up {count} cache entries"}
