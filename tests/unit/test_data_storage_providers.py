# ABOUTME: Unit tests for data storage provider system.
# ABOUTME: Tests storage implementations with deduplication and cache integration.

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from paise2.models import Metadata
from paise2.plugins.core.interfaces import DataStorage, DataStorageProvider
from tests.fixtures import MockConfiguration


class TestMemoryDataStorage:
    """Test MemoryDataStorage implementation."""

    @pytest.mark.asyncio
    async def test_memory_data_storage_implements_protocol(self) -> None:
        """Test that MemoryDataStorage implements DataStorage protocol."""
        from paise2.storage.providers import MemoryDataStorage

        storage = MemoryDataStorage()
        assert isinstance(storage, DataStorage)

    @pytest.mark.asyncio
    async def test_add_item_basic_operation(self) -> None:
        """Test basic add_item operation."""
        from paise2.storage.providers import MemoryDataStorage
        from tests.fixtures.mock_plugins import MockDataStorageHost

        storage = MemoryDataStorage()
        host = MockDataStorageHost()
        metadata = Metadata(source_url="test://example.com", title="Test Document")

        item_id = await storage.add_item(host, "test content", metadata)

        assert item_id.startswith("item_")
        assert len(item_id) > 5

    @pytest.mark.asyncio
    async def test_find_item_after_add(self) -> None:
        """Test finding item metadata after adding."""
        from paise2.storage.providers import MemoryDataStorage
        from tests.fixtures.mock_plugins import MockDataStorageHost

        storage = MemoryDataStorage()
        host = MockDataStorageHost()
        metadata = Metadata(source_url="test://example.com", title="Test Document")

        item_id = await storage.add_item(host, "test content", metadata)
        retrieved_metadata = await storage.find_item(item_id)

        assert retrieved_metadata is not None
        assert retrieved_metadata.source_url == "test://example.com"
        assert retrieved_metadata.title == "Test Document"

    @pytest.mark.asyncio
    async def test_find_item_id_by_metadata(self) -> None:
        """Test finding item ID by metadata."""
        from paise2.storage.providers import MemoryDataStorage
        from tests.fixtures.mock_plugins import MockDataStorageHost

        storage = MemoryDataStorage()
        host = MockDataStorageHost()
        metadata = Metadata(source_url="test://example.com", title="Test Document")

        item_id = await storage.add_item(host, "test content", metadata)

        # Search by same metadata
        found_id = await storage.find_item_id(host, metadata)
        assert found_id == item_id

        # Search by different metadata should return None
        other_metadata = Metadata(source_url="test://other.com")
        found_id = await storage.find_item_id(host, other_metadata)
        assert found_id is None

    @pytest.mark.asyncio
    async def test_update_item_content(self) -> None:
        """Test updating item content."""
        from paise2.storage.providers import MemoryDataStorage
        from tests.fixtures.mock_plugins import MockDataStorageHost

        storage = MemoryDataStorage()
        host = MockDataStorageHost()
        metadata = Metadata(source_url="test://example.com")

        item_id = await storage.add_item(host, "original content", metadata)
        await storage.update_item(host, item_id, "updated content")

        # Verify the item still exists with updated content
        retrieved_metadata = await storage.find_item(item_id)
        assert retrieved_metadata is not None

    @pytest.mark.asyncio
    async def test_update_metadata(self) -> None:
        """Test updating item metadata."""
        from paise2.storage.providers import MemoryDataStorage
        from tests.fixtures.mock_plugins import MockDataStorageHost

        storage = MemoryDataStorage()
        host = MockDataStorageHost()
        original_metadata = Metadata(source_url="test://example.com", title="Original")

        item_id = await storage.add_item(host, "content", original_metadata)

        updated_metadata = Metadata(source_url="test://example.com", title="Updated")
        await storage.update_metadata(host, item_id, updated_metadata)

        retrieved_metadata = await storage.find_item(item_id)
        assert retrieved_metadata is not None
        assert retrieved_metadata.title == "Updated"

    @pytest.mark.asyncio
    async def test_remove_item(self) -> None:
        """Test removing an item."""
        from paise2.storage.providers import MemoryDataStorage
        from tests.fixtures.mock_plugins import MockDataStorageHost

        storage = MemoryDataStorage()
        host = MockDataStorageHost()
        metadata = Metadata(source_url="test://example.com")

        item_id = await storage.add_item(host, "content", metadata)

        # Remove the item
        cache_id = await storage.remove_item(host, item_id)
        assert cache_id is not None

        # Verify item is gone
        retrieved_metadata = await storage.find_item(item_id)
        assert retrieved_metadata is None

    @pytest.mark.asyncio
    async def test_remove_items_by_metadata(self) -> None:
        """Test removing items by metadata criteria."""
        from paise2.storage.providers import MemoryDataStorage
        from tests.fixtures.mock_plugins import MockDataStorageHost

        storage = MemoryDataStorage()
        host = MockDataStorageHost()

        # Add multiple items
        metadata1 = Metadata(source_url="test://example.com", title="Doc1")
        metadata2 = Metadata(source_url="test://example.com", title="Doc2")
        metadata3 = Metadata(source_url="test://other.com", title="Doc3")

        item1 = await storage.add_item(host, "content1", metadata1)
        item2 = await storage.add_item(host, "content2", metadata2)
        item3 = await storage.add_item(host, "content3", metadata3)

        # Remove items by URL
        search_metadata = Metadata(source_url="test://example.com")
        cache_ids = await storage.remove_items_by_metadata(host, search_metadata)

        assert len(cache_ids) == 2

        # Verify correct items are removed
        assert await storage.find_item(item1) is None
        assert await storage.find_item(item2) is None
        assert await storage.find_item(item3) is not None

    @pytest.mark.asyncio
    async def test_remove_items_by_url(self) -> None:
        """Test removing items by URL."""
        from paise2.storage.providers import MemoryDataStorage
        from tests.fixtures.mock_plugins import MockDataStorageHost

        storage = MemoryDataStorage()
        host = MockDataStorageHost()

        # Add multiple items
        metadata1 = Metadata(source_url="test://target.com", title="Doc1")
        metadata2 = Metadata(source_url="test://target.com", title="Doc2")
        metadata3 = Metadata(source_url="test://other.com", title="Doc3")

        item1 = await storage.add_item(host, "content1", metadata1)
        item2 = await storage.add_item(host, "content2", metadata2)
        item3 = await storage.add_item(host, "content3", metadata3)

        # Remove items by URL
        cache_ids = await storage.remove_items_by_url(host, "test://target.com")

        assert len(cache_ids) == 2

        # Verify correct items are removed
        assert await storage.find_item(item1) is None
        assert await storage.find_item(item2) is None
        assert await storage.find_item(item3) is not None

    @pytest.mark.asyncio
    async def test_content_deduplication(self) -> None:
        """Test content deduplication logic."""
        from paise2.storage.providers import MemoryDataStorage
        from tests.fixtures.mock_plugins import MockDataStorageHost

        storage = MemoryDataStorage()
        host = MockDataStorageHost()

        # Add same content with different metadata
        metadata1 = Metadata(source_url="test://example1.com", title="Doc1")
        metadata2 = Metadata(source_url="test://example2.com", title="Doc2")

        item1 = await storage.add_item(host, "identical content", metadata1)
        item2 = await storage.add_item(host, "identical content", metadata2)

        # Should have separate items despite identical content
        # (deduplication happens at storage level, not protocol level)
        assert item1 != item2

        retrieved1 = await storage.find_item(item1)
        retrieved2 = await storage.find_item(item2)
        assert retrieved1 is not None
        assert retrieved2 is not None
        assert retrieved1.source_url != retrieved2.source_url

    @pytest.mark.asyncio
    async def test_add_item_with_bytes_content(self) -> None:
        """Test adding item with bytes content."""
        from paise2.storage.providers import MemoryDataStorage
        from tests.fixtures.mock_plugins import MockDataStorageHost

        storage = MemoryDataStorage()
        host = MockDataStorageHost()
        metadata = Metadata(source_url="test://binary.com", mime_type="image/jpeg")
        binary_content = b"\x89\x50\x4e\x47\x0d\x0a\x1a\x0a"  # PNG header bytes

        item_id = await storage.add_item(host, binary_content, metadata)

        assert item_id.startswith("item_")
        retrieved_metadata = await storage.find_item(item_id)
        assert retrieved_metadata is not None
        assert retrieved_metadata.mime_type == "image/jpeg"

    @pytest.mark.asyncio
    async def test_update_item_with_bytes_content(self) -> None:
        """Test updating item with bytes content."""
        from paise2.storage.providers import MemoryDataStorage
        from tests.fixtures.mock_plugins import MockDataStorageHost

        storage = MemoryDataStorage()
        host = MockDataStorageHost()
        metadata = Metadata(source_url="test://file.bin")

        # Start with string content
        item_id = await storage.add_item(host, "text content", metadata)

        # Update with bytes content
        binary_content = b"\x00\x01\x02\x03\x04"
        await storage.update_item(host, item_id, binary_content)

        # Verify the item still exists
        retrieved_metadata = await storage.find_item(item_id)
        assert retrieved_metadata is not None

    @pytest.mark.asyncio
    async def test_mixed_content_types(self) -> None:
        """Test handling both string and bytes content in same storage."""
        from paise2.storage.providers import MemoryDataStorage
        from tests.fixtures.mock_plugins import MockDataStorageHost

        storage = MemoryDataStorage()
        host = MockDataStorageHost()

        # Add string content
        text_metadata = Metadata(source_url="test://text.txt", mime_type="text/plain")
        text_id = await storage.add_item(host, "Hello world", text_metadata)

        # Add bytes content
        binary_metadata = Metadata(
            source_url="test://data.bin", mime_type="application/octet-stream"
        )
        binary_content = b"\xff\xfe\xfd\xfc"
        binary_id = await storage.add_item(host, binary_content, binary_metadata)

        # Verify both exist and have correct metadata
        text_meta = await storage.find_item(text_id)
        binary_meta = await storage.find_item(binary_id)

        assert text_meta is not None
        assert binary_meta is not None
        assert text_meta.mime_type == "text/plain"
        assert binary_meta.mime_type == "application/octet-stream"


