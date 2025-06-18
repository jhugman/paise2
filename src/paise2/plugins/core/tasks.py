from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from huey import Huey

if TYPE_CHECKING:
    from typing import Any

    from huey import Huey
    from huey.api import Result as HueyResult

    from paise2.models import Content, Metadata
    from paise2.plugins.core.startup import Singletons


__all__ = [
    "setup_tasks",
]


class TaskQueue:
    def __init__(self, huey: Huey, singletons: Singletons):
        self._huey = huey
        self._tasks = setup_tasks(huey, singletons)
        singletons.task_queue = self

    @property
    def huey(self) -> Huey:
        """Get the underlying Huey instance."""
        return self._huey

    def fetch_content(
        self,
        url: str,
        metadata: dict[str, Any] | None = None,
    ) -> HueyResult:
        return self._tasks["fetch_content"](url, metadata)

    def extract_content(self, content: Content, metadata: Metadata) -> HueyResult:
        return self._tasks["extract_content"](content, metadata)

    def store_content(self, content: Content, metadata: Metadata) -> HueyResult:
        return self._tasks["store_content"](content, metadata)

    def cleanup_cache(self, cache_ids: list[str]) -> HueyResult:
        return self._tasks["cleanup_cache"](cache_ids)


def setup_tasks(huey: Huey | None, singletons: Singletons) -> dict[str, Callable]:
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
    if huey is None:
        # No tasks for synchronous execution
        return {}

    @huey.task()  # type: ignore[misc]
    def fetch_content_task(
        url: str,
        metadata: dict[str, Any] | None = None,  # noqa: ARG001
    ) -> dict[str, Any]:
        """Fetch content using appropriate ContentFetcher plugin."""
        try:
            # Create ContentFetcher host
            from paise2.plugins.core.hosts import create_content_fetcher_host

            fetcher_host = create_content_fetcher_host(
                logger=singletons.logger,
                configuration=singletons.configuration,
                state_storage=singletons.state_storage,
                plugin_module_name="system",
                cache=singletons.cache,
                task_queue=None,  # Cannot pass self since it's being constructed
            )

            # Get all registered ContentFetchers
            fetchers = singletons.plugin_manager.get_content_fetchers()

            # Find first fetcher that can handle the URL
            selected_fetcher = None
            for fetcher in fetchers:
                if fetcher.can_fetch(fetcher_host, url):
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

            # Fetch content asynchronously
            _run_fetcher_async(selected_fetcher, fetcher_host, url, singletons.logger)

            return {"status": "success", "message": f"Fetched content from {url}"}  # noqa: TRY300

        except Exception as e:
            singletons.logger.error("Error in fetch_content_task: %s", e)  # noqa: TRY400
            return {"status": "error", "message": f"Error fetching content: {e}"}

    @huey.task()  # type: ignore[misc]
    def extract_content_task(
        content: bytes | str, metadata: dict[str, Any]
    ) -> dict[str, Any]:
        """Extract content using appropriate ContentExtractor plugin."""
        # Placeholder implementation - will be enhanced in future prompts
        # with actual ContentExtractor integration
        _ = content  # Will be used in future implementation
        _ = metadata  # Will be used in future implementation
        singletons.logger.info("Extract task scheduled")
        return {"status": "success", "message": "Content extraction completed"}

    @huey.task()  # type: ignore[misc]
    def store_content_task(
        content: dict[str, Any], metadata: dict[str, Any]
    ) -> dict[str, Any]:
        """Store processed content in the data storage."""
        # Placeholder implementation - will be enhanced in future prompts
        # with actual DataStorage integration
        _ = content  # Will be used in future implementation
        _ = metadata  # Will be used in future implementation
        singletons.logger.info("Store task scheduled for processed content")
        return {"status": "success", "message": "Content stored successfully"}

    @huey.task()  # type: ignore[misc]
    def cleanup_cache_task(cache_ids: list[str]) -> dict[str, Any]:
        """Clean up specified cache entries."""
        # Placeholder implementation - will be enhanced in future prompts
        # with actual cache cleanup integration
        count = len(cache_ids)
        singletons.logger.info("Cache cleanup task scheduled")
        return {"status": "success", "message": f"Cleaned up {count} cache entries"}

    return {
        "fetch_content": fetch_content_task,
        "extract_content": extract_content_task,
        "store_content": store_content_task,
        "cleanup_cache": cleanup_cache_task,
    }


def _run_fetcher_async(
    selected_fetcher: Any, fetcher_host: Any, url: str, logger: Any
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
