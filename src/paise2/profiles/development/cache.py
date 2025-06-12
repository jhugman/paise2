# ABOUTME: Development profile plugins - multiple cache providers for flexibility
# ABOUTME: Provides both memory and file-based cache for development convenience

from typing import Callable

from paise2.plugins.core.interfaces import CacheProvider
from paise2.plugins.core.registry import hookimpl
from paise2.plugins.providers.cache import FileCacheProvider, MemoryCacheProvider

# Note: We provide both providers in development for flexibility.
# The developer can choose which one to use based on their needs.

memory_provider = MemoryCacheProvider()
file_provider = FileCacheProvider()


@hookimpl
def register_cache_provider(
    register: Callable[[CacheProvider], None],
) -> None:
    """Register both memory and file cache providers for development."""
    register(memory_provider)
    register(file_provider)
