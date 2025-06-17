# ABOUTME: ContentSource plugin implementations for discovering and monitoring content.
# ABOUTME: Provides DirectoryWatcherContentSource for local file monitoring.

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

import pluggy

from paise2.models import Metadata

if TYPE_CHECKING:
    from paise2.plugins.core.interfaces import ContentSource, ContentSourceHost

# Plugin registration hookimpl decorator
hookimpl = pluggy.HookimplMarker("paise2")


class DirectoryWatcherContentSource:
    """ContentSource that monitors a directory for file changes."""

    def __init__(
        self,
        watch_directory: str = ".",
        file_extensions: list[str] | None = None,
    ):
        """
        Initialize directory watcher.

        Args:
            watch_directory: Directory to monitor for files
            file_extensions: List of file extensions to watch (e.g., ['.txt', '.md'])
                           If None, watches all files
        """
        self.watch_directory = Path(watch_directory).expanduser().resolve()
        self.file_extensions = file_extensions or []

    async def discover_content(
        self, host: ContentSourceHost
    ) -> list[tuple[str, Metadata]]:
        """Discover content in the watched directory."""
        content_items: list[tuple[str, Metadata]] = []

        if not self.watch_directory.exists():
            host.logger.warning(
                "Watch directory does not exist: %s", self.watch_directory
            )
            return content_items

        try:
            for root, _dirs, files in os.walk(self.watch_directory):
                for file in files:
                    file_path = Path(root) / file

                    # Filter by extensions if specified
                    if (
                        self.file_extensions
                        and file_path.suffix not in self.file_extensions
                    ):
                        continue

                    # Create file URL and metadata
                    file_url = file_path.as_uri()
                    stat = file_path.stat()
                    metadata = Metadata(
                        source_url=file_url,
                        mime_type="text/plain",  # Default, will be detected later
                        extra={
                            "file_path": str(file_path),
                            "file_size": stat.st_size,
                            "file_modified": stat.st_mtime,
                            "source_plugin": "DirectoryWatcherContentSource",
                        },
                    )

                    content_items.append((file_url, metadata))

            host.logger.info(
                "Discovered %d files in %s", len(content_items), self.watch_directory
            )

        except (OSError, PermissionError) as e:
            # Use error logging since Logger protocol doesn't include exception
            host.logger.error(  # noqa: TRY400
                "Error discovering content in %s: %s", self.watch_directory, str(e)
            )

        return content_items

    async def start_source(self, host: ContentSourceHost) -> None:
        """Start the content source and begin scheduling content for fetching."""
        # Discover and schedule all content
        content_items = await self.discover_content(host)

        for url, metadata in content_items:
            # Schedule each discovered file for fetching
            task_id: str | None = host.schedule_fetch(url, metadata)  # type: ignore[func-returns-value]
            if task_id:
                host.logger.debug("Scheduled fetch for %s (task: %s)", url, task_id)

        host.logger.info(
            "DirectoryWatcherContentSource started monitoring %s",
            self.watch_directory,
        )

    async def stop_source(self, host: ContentSourceHost) -> None:
        """Stop the content source and clean up any resources."""
        host.logger.info(
            "DirectoryWatcherContentSource stopped monitoring %s",
            self.watch_directory,
        )

    def get_configuration_id(self) -> str:
        """Get configuration identifier for this source."""
        return "directory_watcher"


@hookimpl
def register_content_source_providers() -> list[ContentSource]:
    """Register DirectoryWatcherContentSource with the plugin system."""
    # Example configuration-based instance
    # In practice, this would read from configuration
    default_watcher = DirectoryWatcherContentSource(
        watch_directory="~/Documents",
        file_extensions=[".txt", ".md", ".pdf", ".doc", ".docx"],
    )

    return [default_watcher]
