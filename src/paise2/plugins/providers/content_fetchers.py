# ABOUTME: Example ContentFetcher implementations for local files and HTTP resources
# ABOUTME: Provides FileContentFetcher and HTTPContentFetcher with proper logic

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlparse

if TYPE_CHECKING:
    from paise2.plugins.core.interfaces import ContentFetcherHost


class FileContentFetcher:
    """ContentFetcher implementation for local file access."""

    def can_fetch(self, host: ContentFetcherHost, url: str) -> bool:  # noqa: ARG002
        """
        Determine if this fetcher can handle the given URL.

        Handles file:// URLs and local file paths.

        Args:
            host: Host interface for system interaction
            url: URL to potentially fetch

        Returns:
            True if this fetcher can handle the URL
        """
        parsed = urlparse(url)

        # Handle file:// scheme
        if parsed.scheme == "file":
            return True

        # Handle local file paths (no scheme or relative paths)
        if not parsed.scheme or parsed.scheme == "":
            # Check if it's a valid file path
            try:
                path = Path(url)
                return path.exists() and path.is_file()
            except (OSError, ValueError):
                return False

        return False

    async def fetch(self, host: ContentFetcherHost, url: str) -> None:
        """
        Fetch content from local file and pass it to extraction.

        Args:
            host: Host interface for system interaction
            url: URL to fetch content from
        """
        parsed = urlparse(url)

        # Get file path
        file_path = Path(parsed.path) if parsed.scheme == "file" else Path(url)

        if not file_path.exists() or not file_path.is_file():
            host.logger.error("File not found: %s", file_path)
            return

        try:
            # Read file content - handle both binary and text files
            if self._is_binary_file(file_path):
                content: bytes | str = file_path.read_bytes()
            else:
                content = file_path.read_text(encoding="utf-8")

            # Create metadata
            from paise2.models import Metadata

            metadata = Metadata(
                source_url=url,
                title=file_path.name,
                mime_type=self._guess_mime_type(file_path),
                created_at=None,  # Could add file stats here
                modified_at=None,  # Could add file stats here
            )

            host.logger.info("Fetched content from file: %s", file_path)

            # Pass to extraction
            host.extract_file(content, metadata)

        except (OSError, UnicodeDecodeError) as e:
            # Note: Using logger.error as interface doesn't guarantee exception method
            host.logger.error("Error reading file %s: %s", file_path, e)  # noqa: TRY400

    def _is_binary_file(self, file_path: Path) -> bool:
        """Check if file is binary by examining first few bytes."""
        try:
            with file_path.open("rb") as f:
                chunk = f.read(1024)
                return b"\0" in chunk
        except OSError:
            return False

    def _guess_mime_type(self, file_path: Path) -> str:
        """Guess MIME type from file extension."""
        extension = file_path.suffix.lower()
        mime_types = {
            ".txt": "text/plain",
            ".md": "text/markdown",
            ".html": "text/html",
            ".htm": "text/html",
            ".json": "application/json",
            ".xml": "application/xml",
            ".pdf": "application/pdf",
            ".doc": "application/msword",
            ".docx": (
                "application/vnd.openxmlformats-officedocument"
                ".wordprocessingml.document"
            ),
        }
        return mime_types.get(extension, "application/octet-stream")


class HTTPContentFetcher:
    """ContentFetcher implementation for HTTP/HTTPS resources."""

    def can_fetch(self, host: ContentFetcherHost, url: str) -> bool:  # noqa: ARG002
        """
        Determine if this fetcher can handle the given URL.

        Handles http:// and https:// URLs.

        Args:
            host: Host interface for system interaction
            url: URL to potentially fetch

        Returns:
            True if this fetcher can handle the URL
        """
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https")

    async def fetch(self, host: ContentFetcherHost, url: str) -> None:
        """
        Fetch content from HTTP/HTTPS URL and pass it to extraction.

        Args:
            host: Host interface for system interaction
            url: URL to fetch content from
        """
        try:
            # For now, this is a placeholder implementation
            # In a real implementation, we would use aiohttp or similar
            host.logger.info("HTTPContentFetcher would fetch from: %s", url)

            # Placeholder: create dummy content and metadata
            content = f"Placeholder content from {url}"

            from paise2.models import Metadata

            metadata = Metadata(
                source_url=url,
                title=f"Content from {url}",
                mime_type="text/html",
            )

            # Pass to extraction
            host.extract_file(content, metadata)

        except Exception as e:
            # Note: Using logger.error instead of logger.exception
            # since interface doesn't guarantee exception method
            host.logger.error("Error fetching from %s: %s", url, e)  # noqa: TRY400
