# ABOUTME: Cache provider implementations for content caching with partitioning.
# ABOUTME: Provides memory and file-based cache with ExtensionCacheManager facade.

from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from paise2.config.models import Configuration
    from paise2.models import CacheId, Content
    from paise2.plugins.core.interfaces import CacheManager

# Constants for UUID validation and cache ID parsing
UUID_LENGTH = 36
UUID_DASH_COUNT = 4
CACHE_ID_PARTS_COUNT = 4


@dataclass(frozen=True)
class CacheEntry:
    """Data model for cache entries."""

    cache_id: CacheId
    partition_key: str
    content: Content
    file_extension: str = ""


@dataclass(frozen=True)
class CacheMetadata:
    """Metadata for cache entries stored in cache IDs."""

    partition_key: str
    file_extension: str
    unique_id: str
    is_binary: bool

    def to_cache_id(self) -> CacheId:
        """Encode this metadata into an opaque cache ID."""
        # Use pipe-delimited format: partition_key|file_extension|unique_id|is_binary
        binary_flag = "1" if self.is_binary else "0"
        return (
            f"{self.partition_key}|{self.file_extension}|{self.unique_id}|{binary_flag}"
        )

    @classmethod
    def from_cache_id(cls, cache_id: CacheId) -> CacheMetadata | None:
        """Decode metadata from cache ID."""
        try:
            metadata_string = cache_id

            # Split by pipe delimiter
            parts = metadata_string.split("|")
            if len(parts) != CACHE_ID_PARTS_COUNT:
                return None

            partition_key, file_extension, unique_id, binary_flag = parts
            is_binary = binary_flag == "1"

            return cls(
                partition_key=partition_key,
                file_extension=file_extension,
                unique_id=unique_id,
                is_binary=is_binary,
            )
        except (ValueError, UnicodeDecodeError):
            return None

    @classmethod
    def from_file_path(cls, cache_dir: Path, file_path: Path) -> CacheMetadata | None:
        """Decode metadata from cache file path."""
        try:
            # Extract partition key from the directory structure
            relative_path = file_path.relative_to(cache_dir)
            partition_key, filename = relative_path.parts

            # Check for binary flag in filename
            is_binary = False
            if ".bin" in filename:
                # Remove .bin suffix to get base filename
                filename = filename.replace(".bin", "", 1)
                is_binary = True

            # Handle files with extensions
            if "." in filename:
                # Find the UUID part
                parts = filename.split(".")
                if (
                    parts
                    and len(parts[0]) == UUID_LENGTH
                    and parts[0].count("-") == UUID_DASH_COUNT
                ):
                    unique_id = parts[0]
                    file_extension = "." + ".".join(parts[1:])
                else:
                    # Not a UUID-based filename
                    return None
            elif (
                len(filename) == UUID_LENGTH and filename.count("-") == UUID_DASH_COUNT
            ):
                # No extension
                unique_id = filename
                file_extension = ""
            else:
                # Not a UUID-based filename
                return None

            return cls(
                partition_key=partition_key,
                file_extension=file_extension,
                unique_id=unique_id,
                is_binary=is_binary,
            )
        except (ValueError, OSError):
            return None

    def get_file_path(self, cache_dir: Path) -> Path:
        """Get the file path for this cache entry."""
        partition_dir = cache_dir / self.partition_key
        partition_dir.mkdir(parents=True, exist_ok=True)

        # Encode binary type in filename by adding suffix
        base_filename = self.unique_id
        if self.is_binary:
            base_filename += ".bin"

        filename = base_filename
        if self.file_extension and not filename.endswith(self.file_extension):
            filename = f"{filename}{self.file_extension}"

        return partition_dir / filename


class MemoryCacheManager:
    """
    In-memory cache manager implementation.

    Provides cache storage for development and testing.
    Data is lost when the process exits.
    """

    def __init__(self) -> None:
        """Initialize memory cache with empty cache dictionary."""
        self._cache: dict[str, CacheEntry] = {}

    async def save(
        self, partition_key: str, content: Content, file_extension: str = ""
    ) -> CacheId:
        """Save content to cache and return a cache ID."""
        cache_id = str(uuid.uuid4())
        entry = CacheEntry(
            cache_id=cache_id,
            partition_key=partition_key,
            content=content,
            file_extension=file_extension,
        )
        self._cache[cache_id] = entry
        return cache_id

    async def get(self, cache_id: CacheId) -> Content | None:
        """Retrieve content from cache by ID."""
        entry = self._cache.get(cache_id)
        return entry.content if entry else None

    async def remove(self, cache_id: CacheId) -> bool:
        """Remove content from cache."""
        if cache_id in self._cache:
            del self._cache[cache_id]
            return True
        return False

    async def remove_all(self, cache_ids: list[CacheId]) -> list[CacheId]:
        """Remove multiple cache entries and return successfully removed IDs."""
        return [cache_id for cache_id in cache_ids if await self.remove(cache_id)]

    async def get_all(self, partition_key: str) -> list[CacheId]:
        """Get all cache IDs for a specific partition."""
        return [
            entry.cache_id
            for entry in self._cache.values()
            if entry.partition_key == partition_key
        ]