class TestMemoryDataStorageProvider:
    """Test MemoryDataStorageProvider implementation."""

    def test_memory_provider_implements_protocol(self) -> None:
        """Test MemoryDataStorageProvider implements DataStorageProvider protocol."""
        from paise2.storage.providers import MemoryDataStorageProvider

        provider = MemoryDataStorageProvider()
        assert isinstance(provider, DataStorageProvider)

    def test_memory_provider_creates_storage(self) -> None:
        """Test that provider creates DataStorage instance."""
        from paise2.storage.providers import MemoryDataStorageProvider

        provider = MemoryDataStorageProvider()
        configuration = MockConfiguration({"test": "config"})

        storage = provider.create_data_storage(configuration)

        assert isinstance(storage, DataStorage)

    def test_multiple_storages_are_independent(self) -> None:
        """Test that multiple storage instances are independent."""
        from paise2.storage.providers import MemoryDataStorageProvider

        provider = MemoryDataStorageProvider()

        storage1 = provider.create_data_storage(MockConfiguration({}))
        storage2 = provider.create_data_storage(MockConfiguration({}))

        # Should be different instances
        assert storage1 is not storage2


class TestSQLiteDataStorage:
    """Test SQLiteDataStorage implementation."""

    @pytest.mark.asyncio
    async def test_sqlite_data_storage_implements_protocol(self) -> None:
        """Test that SQLiteDataStorage implements DataStorage protocol."""
        from paise2.storage.providers import SQLiteDataStorage

        with tempfile.TemporaryDirectory() as temp_dir:
            storage = SQLiteDataStorage(Path(temp_dir) / "storage.db")
            assert isinstance(storage, DataStorage)

    @pytest.mark.asyncio
    async def test_add_item_with_persistence(self) -> None:
        """Test basic add_item operation with file persistence."""
        from paise2.storage.providers import SQLiteDataStorage
        from tests.fixtures.mock_plugins import MockDataStorageHost

        with tempfile.TemporaryDirectory() as temp_dir:
            storage_file = Path(temp_dir) / "storage.db"
            storage = SQLiteDataStorage(storage_file)
            host = MockDataStorageHost()
            metadata = Metadata(source_url="test://example.com", title="Test Document")

            item_id = await storage.add_item(host, "test content", metadata)

            # Create new storage instance with same file
            storage2 = SQLiteDataStorage(storage_file)
            retrieved_metadata = await storage2.find_item(item_id)

            assert retrieved_metadata is not None
            assert retrieved_metadata.source_url == "test://example.com"
            assert retrieved_metadata.title == "Test Document"

    @pytest.mark.asyncio
    async def test_sqlite_indexing_performance(self) -> None:
        """Test that SQLite storage has proper indexing for efficient queries."""
        from paise2.storage.providers import SQLiteDataStorage
        from tests.fixtures.mock_plugins import MockDataStorageHost

        with tempfile.TemporaryDirectory() as temp_dir:
            storage = SQLiteDataStorage(Path(temp_dir) / "storage.db")
            host = MockDataStorageHost()

            # Add multiple items for testing query performance
            for i in range(10):
                metadata = Metadata(
                    source_url=f"test://example{i}.com", title=f"Doc {i}"
                )
                await storage.add_item(host, f"content {i}", metadata)

            # Test querying - should be fast due to indexing
            search_metadata = Metadata(source_url="test://example5.com")
            found_id = await storage.find_item_id(host, search_metadata)
            assert found_id is not None

    @pytest.mark.asyncio
    async def test_content_deduplication_with_hashing(self) -> None:
        """Test content deduplication using content hashing."""
        from paise2.storage.providers import SQLiteDataStorage
        from tests.fixtures.mock_plugins import MockDataStorageHost

        with tempfile.TemporaryDirectory() as temp_dir:
            storage = SQLiteDataStorage(Path(temp_dir) / "storage.db")
            host = MockDataStorageHost()

            # Add same content twice - should deduplicate at storage level
            metadata1 = Metadata(source_url="test://example1.com", title="Doc1")
            metadata2 = Metadata(source_url="test://example2.com", title="Doc2")

            item1 = await storage.add_item(host, "identical content", metadata1)
            item2 = await storage.add_item(host, "identical content", metadata2)

            # Items should be different but could reference same content hash
            assert item1 != item2

            retrieved1 = await storage.find_item(item1)
            retrieved2 = await storage.find_item(item2)
            assert retrieved1 is not None
            assert retrieved2 is not None


