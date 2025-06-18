# ABOUTME: Provider package for cache, task queue, and content fetcher implementations
# ABOUTME: Provides implementations of various system infrastructure protocols

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

import pluggy

from .cache import (
    CacheEntry,
    ExtensionCacheManager,
    FileCacheManager,
    FileCacheProvider,
    MemoryCacheManager,
    MemoryCacheProvider,
)
from .content_fetchers import FileContentFetcher, HTTPContentFetcher
from .task_queue import (
    HueyRedisTaskQueueProvider,
    HueySQLiteTaskQueueProvider,
    NoTaskQueueProvider,
)

if TYPE_CHECKING:
    from paise2.plugins.core.interfaces import ContentFetcher

hookimpl = pluggy.HookimplMarker("paise2")


@hookimpl
def register_content_fetcher(register: Callable[[ContentFetcher], None]) -> None:
    """Register FileContentFetcher and HTTPContentFetcher plugins."""
    # Register FileContentFetcher
    register(FileContentFetcher())

    # Register HTTPContentFetcher
    register(HTTPContentFetcher())


__all__ = [
    "CacheEntry",
    "ExtensionCacheManager",
    "FileCacheManager",
    "FileCacheProvider",
    "FileContentFetcher",
    "HTTPContentFetcher",
    "HueyRedisTaskQueueProvider",
    "HueySQLiteTaskQueueProvider",
    "MemoryCacheManager",
    "MemoryCacheProvider",
    "NoTaskQueueProvider",
]