class MemoryCacheProvider:
    """
    Memory cache provider.

    Creates in-memory cache manager instances for development and testing.
    """

    def create_cache(self, configuration: Configuration) -> CacheManager:  # noqa: ARG002
        """Create a memory-based cache manager instance."""
        return MemoryCacheManager()


class FileCacheManager:
    """
    File-based cache manager implementation.

    Provides persistent cache storage with automatic partitioning and file management.
    Uses encoded cache IDs to eliminate the need for separate metadata storage.
    """

    def __init__(self, cache_dir: Path) -> None:
        """Initialize file cache with specified directory."""
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    async def save(
        self, partition_key: str, content: Content, file_extension: str = ""
    ) -> CacheId:
        """Save content to cache file and return a cache ID."""
        unique_id = str(uuid.uuid4())
        is_binary = isinstance(content, bytes)

        # Create metadata and get cache ID
        metadata = CacheMetadata(
            partition_key=partition_key,
            file_extension=file_extension,
            unique_id=unique_id,
            is_binary=is_binary,
        )
        cache_id = metadata.to_cache_id()
        file_path = metadata.get_file_path(self.cache_dir)

        # Save content to file
        try:
            if is_binary:
                with file_path.open("wb") as f:
                    f.write(content)  # type: ignore[arg-type]
            else:
                with file_path.open("w", encoding="utf-8") as f:
                    f.write(str(content))
        except OSError as e:
            msg = f"Failed to save cache file: {e}"
            raise OSError(msg) from e

        return cache_id

    async def get(self, cache_id: CacheId) -> Content | None:
        """Retrieve content from cache file by ID."""
        metadata = CacheMetadata.from_cache_id(cache_id)
        if metadata is None:
            return None

        file_path = metadata.get_file_path(self.cache_dir)

        if not file_path.exists():
            return None

        try:
            # Use stored content type information
            if metadata.is_binary:
                with file_path.open("rb") as f:
                    return f.read()
            else:
                with file_path.open("r", encoding="utf-8") as f:
                    return f.read()
        except OSError:
            return None

    async def remove(self, cache_id: CacheId) -> bool:
        """Remove content from cache file."""
        metadata = CacheMetadata.from_cache_id(cache_id)
        if metadata is None:
            return False

        file_path = metadata.get_file_path(self.cache_dir)

        try:
            if file_path.exists():
                file_path.unlink()
                return True
        except OSError:
            pass

        return False

    async def remove_all(self, cache_ids: list[CacheId]) -> list[CacheId]:
        """Remove multiple cache entries and return successfully removed IDs."""
        return [cache_id for cache_id in cache_ids if await self.remove(cache_id)]

    async def get_all(self, partition_key: str) -> list[CacheId]:
        """Get all cache IDs for a specific partition."""
        partition_dir = self.cache_dir / partition_key
        if not partition_dir.exists():
            return []

        cache_ids = []
        try:
            for file_path in partition_dir.iterdir():
                if file_path.is_file():
                    # Use the from_file_path method to decode metadata
                    metadata = CacheMetadata.from_file_path(self.cache_dir, file_path)
                    if metadata and metadata.partition_key == partition_key:
                        cache_ids.append(metadata.to_cache_id())
        except OSError:
            # If we can't read the directory, return empty list
            pass

        return cache_ids


class FileCacheProvider:
    """
    File-based cache provider.

    Creates file-based cache manager instances for production use.
    """

    def create_cache(self, configuration: Configuration) -> CacheManager:
        """Create a file-based cache manager instance."""
        cache_path = configuration.get("cache.file_path", "~/.local/share/paise2/cache")

        if cache_path == ":memory:":
            # Special case for testing
            return MemoryCacheManager()

        cache_dir = Path(cache_path).expanduser().resolve()
        cache_dir.mkdir(parents=True, exist_ok=True)
        return FileCacheManager(cache_dir)


class ExtensionCacheManager:
    """
    Facade cache manager for plugins.

    Provides a simplified interface that automatically fills in the partition key
    for plugin-specific cache operations.
    """

    def __init__(self, cache_manager: CacheManager, partition_key: str):
        """Initialize extension cache manager with base manager and partition key."""
        self.cache_manager = cache_manager
        self.partition_key = partition_key

    async def save(self, content: Content, file_extension: str = "") -> CacheId:
        """Save content to cache using automatic partitioning."""
        return await self.cache_manager.save(
            self.partition_key, content, file_extension
        )

    async def get(self, cache_id: CacheId) -> Content | None:
        """Retrieve content from cache by ID."""
        return await self.cache_manager.get(cache_id)

    async def remove(self, cache_id: CacheId) -> bool:
        """Remove content from cache."""
        return await self.cache_manager.remove(cache_id)

    async def remove_all(self, cache_ids: list[CacheId]) -> list[CacheId]:
        """Remove multiple cache entries and return successfully removed IDs."""
        return await self.cache_manager.remove_all(cache_ids)

    async def get_all(self) -> list[CacheId]:
        """Get all cache IDs for this plugin's partition."""
        return await self.cache_manager.get_all(self.partition_key)