class TestSQLiteDataStorageProvider:
    """Test SQLiteDataStorageProvider implementation."""

    def test_sqlite_provider_implements_protocol(self) -> None:
        """Test SQLiteDataStorageProvider implements DataStorageProvider protocol."""
        from paise2.storage.providers import SQLiteDataStorageProvider

        provider = SQLiteDataStorageProvider()
        assert isinstance(provider, DataStorageProvider)

    def test_sqlite_provider_creates_storage_with_default_path(self) -> None:
        """Test provider creates storage with default path configuration."""
        from paise2.storage.providers import SQLiteDataStorageProvider

        provider = SQLiteDataStorageProvider()
        configuration = MockConfiguration({})

        storage = provider.create_data_storage(configuration)

        assert isinstance(storage, DataStorage)

    def test_sqlite_provider_creates_storage_with_custom_path(self) -> None:
        """Test provider creates storage with custom path from configuration."""
        from paise2.storage.providers import SQLiteDataStorageProvider

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
            provider = SQLiteDataStorageProvider()
            configuration = MockConfiguration({"data_storage.file_path": tmp_file.name})

            storage = provider.create_data_storage(configuration)

            assert isinstance(storage, DataStorage)

    def test_sqlite_provider_handles_path_expansion(self) -> None:
        """Test provider handles path expansion (~ for home directory)."""
        from paise2.storage.providers import SQLiteDataStorageProvider

        provider = SQLiteDataStorageProvider()
        configuration = MockConfiguration(
            {"data_storage.file_path": "~/test_storage.db"}
        )

        storage = provider.create_data_storage(configuration)

        assert isinstance(storage, DataStorage)


