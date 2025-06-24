# ABOUTME: Example plugin demonstrating the register_plugin hook implementation
# ABOUTME: Shows how a single plugin class can implement multiple extension points

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from paise2.plugins.core.registry import hookimpl

if TYPE_CHECKING:
    from paise2.models import Metadata
    from paise2.plugins.core.interfaces import (
        CacheProvider,
        Configuration,
        ConfigurationProvider,
        ContentExtractor,
        ContentExtractorHost,
    )


class ExamplePlugin:
    """Example plugin that implements multiple extension points."""

    def register_configuration_provider(
        self, register: Callable[[ConfigurationProvider], None]
    ) -> None:
        """Register a configuration provider."""
        register(ExampleConfigurationProvider())

    def register_content_extractor(
        self, register: Callable[[ContentExtractor], None]
    ) -> None:
        """Register a content extractor."""
        register(ExampleContentExtractor())

    def register_cache_provider(
        self, register: Callable[[CacheProvider], None]
    ) -> None:
        """Register a cache provider."""
        register(ExampleCacheProvider())


class ExampleConfigurationProvider:
    """Example configuration provider."""

    def get_default_configuration(self) -> str:
        """Get default YAML configuration."""
        return """
example_plugin:
  enabled: true
  max_items: 1000
  cache_ttl: 3600
"""

    def get_configuration_id(self) -> str:
        """Get configuration identifier."""
        return "example_plugin"


class ExampleContentExtractor:
    """Example content extractor for demonstration files."""

    def can_extract(self, url: str, mime_type: str | None = None) -> bool:
        """Check if this extractor can handle the given URL."""
        if url.endswith(".example"):
            return True
        return bool(mime_type and "example" in mime_type)

    def preferred_mime_types(self) -> list[str]:
        """Return preferred MIME types."""
        return ["application/x-example", "text/x-example"]

    async def extract(
        self,
        host: ContentExtractorHost,
        content: bytes | str,
        metadata: Metadata | None = None,
    ) -> None:
        """Extract content from example files."""
        # Simple extraction: just use the content as-is
        if isinstance(content, str):
            text_content = content
        else:  # content is bytes
            text_content = content.decode("utf-8", errors="ignore")

        from paise2.models import Metadata

        if metadata is None:
            metadata = Metadata(source_url="unknown://example")

        # Update metadata with extracted info
        updated_metadata = metadata.copy(
            title=f"Example: {text_content[:50]}...",
            description="Content extracted by ExampleContentExtractor",
        )

        # Store the extracted content
        await host.storage.add_item(host, text_content, updated_metadata)


class ExampleCacheProvider:
    """Example cache provider."""

    def create_cache(self, configuration: Configuration) -> Any:
        """Create a cache manager."""
        # This is just a placeholder implementation
        return ExampleCacheManager()


class ExampleCacheManager:
    """Example cache manager."""

    def __init__(self) -> None:
        self._cache: dict[str, Any] = {}

    async def save(
        self, partition_key: str, content: Any, file_extension: str = ""
    ) -> str:
        """Save content to cache."""
        cache_id = f"{partition_key}_{len(self._cache)}"
        self._cache[cache_id] = content
        return cache_id

    async def get(self, cache_id: str) -> Any:
        """Get content from cache."""
        return self._cache.get(cache_id)

    async def remove(self, cache_id: str) -> bool:
        """Remove content from cache."""
        if cache_id in self._cache:
            del self._cache[cache_id]
            return True
        return False

    async def remove_all(self, cache_ids: list[str]) -> list[str]:
        """Remove multiple items from cache."""
        return [cache_id for cache_id in cache_ids if await self.remove(cache_id)]

    async def get_all(self, partition_key: str) -> list[str]:
        """Get all cache IDs for a partition."""
        return [
            cache_id for cache_id in self._cache if cache_id.startswith(partition_key)
        ]


# Plugin registration hook - this is the key implementation
@hookimpl
def register_plugin(register: Callable[[Any], None]) -> None:
    """Register the example plugin that implements multiple extension points."""
    register(ExamplePlugin())
