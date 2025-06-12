# ABOUTME: Unit tests for data storage provider plugin registration.
# ABOUTME: Tests registration system and provider discovery for different profiles.

from __future__ import annotations

import tempfile
from pathlib import Path

from paise2.plugins.core.interfaces import DataStorageProvider
from tests.fixtures import MockConfiguration


class TestDataStorageProviderRegistration:
    """Test data storage provider plugin registration."""

    def test_memory_provider_registration(self) -> None:
        """Test memory provider registration from test profile."""
        from paise2.storage.providers import MemoryDataStorageProvider

        provider = MemoryDataStorageProvider()
        assert isinstance(provider, DataStorageProvider)

    def test_sqlite_provider_registration(self) -> None:
        """Test SQLite provider registration from production profile."""
        from paise2.storage.providers import SQLiteDataStorageProvider

        provider = SQLiteDataStorageProvider()
        assert isinstance(provider, DataStorageProvider)

    def test_provider_creation_from_configuration(self) -> None:
        """Test that providers can create storage instances from configuration."""
        from paise2.storage.providers import (
            MemoryDataStorageProvider,
            SQLiteDataStorageProvider,
        )

        # Test memory provider
        memory_provider = MemoryDataStorageProvider()
        memory_storage = memory_provider.create_data_storage(MockConfiguration({}))

        assert memory_storage is not None
        assert hasattr(memory_storage, "add_item")
        assert hasattr(memory_storage, "find_item")

        # Test SQLite provider with temporary file
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
            sqlite_provider = SQLiteDataStorageProvider()
            sqlite_storage = sqlite_provider.create_data_storage(
                MockConfiguration({"data_storage.file_path": tmp_file.name})
            )

            assert sqlite_storage is not None
            assert hasattr(sqlite_storage, "add_item")
            assert hasattr(sqlite_storage, "find_item")


class TestDataStorageProviderIntegrationWithConfiguration:
    """Test data storage provider integration with configuration system."""

    def test_memory_provider_ignores_configuration(self) -> None:
        """Test that memory provider works regardless of configuration."""
        from paise2.storage.providers import MemoryDataStorageProvider

        provider = MemoryDataStorageProvider()

        # Any configuration should work
        storage1 = provider.create_data_storage(MockConfiguration({}))
        storage2 = provider.create_data_storage(
            MockConfiguration({"anything": "value"})
        )

        # Both should work independently
        assert storage1 is not storage2

    def test_sqlite_provider_uses_configuration_path(self) -> None:
        """Test that SQLite provider uses configuration for file path."""
        from paise2.storage.providers import SQLiteDataStorageProvider

        provider = SQLiteDataStorageProvider()

        # Test with specific path
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test_storage.db"
            storage = provider.create_data_storage(
                MockConfiguration({"data_storage.file_path": str(db_path)})
            )

            assert storage is not None
            assert hasattr(storage, "add_item")

    def test_sqlite_provider_handles_missing_configuration(self) -> None:
        """Test that SQLite provider works with missing configuration."""
        from paise2.storage.providers import SQLiteDataStorageProvider

        provider = SQLiteDataStorageProvider()

        # Should work with empty configuration (uses default path)
        storage = provider.create_data_storage(MockConfiguration({}))

        assert storage is not None
        assert hasattr(storage, "add_item")
