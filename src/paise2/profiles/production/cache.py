# ABOUTME: Production profile plugins - persistent cache provider for production
# ABOUTME: Provides only file-based cache for production environments

from typing import Callable

from paise2.plugins.core.interfaces import CacheProvider
from paise2.plugins.core.registry import hookimpl
from paise2.plugins.providers.cache import FileCacheProvider


@hookimpl
def register_cache_provider(
    register: Callable[[CacheProvider], None],
) -> None:
    """Register the file cache provider for production."""
    register(FileCacheProvider())
