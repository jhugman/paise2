# ABOUTME: Example ContentExtractor implementations for text and HTML content
# ABOUTME: Provides PlainTextExtractor and HTMLExtractor with proper logic

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from paise2.models import Metadata
    from paise2.plugins.core.interfaces import ContentExtractorHost


class PlainTextExtractor:
    """ContentExtractor implementation for plain text files."""

    def can_extract(self, url: str, mime_type: str | None = None) -> bool:
        """
        Determine if this extractor can handle the given content.

        Handles text/* MIME types and common text file extensions.

        Args:
            url: Source URL or path
            mime_type: Optional MIME type of the content

        Returns:
            True if this extractor can handle the content
        """
        # Check MIME type first if available
        if mime_type:
            return mime_type.startswith("text/")

        # Fall back to URL-based detection
        text_extensions = {".txt", ".md", ".rst", ".log", ".cfg", ".ini", ".conf"}
        url_lower = url.lower()
        return any(url_lower.endswith(ext) for ext in text_extensions)

    def preferred_mime_types(self) -> list[str]:
        """
        Return list of MIME types this extractor prefers to handle.

        Returns:
            List of MIME type strings
        """
        return [
            "text/plain",
            "text/markdown",
            "text/x-rst",
            "text/x-log",
            "text/x-config",
        ]

    async def extract(
        self,
        host: ContentExtractorHost,
        content: bytes | str,
        metadata: Metadata | None = None,
    ) -> None:
        """
        Extract plain text content and store it in the system.

        Args:
            host: Host interface for system interaction
            content: Content to extract from
            metadata: Optional metadata about the content
        """
        try:
            # Convert bytes to string if needed
            if isinstance(content, bytes):
                text_content = content.decode("utf-8")
            else:
                text_content = str(content)  # Ensure it's a string

            # Create or update metadata
            from paise2.models import Metadata

            if metadata is None:
                metadata = Metadata(source_url="unknown")

            # Update metadata for extracted content
            extracted_metadata = metadata.copy(
                mime_type="text/plain",
                processing_state="extracted",
                title=metadata.title or self._extract_title_from_text(text_content),
            )

            host.logger.info(
                "PlainTextExtractor extracted %d characters from %s",
                len(text_content),
                metadata.source_url,
            )

            # Store the extracted content using the storage interface
            await host.storage.add_item(host, text_content, extracted_metadata)

        except UnicodeDecodeError:
            host.logger.exception(
                "Failed to decode content as UTF-8 for %s",
                metadata.source_url if metadata else "unknown",
            )
            raise
        except Exception:
            host.logger.exception(
                "Error extracting plain text from %s",
                metadata.source_url if metadata else "unknown",
            )
            raise

    def _extract_title_from_text(self, text: str) -> str:
        """Extract a title from the first line of text."""
        max_title_length = 100
        lines = text.strip().split("\n")
        if lines:
            # Use first non-empty line as title, truncated to reasonable length
            first_line = lines[0].strip()
            if first_line:
                if len(first_line) > max_title_length:
                    return first_line[:max_title_length] + "..."
                return first_line
        return "Untitled Document"


class HTMLExtractor:
    """ContentExtractor implementation for HTML content."""

    def can_extract(self, url: str, mime_type: str | None = None) -> bool:
        """
        Determine if this extractor can handle the given content.

        Handles HTML MIME types and common HTML file extensions.

        Args:
            url: Source URL or path
            mime_type: Optional MIME type of the content

        Returns:
            True if this extractor can handle the content
        """
        # Check MIME type first if available
        if mime_type:
            return mime_type in ("text/html", "application/xhtml+xml")

        # Fall back to URL-based detection
        html_extensions = {".html", ".htm", ".xhtml"}
        url_lower = url.lower()
        return any(url_lower.endswith(ext) for ext in html_extensions)

    def preferred_mime_types(self) -> list[str]:
        """
        Return list of MIME types this extractor prefers to handle.

        Returns:
            List of MIME type strings
        """
        return [
            "text/html",
            "application/xhtml+xml",
        ]

    async def extract(
        self,
        host: ContentExtractorHost,
        content: bytes | str,
        metadata: Metadata | None = None,
    ) -> None:
        """
        Extract text content from HTML and store it in the system.

        Args:
            host: Host interface for system interaction
            content: Content to extract from
            metadata: Optional metadata about the content
        """
        try:
            # Convert bytes to string if needed
            if isinstance(content, bytes):
                html_content = content.decode("utf-8")
            else:
                html_content = str(content)  # Ensure it's a string

            # Simple text extraction (strip HTML tags)
            # In a real implementation, you'd use BeautifulSoup or similar
            text_content = self._strip_html_tags(html_content)

            # Extract title from HTML
            title = self._extract_html_title(html_content)

            # Create or update metadata
            from paise2.models import Metadata

            if metadata is None:
                metadata = Metadata(source_url="unknown")

            # Update metadata for extracted content
            extracted_metadata = metadata.copy(
                mime_type="text/plain",  # Extracted as plain text
                processing_state="extracted",
                title=title or metadata.title or "Untitled HTML Document",
            )

            host.logger.info(
                "HTMLExtractor extracted %d characters from %s",
                len(text_content),
                metadata.source_url,
            )

            # Store the extracted content using the storage interface
            await host.storage.add_item(host, text_content, extracted_metadata)

        except UnicodeDecodeError:
            host.logger.exception(
                "Failed to decode HTML content as UTF-8 for %s",
                metadata.source_url if metadata else "unknown",
            )
            raise
        except Exception:
            host.logger.exception(
                "Error extracting HTML from %s",
                metadata.source_url if metadata else "unknown",
            )
            raise

    def _strip_html_tags(self, html: str) -> str:
        """Simple HTML tag removal (replace with proper HTML parsing in production)."""
        import re

        # Remove script and style content
        html = re.sub(
            r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE
        )
        html = re.sub(
            r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE
        )
        # Remove HTML tags
        html = re.sub(r"<[^>]+>", " ", html)
        # Clean up whitespace
        html = re.sub(r"\s+", " ", html)
        return html.strip()

    def _extract_html_title(self, html: str) -> str | None:
        """Extract title from HTML <title> tag."""
        import re

        title_match = re.search(
            r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL
        )
        if title_match:
            title = title_match.group(1).strip()
            # Clean up whitespace and decode HTML entities (basic)
            return re.sub(r"\s+", " ", title)
        return None
