# ABOUTME: Unit tests for cache provider system.
# ABOUTME: Tests cache implementations with partitioning and file extension support.

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from paise2.plugins.core.interfaces import CacheManager, CacheProvider
from tests.fixtures import MockConfiguration


class TestCacheEntry:
    """Test CacheEntry data model."""

    def test_cache_entry_creation_with_defaults(self) -> None:
        """Test CacheEntry can be created with default values."""
        from paise2.plugins.providers.cache import CacheEntry

        entry = CacheEntry(
            cache_id="test-id",
            partition_key="test.plugin",
            content=b"test content",
            file_extension=".txt",
        )

        assert entry.cache_id == "test-id"
        assert entry.partition_key == "test.plugin"
        assert entry.content == b"test content"
        assert entry.file_extension == ".txt"


class TestMemoryCacheManager:
    """Test MemoryCacheManager implementation."""

    @pytest.mark.asyncio
    async def test_memory_cache_manager_implements_protocol(self) -> None:
        """Test that MemoryCacheManager implements CacheManager protocol."""
        from paise2.plugins.providers.cache import MemoryCacheManager

        cache = MemoryCacheManager()
        assert isinstance(cache, CacheManager)

    @pytest.mark.asyncio
    async def test_save_and_get_basic_operations(self) -> None:
        """Test basic save and get operations."""
        from paise2.plugins.providers.cache import MemoryCacheManager

        cache = MemoryCacheManager()

        cache_id = await cache.save("test.plugin", b"test content", ".txt")

        result = await cache.get(cache_id)
        assert result == b"test content"

    @pytest.mark.asyncio
    async def test_save_with_file_extension(self) -> None:
        """Test saving content with file extension."""
        from paise2.plugins.providers.cache import MemoryCacheManager

        cache = MemoryCacheManager()

        cache_id = await cache.save("test.plugin", "html content", ".html")

        result = await cache.get(cache_id)
        assert result == "html content"

    @pytest.mark.asyncio
    async def test_get_missing_cache_id_returns_none(self) -> None:
        """Test get operation with missing cache ID returns None."""
        from paise2.plugins.providers.cache import MemoryCacheManager

        cache = MemoryCacheManager()

        result = await cache.get("missing-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_remove(self) -> None:
        """Test remove operation."""
        from paise2.plugins.providers.cache import MemoryCacheManager

        cache = MemoryCacheManager()

        cache_id = await cache.save("test.plugin", b"test content")
        removed = await cache.remove(cache_id)
        assert removed is True

        # Should not be retrievable after removal
        result = await cache.get(cache_id)
        assert result is None

        # Removing again should return False
        removed_again = await cache.remove(cache_id)
        assert removed_again is False

    @pytest.mark.asyncio
    async def test_remove_all(self) -> None:
        """Test batch removal operation."""
        from paise2.plugins.providers.cache import MemoryCacheManager

        cache = MemoryCacheManager()

        # Save multiple items
        id1 = await cache.save("test.plugin", b"content1")
        id2 = await cache.save("test.plugin", b"content2")
        id3 = await cache.save("test.plugin", b"content3")

        # Remove some items
        removed_ids = await cache.remove_all([id1, id3, "missing-id"])

        # Should return successfully removed IDs
        assert len(removed_ids) == 2
        assert id1 in removed_ids
        assert id3 in removed_ids
        assert "missing-id" not in removed_ids

        # Verify removal
        assert await cache.get(id1) is None
        assert await cache.get(id2) == b"content2"
        assert await cache.get(id3) is None

    @pytest.mark.asyncio
    async def test_get_all(self) -> None:
        """Test getting all cache IDs for a partition."""
        from paise2.plugins.providers.cache import MemoryCacheManager

        cache = MemoryCacheManager()

        # Save items in different partitions
        id1 = await cache.save("plugin1", b"content1")
        id2 = await cache.save("plugin1", b"content2")
        id3 = await cache.save("plugin2", b"content3")

        # Get all for plugin1
        plugin1_ids = await cache.get_all("plugin1")
        assert len(plugin1_ids) == 2
        assert id1 in plugin1_ids
        assert id2 in plugin1_ids
        assert id3 not in plugin1_ids

        # Get all for plugin2
        plugin2_ids = await cache.get_all("plugin2")
        assert len(plugin2_ids) == 1
        assert id3 in plugin2_ids

    @pytest.mark.asyncio
    async def test_automatic_partitioning_isolation(self) -> None:
        """Test that different partitions are properly isolated."""
        from paise2.plugins.providers.cache import MemoryCacheManager

        cache = MemoryCacheManager()

        # Save same content in different partitions
        id1 = await cache.save("plugin1", b"content")
        id2 = await cache.save("plugin2", b"content")

        # Both should be accessible
        assert await cache.get(id1) == b"content"
        assert await cache.get(id2) == b"content"

        # Removing from one partition shouldn't affect the other
        await cache.remove(id1)
        assert await cache.get(id1) is None
        assert await cache.get(id2) == b"content"


class TestMemoryCacheProvider:
    """Test MemoryCacheProvider implementation."""

    def test_memory_cache_provider_implements_protocol(self) -> None:
        """Test MemoryCacheProvider implements CacheProvider protocol."""
        from paise2.plugins.providers.cache import MemoryCacheProvider

        provider = MemoryCacheProvider()
        assert isinstance(provider, CacheProvider)

    def test_provider_creates_manager(self) -> None:
        """Test that provider creates CacheManager instance."""
        from paise2.plugins.providers.cache import (
            MemoryCacheManager,
            MemoryCacheProvider,
        )

        provider = MemoryCacheProvider()
        configuration = MockConfiguration({"test": "config"})

        cache_manager = provider.create_cache(configuration)

        assert isinstance(cache_manager, CacheManager)
        assert isinstance(cache_manager, MemoryCacheManager)

    def test_multiple_managers_are_independent(self) -> None:
        """Test that multiple cache manager instances are independent."""
        from paise2.plugins.providers.cache import MemoryCacheProvider

        provider = MemoryCacheProvider()

        cache1 = provider.create_cache(MockConfiguration({}))
        cache2 = provider.create_cache(MockConfiguration({}))

        # They should be different instances
        assert cache1 is not cache2

    @pytest.mark.asyncio
    async def test_integration(self) -> None:
        """Test provider integration with cache operations."""
        from paise2.plugins.providers.cache import MemoryCacheProvider

        provider = MemoryCacheProvider()
        cache = provider.create_cache(MockConfiguration({}))

        # Basic operation
        cache_id = await cache.save("test.plugin", b"test content", ".txt")
        result = await cache.get(cache_id)

        assert result == b"test content"


class TestFileCacheManager:
    """Test FileCacheManager implementation."""

    @pytest.mark.asyncio
    async def test_file_cache_manager_implements_protocol(self) -> None:
        """Test that FileCacheManager implements CacheManager protocol."""
        from paise2.plugins.providers.cache import FileCacheManager

        with tempfile.TemporaryDirectory() as temp_dir:
            cache = FileCacheManager(Path(temp_dir))
            assert isinstance(cache, CacheManager)

    @pytest.mark.asyncio
    async def test_save_and_get(self) -> None:
        """Test basic save and get operations with file persistence."""
        from paise2.plugins.providers.cache import FileCacheManager

        with tempfile.TemporaryDirectory() as temp_dir:
            cache = FileCacheManager(Path(temp_dir))

            cache_id = await cache.save("test.plugin", b"test content", ".txt")

            result = await cache.get(cache_id)
            assert result == b"test content"

    @pytest.mark.asyncio
    async def test_save_with_file_extension_creates_correct_file(self) -> None:
        """Test that file extension is used in file creation."""
        from paise2.plugins.providers.cache import FileCacheManager

        with tempfile.TemporaryDirectory() as temp_dir:
            cache = FileCacheManager(Path(temp_dir))
            cache_path = Path(temp_dir)

            _ = await cache.save("test.plugin", b"content", ".html")

            # File should be created with extension
            cache_files = list(cache_path.rglob("*.html"))
            assert len(cache_files) == 1
            assert cache_files[0].suffix == ".html"

    @pytest.mark.asyncio
    async def test_automatic_partitioning(self) -> None:
        """Test automatic partitioning by plugin module name."""
        from paise2.plugins.providers.cache import FileCacheManager

        with tempfile.TemporaryDirectory() as temp_dir:
            cache = FileCacheManager(Path(temp_dir))
            cache_path = Path(temp_dir)

            # Save items in different partitions
            id1 = await cache.save("plugin1", b"content1", ".txt")
            id2 = await cache.save("plugin2", b"content2", ".txt")

            # Should create separate directories
            plugin1_dir = cache_path / "plugin1"
            plugin2_dir = cache_path / "plugin2"
            assert plugin1_dir.exists()
            assert plugin2_dir.exists()

            # Content should be accessible
            assert await cache.get(id1) == b"content1"
            assert await cache.get(id2) == b"content2"

    @pytest.mark.asyncio
    async def test_remove(self) -> None:
        """Test file removal."""
        from paise2.plugins.providers.cache import FileCacheManager

        with tempfile.TemporaryDirectory() as temp_dir:
            cache = FileCacheManager(Path(temp_dir))

            cache_id = await cache.save("test.plugin", b"content", ".txt")

            # File should exist
            assert await cache.get(cache_id) == b"content"

            # Remove file
            removed = await cache.remove(cache_id)
            assert removed is True

            # File should be gone
            assert await cache.get(cache_id) is None

            # Removing again should return False
            removed_again = await cache.remove(cache_id)
            assert removed_again is False

    @pytest.mark.asyncio
    async def test_remove_all(self) -> None:
        """Test batch file removal."""
        from paise2.plugins.providers.cache import FileCacheManager

        with tempfile.TemporaryDirectory() as temp_dir:
            cache = FileCacheManager(Path(temp_dir))

            # Save multiple files
            id1 = await cache.save("test.plugin", b"content1", ".txt")
            id2 = await cache.save("test.plugin", b"content2", ".txt")
            id3 = await cache.save("test.plugin", b"content3", ".txt")

            # Remove some files
            removed_ids = await cache.remove_all([id1, id3, "missing-id"])

            # Should return successfully removed IDs
            assert len(removed_ids) == 2
            assert id1 in removed_ids
            assert id3 in removed_ids
            assert "missing-id" not in removed_ids

            # Verify removal
            assert await cache.get(id1) is None
            assert await cache.get(id2) == b"content2"
            assert await cache.get(id3) is None

    @pytest.mark.asyncio
    async def test_get_all(self) -> None:
        """Test getting all cache IDs for a partition."""
        from paise2.plugins.providers.cache import FileCacheManager

        with tempfile.TemporaryDirectory() as temp_dir:
            cache = FileCacheManager(Path(temp_dir))

            # Save items in different partitions
            id1 = await cache.save("plugin1", b"content1", ".txt")
            id2 = await cache.save("plugin1", b"content2", ".txt")
            id3 = await cache.save("plugin2", b"content3", ".txt")

            # Get all for plugin1
            plugin1_ids = await cache.get_all("plugin1")
            assert len(plugin1_ids) == 2
            assert id1 in plugin1_ids
            assert id2 in plugin1_ids
            assert id3 not in plugin1_ids

            # Get all for plugin2
            plugin2_ids = await cache.get_all("plugin2")
            assert len(plugin2_ids) == 1
            assert id3 in plugin2_ids

    @pytest.mark.asyncio
    async def test_cache_id_uniqueness(self) -> None:
        """Test that cache IDs are unique."""
        from paise2.plugins.providers.cache import FileCacheManager

        with tempfile.TemporaryDirectory() as temp_dir:
            cache = FileCacheManager(Path(temp_dir))

            # Save same content multiple times
            id1 = await cache.save("test.plugin", b"content", ".txt")
            id2 = await cache.save("test.plugin", b"content", ".txt")
            id3 = await cache.save("test.plugin", b"different", ".txt")

            # All IDs should be unique
            assert id1 != id2
            assert id1 != id3
            assert id2 != id3

            # All should be retrievable
            assert await cache.get(id1) == b"content"
            assert await cache.get(id2) == b"content"
            assert await cache.get(id3) == b"different"


class TestFileCacheProvider:
    """Test FileCacheProvider implementation."""

    def test_file_cache_provider_implements_protocol(self) -> None:
        """Test FileCacheProvider implements CacheProvider protocol."""
        from paise2.plugins.providers.cache import FileCacheProvider

        provider = FileCacheProvider()
        assert isinstance(provider, CacheProvider)

    def test_provider_creates_manager(self) -> None:
        """Test that provider creates FileCacheManager with default path."""
        from paise2.plugins.providers.cache import FileCacheManager, FileCacheProvider

        provider = FileCacheProvider()
        configuration = MockConfiguration({})

        cache_manager = provider.create_cache(configuration)

        assert isinstance(cache_manager, CacheManager)
        assert isinstance(cache_manager, FileCacheManager)

    def test_provider_creates_manager_with_custom_path(self) -> None:
        """Test provider creates manager with custom path from configuration."""
        from paise2.plugins.providers.cache import FileCacheManager, FileCacheProvider

        with tempfile.TemporaryDirectory() as temp_dir:
            custom_path = str(Path(temp_dir) / "custom_cache")
            provider = FileCacheProvider()
            configuration = MockConfiguration({"cache.file_path": custom_path})

            cache_manager = provider.create_cache(configuration)

            assert isinstance(cache_manager, FileCacheManager)
            # Test that it uses the custom path by saving and retrieving
            # (We can't directly check the path without exposing internals)

    def test_provider_handles_path_expansion(self) -> None:
        """Test provider handles path expansion (~ for home directory)."""
        from paise2.plugins.providers.cache import FileCacheProvider

        provider = FileCacheProvider()
        configuration = MockConfiguration({"cache.file_path": "~/test_cache"})

        cache_manager = provider.create_cache(configuration)

        assert isinstance(cache_manager, CacheManager)
        # The path should be expanded, but we won't test the actual path
        # to avoid creating files in the user's home directory during tests


class TestExtensionCacheManager:
    """Test ExtensionCacheManager facade functionality."""

    @pytest.mark.asyncio
    async def test_extension_cache_manager_facade(self) -> None:
        """Test that ExtensionCacheManager properly wraps CacheManager."""
        from paise2.plugins.providers.cache import (
            ExtensionCacheManager,
            MemoryCacheManager,
        )

        base_cache = MemoryCacheManager()
        extension_cache = ExtensionCacheManager(base_cache, "test.plugin")

        # Save using extension cache (should use the provided partition)
        cache_id = await extension_cache.save(b"test content", ".txt")

        # Should be retrievable
        result = await extension_cache.get(cache_id)
        assert result == b"test content"

        # Should also be retrievable from base cache with explicit partition
        base_result = await base_cache.get(cache_id)
        assert base_result == b"test content"

    @pytest.mark.asyncio
    async def test_extension_cache_manager_remove_operations(self) -> None:
        """Test remove operations work through facade."""
        from paise2.plugins.providers.cache import (
            ExtensionCacheManager,
            MemoryCacheManager,
        )

        base_cache = MemoryCacheManager()
        extension_cache = ExtensionCacheManager(base_cache, "test.plugin")

        # Save and remove
        cache_id = await extension_cache.save(b"content", ".txt")
        removed = await extension_cache.remove(cache_id)
        assert removed is True

        # Should be gone
        result = await extension_cache.get(cache_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_extension_cache_manager_get_all(self) -> None:
        """Test get_all operation works through facade."""
        from paise2.plugins.providers.cache import (
            ExtensionCacheManager,
            MemoryCacheManager,
        )

        base_cache = MemoryCacheManager()
        extension_cache = ExtensionCacheManager(base_cache, "test.plugin")

        # Save some items
        id1 = await extension_cache.save(b"content1", ".txt")
        id2 = await extension_cache.save(b"content2", ".txt")

        # Get all should return our items
        all_ids = await extension_cache.get_all()
        assert len(all_ids) == 2
        assert id1 in all_ids
        assert id2 in all_ids


class TestCacheProviderIntegration:
    """Integration tests for cache provider system."""

    @pytest.mark.asyncio
    async def test_memory_cache_integration_with_extension_manager(self) -> None:
        """Test memory cache integration with ExtensionCacheManager."""
        from paise2.plugins.providers.cache import (
            ExtensionCacheManager,
            MemoryCacheProvider,
        )

        provider = MemoryCacheProvider()
        base_cache = provider.create_cache(MockConfiguration({}))
        extension_cache = ExtensionCacheManager(base_cache, "test.plugin")

        # Use extension cache interface
        cache_id = await extension_cache.save(b"test content", ".txt")
        result = await extension_cache.get(cache_id)

        assert result == b"test content"

        # Verify partitioning by checking base cache
        direct_result = await base_cache.get(cache_id)
        assert direct_result == b"test content"

    @pytest.mark.asyncio
    async def test_file_cache_integration_with_extension_manager(self) -> None:
        """Test file cache integration with ExtensionCacheManager."""
        from paise2.plugins.providers.cache import (
            ExtensionCacheManager,
            FileCacheProvider,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            provider = FileCacheProvider()
            config = MockConfiguration({"cache.file_path": temp_dir})
            base_cache = provider.create_cache(config)
            extension_cache = ExtensionCacheManager(base_cache, "test.plugin")

            # Use extension cache interface
            cache_id = await extension_cache.save(b"test content", ".txt")
            result = await extension_cache.get(cache_id)

            assert result == b"test content"

            # Verify file was created in correct location
            cache_path = Path(temp_dir)
            plugin_files = list(cache_path.rglob("*.txt"))
            assert len(plugin_files) >= 1

    @pytest.mark.asyncio
    async def test_cache_cleanup_integration(self) -> None:
        """Test cache cleanup integration with remove operations."""
        from paise2.plugins.providers.cache import MemoryCacheProvider

        provider = MemoryCacheProvider()
        cache = provider.create_cache(MockConfiguration({}))

        # Simulate storage removal returning cache IDs for cleanup
        cache_ids = []
        for i in range(3):
            cache_id = await cache.save("test.plugin", f"content{i}".encode(), ".txt")
            cache_ids.append(cache_id)

        # Simulate cache cleanup
        removed_ids = await cache.remove_all(cache_ids)

        # All should be removed
        assert len(removed_ids) == 3
        for cache_id in cache_ids:
            assert cache_id in removed_ids
            assert await cache.get(cache_id) is None


class TestCacheMetadata:
    """Test CacheMetadata roundtripping and edge cases."""

    def test_cache_metadata_creation(self) -> None:
        """Test basic CacheMetadata creation."""
        from paise2.plugins.providers.cache import CacheMetadata

        metadata = CacheMetadata(
            partition_key="test.plugin",
            file_extension=".txt",
            unique_id="12345678-1234-1234-1234-123456789abc",
            is_binary=True,
        )

        assert metadata.partition_key == "test.plugin"
        assert metadata.file_extension == ".txt"
        assert metadata.unique_id == "12345678-1234-1234-1234-123456789abc"
        assert metadata.is_binary is True

    def test_cache_id_roundtrip_basic(self) -> None:
        """Test basic cache ID encoding and decoding roundtrip."""
        from paise2.plugins.providers.cache import CacheMetadata

        original = CacheMetadata(
            partition_key="test.plugin",
            file_extension=".txt",
            unique_id="12345678-1234-1234-1234-123456789abc",
            is_binary=True,
        )

        # Encode to cache ID
        cache_id = original.to_cache_id()
        assert cache_id is not None
        assert isinstance(cache_id, str)

        # Decode back from cache ID
        decoded = CacheMetadata.from_cache_id(cache_id)
        assert decoded is not None
        assert decoded == original

    def test_cache_id_roundtrip_binary_false(self) -> None:
        """Test cache ID roundtrip with binary=False."""
        from paise2.plugins.providers.cache import CacheMetadata

        original = CacheMetadata(
            partition_key="plugin.text",
            file_extension=".md",
            unique_id="abcdef01-2345-6789-abcd-ef0123456789",
            is_binary=False,
        )

        cache_id = original.to_cache_id()
        decoded = CacheMetadata.from_cache_id(cache_id)

        assert decoded == original
        assert decoded is not None
        assert decoded.is_binary is False

    def test_cache_id_roundtrip_no_extension(self) -> None:
        """Test cache ID roundtrip with no file extension."""
        from paise2.plugins.providers.cache import CacheMetadata

        original = CacheMetadata(
            partition_key="plugin.raw",
            file_extension="",
            unique_id="fedcba09-8765-4321-fedc-ba0987654321",
            is_binary=True,
        )

        cache_id = original.to_cache_id()
        decoded = CacheMetadata.from_cache_id(cache_id)

        assert decoded == original
        assert decoded is not None
        assert decoded.file_extension == ""

    def test_cache_id_roundtrip_complex_extension(self) -> None:
        """Test cache ID roundtrip with complex file extension."""
        from paise2.plugins.providers.cache import CacheMetadata

        original = CacheMetadata(
            partition_key="plugin.complex",
            file_extension=".tar.gz",
            unique_id="11111111-2222-3333-4444-555555555555",
            is_binary=True,
        )

        cache_id = original.to_cache_id()
        decoded = CacheMetadata.from_cache_id(cache_id)

        assert decoded == original
        assert decoded is not None
        assert decoded.file_extension == ".tar.gz"

    def test_cache_id_roundtrip_special_characters_in_partition(self) -> None:
        """Test cache ID roundtrip with special characters in partition key."""
        from paise2.plugins.providers.cache import CacheMetadata

        original = CacheMetadata(
            partition_key="plugin.with-dashes_and.dots",
            file_extension=".json",
            unique_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            is_binary=False,
        )

        cache_id = original.to_cache_id()
        decoded = CacheMetadata.from_cache_id(cache_id)

        assert decoded == original

    def test_file_path_roundtrip_basic(self) -> None:
        """Test basic file path encoding and decoding roundtrip."""
        from paise2.plugins.providers.cache import CacheMetadata

        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir)

            original = CacheMetadata(
                partition_key="test.plugin",
                file_extension=".txt",
                unique_id="12345678-1234-1234-1234-123456789abc",
                is_binary=True,
            )

            # Generate file path
            file_path = original.get_file_path(cache_dir)

            # Create the file so from_file_path can work
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.touch()

            # Decode back from file path
            decoded = CacheMetadata.from_file_path(cache_dir, file_path)
            assert decoded is not None
            assert decoded == original

    def test_file_path_roundtrip_binary_false(self) -> None:
        """Test file path roundtrip with binary=False."""
        from paise2.plugins.providers.cache import CacheMetadata

        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir)

            original = CacheMetadata(
                partition_key="plugin.text",
                file_extension=".md",
                unique_id="abcdef01-2345-6789-abcd-ef0123456789",
                is_binary=False,
            )

            file_path = original.get_file_path(cache_dir)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.touch()

            decoded = CacheMetadata.from_file_path(cache_dir, file_path)
            assert decoded == original
            assert decoded is not None
            assert decoded.is_binary is False

    def test_file_path_roundtrip_no_extension(self) -> None:
        """Test file path roundtrip with no file extension."""
        from paise2.plugins.providers.cache import CacheMetadata

        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir)

            original = CacheMetadata(
                partition_key="plugin.raw",
                file_extension="",
                unique_id="fedcba09-8765-4321-fedc-ba0987654321",
                is_binary=True,
            )

            file_path = original.get_file_path(cache_dir)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.touch()

            decoded = CacheMetadata.from_file_path(cache_dir, file_path)
            assert decoded == original
            assert decoded is not None
            assert decoded.file_extension == ""

    def test_file_path_roundtrip_complex_extension(self) -> None:
        """Test file path roundtrip with complex file extension."""
        from paise2.plugins.providers.cache import CacheMetadata

        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir)

            original = CacheMetadata(
                partition_key="plugin.complex",
                file_extension=".tar.gz",
                unique_id="11111111-2222-3333-4444-555555555555",
                is_binary=True,
            )

            file_path = original.get_file_path(cache_dir)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.touch()

            decoded = CacheMetadata.from_file_path(cache_dir, file_path)
            assert decoded == original
            assert decoded is not None
            assert decoded.file_extension == ".tar.gz"

    def test_full_roundtrip_via_both_methods(self) -> None:
        """Test full roundtrip:
        metadata -> cache_id -> metadata -> file_path -> metadata."""
        from paise2.plugins.providers.cache import CacheMetadata

        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir)

            original = CacheMetadata(
                partition_key="full.roundtrip",
                file_extension=".json",
                unique_id="99999999-8888-7777-6666-555555555555",
                is_binary=False,
            )

            # Step 1: metadata -> cache_id -> metadata
            cache_id = original.to_cache_id()
            from_cache_id = CacheMetadata.from_cache_id(cache_id)
            assert from_cache_id == original

            # Step 2: metadata -> file_path -> metadata
            file_path = from_cache_id.get_file_path(cache_dir)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.touch()

            from_file_path = CacheMetadata.from_file_path(cache_dir, file_path)
            assert from_file_path == original

            # All should be identical
            assert original == from_cache_id == from_file_path

    def test_invalid_cache_id_decoding(self) -> None:
        """Test handling of invalid cache IDs."""
        from paise2.plugins.providers.cache import CacheMetadata

        # Invalid base64
        assert CacheMetadata.from_cache_id("invalid-base64!") is None

        # Valid base64 but wrong format
        import base64

        invalid_data = base64.urlsafe_b64encode(b"not|enough|parts").decode("ascii")
        assert CacheMetadata.from_cache_id(invalid_data) is None

        # Valid base64 but too many parts
        too_many_parts = base64.urlsafe_b64encode(b"a|b|c|d|e|f").decode("ascii")
        assert CacheMetadata.from_cache_id(too_many_parts) is None

    def test_invalid_file_path_decoding(self) -> None:
        """Test handling of invalid file paths."""
        from paise2.plugins.providers.cache import CacheMetadata

        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir)

            # File not in partition structure
            invalid_file = cache_dir / "not-a-uuid.txt"
            invalid_file.touch()
            assert CacheMetadata.from_file_path(cache_dir, invalid_file) is None

            # File with invalid UUID
            partition_dir = cache_dir / "test.partition"
            partition_dir.mkdir()
            invalid_uuid_file = partition_dir / "not-a-valid-uuid.txt"
            invalid_uuid_file.touch()
            assert CacheMetadata.from_file_path(cache_dir, invalid_uuid_file) is None

    def test_edge_case_empty_strings(self) -> None:
        """Test edge cases with empty strings."""
        from paise2.plugins.providers.cache import CacheMetadata

        # Empty partition key should work
        metadata = CacheMetadata(
            partition_key="",
            file_extension="",
            unique_id="12345678-1234-1234-1234-123456789abc",
            is_binary=False,
        )

        cache_id = metadata.to_cache_id()
        decoded = CacheMetadata.from_cache_id(cache_id)
        assert decoded == metadata

    def test_file_path_structure_validation(self) -> None:
        """Test that get_file_path creates correct directory structure."""
        from paise2.plugins.providers.cache import CacheMetadata

        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir)

            metadata = CacheMetadata(
                partition_key="deep.nested.partition",
                file_extension=".test",
                unique_id="12345678-1234-1234-1234-123456789abc",
                is_binary=True,
            )

            file_path = metadata.get_file_path(cache_dir)

            # Should create proper path structure
            expected_path = (
                cache_dir
                / "deep.nested.partition"
                / "12345678-1234-1234-1234-123456789abc.bin.test"
            )
            assert file_path == expected_path

            # Should create directory
            assert file_path.parent.exists()
            assert file_path.parent.is_dir()

    def test_binary_flag_in_filename(self) -> None:
        """Test that binary flag is correctly encoded in filename."""
        from paise2.plugins.providers.cache import CacheMetadata

        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir)

            # Binary file should have .bin suffix
            binary_metadata = CacheMetadata(
                partition_key="test.plugin",
                file_extension=".jpg",
                unique_id="12345678-1234-1234-1234-123456789abc",
                is_binary=True,
            )

            binary_path = binary_metadata.get_file_path(cache_dir)
            assert ".bin." in str(binary_path)
            assert binary_path.name == "12345678-1234-1234-1234-123456789abc.bin.jpg"

            # Text file should not have .bin suffix
            text_metadata = CacheMetadata(
                partition_key="test.plugin",
                file_extension=".txt",
                unique_id="12345678-1234-1234-1234-123456789abc",
                is_binary=False,
            )

            text_path = text_metadata.get_file_path(cache_dir)
            assert ".bin" not in str(text_path)
            assert text_path.name == "12345678-1234-1234-1234-123456789abc.txt"