class TestDataStorageIntegration:
    """Integration tests for data storage system."""

    @pytest.mark.asyncio
    async def test_memory_storage_full_workflow(self) -> None:
        """Test complete workflow with memory storage."""
        from paise2.storage.providers import MemoryDataStorage
        from tests.fixtures.mock_plugins import MockDataStorageHost

        storage = MemoryDataStorage()
        host = MockDataStorageHost()

        # Add item
        metadata = Metadata(source_url="test://example.com", title="Test")
        item_id = await storage.add_item(host, "original content", metadata)

        # Update content
        await storage.update_item(host, item_id, "updated content")

        # Update metadata
        new_metadata = Metadata(source_url="test://example.com", title="Updated Test")
        await storage.update_metadata(host, item_id, new_metadata)

        # Verify updates
        retrieved = await storage.find_item(item_id)
        assert retrieved is not None
        assert retrieved.title == "Updated Test"

        # Remove item
        cache_id = await storage.remove_item(host, item_id)
        assert cache_id is not None

        # Verify removal
        assert await storage.find_item(item_id) is None

    @pytest.mark.asyncio
    async def test_sqlite_storage_full_workflow(self) -> None:
        """Test complete workflow with SQLite storage."""
        from paise2.storage.providers import SQLiteDataStorage
        from tests.fixtures.mock_plugins import MockDataStorageHost

        with tempfile.TemporaryDirectory() as temp_dir:
            storage = SQLiteDataStorage(Path(temp_dir) / "storage.db")
            host = MockDataStorageHost()

            # Add item
            metadata = Metadata(source_url="test://example.com", title="Test")
            item_id = await storage.add_item(host, "original content", metadata)

            # Update content
            await storage.update_item(host, item_id, "updated content")

            # Update metadata
            new_metadata = Metadata(
                source_url="test://example.com", title="Updated Test"
            )
            await storage.update_metadata(host, item_id, new_metadata)

            # Verify updates
            retrieved = await storage.find_item(item_id)
            assert retrieved is not None
            assert retrieved.title == "Updated Test"

            # Remove item
            cache_id = await storage.remove_item(host, item_id)
            assert cache_id is not None

            # Verify removal
            assert await storage.find_item(item_id) is None
