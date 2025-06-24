# ABOUTME: Example plugin demonstrating the register_plugin hook implementation
# ABOUTME: Shows how a plugin class can implement multiple extension points

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from paise2.models import Metadata
from paise2.plugins.core.registry import hookimpl

if TYPE_CHECKING:
    from paise2.plugins.core.interfaces import (
        CacheProvider,
        ConfigurationProvider,
        ContentExtractor,
        ContentExtractorHost,
    )


class ExampleMultiExtensionPlugin:
    """Example plugin that implements multiple extension points."""

    def register_configuration_provider(
        self, register: Callable[[ConfigurationProvider], None]
    ) -> None:
        """Register configuration provider from this plugin."""
        register(ExampleConfigurationProvider())

    def register_content_extractor(
        self, register: Callable[[ContentExtractor], None]
    ) -> None:
        """Register content extractor from this plugin."""
        register(ExampleContentExtractor())

    def register_cache_provider(
        self, register: Callable[[CacheProvider], None]
    ) -> None:
        """Register cache provider from this plugin."""
        register(ExampleCacheProvider())


class ExampleConfigurationProvider:
    """Example configuration provider."""

    def get_default_configuration(self) -> str:
        """Return YAML configuration for this plugin."""
        return """
# Example plugin configuration
example_plugin:
  enabled: true
  settings:
    example_setting: "default_value"
"""

    def get_configuration_id(self) -> str:
        """Return configuration identifier."""
        return "example_plugin"


class ExampleContentExtractor:
    """Example content extractor."""

    def can_extract(self, url: str, mime_type: str | None = None) -> bool:
        """Check if this extractor can handle the content."""
        return url.endswith(".example") or (mime_type == "application/x-example")

    def preferred_mime_types(self) -> list[str]:
        """Return preferred MIME types."""
        return ["application/x-example"]

    async def extract(
        self,
        host: ContentExtractorHost,
        content: bytes | str,
        metadata: Metadata | None = None,
    ) -> None:
        """Extract content and store it."""
        # Simple example extraction - convert to string
        text_content = str(content) if not isinstance(content, str) else content

        new_metadata = metadata or Metadata(source_url="unknown")
        new_metadata = new_metadata.copy(
            title="Example extracted content", processing_state="completed"
        )

        await host.storage.add_item(host, text_content, new_metadata)


class ExampleCacheProvider:
    """Example cache provider (placeholder)."""

    def create_cache(self, configuration: Any) -> Any:
        """Create cache instance."""
        # This is just a placeholder implementation
        return None


# Plugin registration hook
@hookimpl
def register_plugin(register: Callable[[Any], None]) -> None:
    """Register the example multi-extension plugin."""
    register(ExampleMultiExtensionPlugin())
