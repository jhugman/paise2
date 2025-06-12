# ABOUTME: Test profile plugins - memory-only cache provider for fast testing
# ABOUTME: Provides only memory-based cache for unit tests and CI

from typing import Callable

from paise2.plugins.core.interfaces import CacheProvider
from paise2.plugins.core.registry import hookimpl
from paise2.plugins.providers.cache import MemoryCacheProvider


@hookimpl
def register_cache_provider(
    register: Callable[[CacheProvider], None],
) -> None:
    """Register the memory cache provider for testing."""
    register(MemoryCacheProvider())
