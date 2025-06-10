# ABOUTME: Unit tests for state storage provider system.
# ABOUTME: Tests StateStorage implementations with partitioning and versioning.

import tempfile
from pathlib import Path

from paise2.plugins.core.interfaces import StateStorage, StateStorageProvider
from paise2.state.models import StateEntry
from paise2.state.providers import (
    FileStateStorage,
    FileStateStorageProvider,
    MemoryStateStorage,
    MemoryStateStorageProvider,
)


class TestStateEntry:
    """Test StateEntry data model."""

    def test_state_entry_creation(self):
        """Test StateEntry creation with all fields."""
        entry = StateEntry(
            partition_key="test.plugin",
            key="test_key",
            value={"data": "value"},
            version=2,
        )

        assert entry.partition_key == "test.plugin"
        assert entry.key == "test_key"
        assert entry.value == {"data": "value"}
        assert entry.version == 2

    def test_state_entry_with_value(self):
        """Test StateEntry immutable value update."""
        original = StateEntry("test.plugin", "key", "old_value", 1)
        updated = original.with_value("new_value")

        # Original unchanged
        assert original.value == "old_value"
        assert original.version == 1

        # New entry has updated value
        assert updated.value == "new_value"
        assert updated.version == 1  # Version preserved
        assert updated.partition_key == "test.plugin"
        assert updated.key == "key"

    def test_state_entry_with_version(self):
        """Test StateEntry immutable version update."""
        original = StateEntry("test.plugin", "key", "value", 1)
        updated = original.with_version(3)

        # Original unchanged
        assert original.version == 1
        assert original.value == "value"

        # New entry has updated version
        assert updated.version == 3
        assert updated.value == "value"  # Value preserved
        assert updated.partition_key == "test.plugin"
        assert updated.key == "key"


class TestMemoryStateStorage:
    """Test MemoryStateStorage implementation."""

    def test_memory_state_storage_implements_protocol(self):
        """Test that MemoryStateStorage implements StateStorage protocol."""
        storage = MemoryStateStorage()
        assert isinstance(storage, StateStorage)

    def test_store_and_get_basic_operations(self):
        """Test basic store and get operations."""
        storage = MemoryStateStorage()

        storage.store("plugin1", "key1", "value1")

        result = storage.get("plugin1", "key1")
        assert result == "value1"

    def test_get_with_default_value(self):
        """Test get operation with default value for missing keys."""
        storage = MemoryStateStorage()

        result = storage.get("plugin1", "missing_key", "default")
        assert result == "default"

    def test_automatic_partitioning_isolation(self):
        """Test that partitions are properly isolated."""
        storage = MemoryStateStorage()

        # Store same key in different partitions
        storage.store("plugin1", "key", "value1")
        storage.store("plugin2", "key", "value2")

        # Verify isolation
        assert storage.get("plugin1", "key") == "value1"
        assert storage.get("plugin2", "key") == "value2"

    def test_versioning_support(self):
        """Test state versioning for plugin updates."""
        storage = MemoryStateStorage()

        # Store values with different versions
        storage.store("plugin1", "key1", "value1", version=1)
        storage.store("plugin1", "key2", "value2", version=2)
        storage.store("plugin1", "key3", "value3", version=3)

        # Get versioned state older than version 3
        versioned_state = storage.get_versioned_state("plugin1", older_than_version=3)

        # Should get entries with version 1 and 2
        assert len(versioned_state) == 2
        assert ("key1", "value1", 1) in versioned_state
        assert ("key2", "value2", 2) in versioned_state

    def test_get_all_keys_with_value(self):
        """Test querying keys by value."""
        storage = MemoryStateStorage()

        # Store multiple keys with same value
        storage.store("plugin1", "key1", "target_value")
        storage.store("plugin1", "key2", "other_value")
        storage.store("plugin1", "key3", "target_value")

        # Find keys with target value
        keys = storage.get_all_keys_with_value("plugin1", "target_value")

        assert len(keys) == 2
        assert "key1" in keys
        assert "key3" in keys
        assert "key2" not in keys

    def test_overwrite_existing_key(self):
        """Test that storing overwrites existing values."""
        storage = MemoryStateStorage()

        storage.store("plugin1", "key", "old_value", version=1)
        storage.store("plugin1", "key", "new_value", version=2)

        # Should get new value
        assert storage.get("plugin1", "key") == "new_value"

        # Version should be updated
        versioned_state = storage.get_versioned_state("plugin1", older_than_version=3)
        assert ("key", "new_value", 2) in versioned_state


class TestMemoryStateStorageProvider:
    """Test MemoryStateStorageProvider implementation."""

    def test_memory_provider_implements_protocol(self):
        """Test MemoryStateStorageProvider implements StateStorageProvider protocol."""
        provider = MemoryStateStorageProvider()
        assert isinstance(provider, StateStorageProvider)

    def test_memory_provider_creates_storage(self):
        """Test that provider creates StateStorage instance."""
        provider = MemoryStateStorageProvider()
        configuration = {"test": "config"}

        storage = provider.create_state_storage(configuration)

        assert isinstance(storage, StateStorage)
        assert isinstance(storage, MemoryStateStorage)

    def test_multiple_storages_are_independent(self):
        """Test that multiple storage instances are independent."""
        provider = MemoryStateStorageProvider()

        storage1 = provider.create_state_storage({})
        storage2 = provider.create_state_storage({})

        # Store in first storage
        storage1.store("plugin1", "key", "value1")

        # Should not appear in second storage
        assert storage2.get("plugin1", "key") is None


class TestFileStateStorage:
    """Test FileStateStorage implementation."""

    def test_file_state_storage_implements_protocol(self):
        """Test that FileStateStorage implements StateStorage protocol."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = FileStateStorage(Path(temp_dir) / "state.db")
            assert isinstance(storage, StateStorage)

    def test_store_and_get_with_persistence(self):
        """Test basic store and get operations with file persistence."""
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "state.db"

            # Store data
            storage1 = FileStateStorage(state_file)
            storage1.store("plugin1", "key1", "value1")

            # Create new storage instance with same file
            storage2 = FileStateStorage(state_file)

            # Should retrieve persisted data
            result = storage2.get("plugin1", "key1")
            assert result == "value1"

    def test_file_storage_partitioning(self):
        """Test partitioning isolation in file storage."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = FileStateStorage(Path(temp_dir) / "state.db")

            # Store same key in different partitions
            storage.store("plugin1", "key", "value1")
            storage.store("plugin2", "key", "value2")

            # Verify isolation
            assert storage.get("plugin1", "key") == "value1"
            assert storage.get("plugin2", "key") == "value2"

    def test_file_storage_versioning(self):
        """Test versioning with file persistence."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = FileStateStorage(Path(temp_dir) / "state.db")

            # Store values with different versions
            storage.store("plugin1", "key1", "value1", version=1)
            storage.store("plugin1", "key2", "value2", version=2)
            storage.store("plugin1", "key3", "value3", version=3)

            # Get versioned state
            versioned_state = storage.get_versioned_state(
                "plugin1", older_than_version=3
            )

            assert len(versioned_state) == 2
            assert ("key1", "value1", 1) in versioned_state
            assert ("key2", "value2", 2) in versioned_state

    def test_file_storage_get_all_keys_with_value(self):
        """Test querying keys by value with file storage."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = FileStateStorage(Path(temp_dir) / "state.db")

            # Store multiple keys with same value
            storage.store("plugin1", "key1", "target_value")
            storage.store("plugin1", "key2", "other_value")
            storage.store("plugin1", "key3", "target_value")

            # Find keys with target value
            keys = storage.get_all_keys_with_value("plugin1", "target_value")

            assert len(keys) == 2
            assert "key1" in keys
            assert "key3" in keys


class TestFileStateStorageProvider:
    """Test FileStateStorageProvider implementation."""

    def test_file_provider_implements_protocol(self):
        """Test FileStateStorageProvider implements StateStorageProvider protocol."""
        provider = FileStateStorageProvider()
        assert isinstance(provider, StateStorageProvider)

    def test_file_provider_creates_storage_with_default_path(self):
        """Test provider creates storage with default path configuration."""
        provider = FileStateStorageProvider()
        configuration = {}

        storage = provider.create_state_storage(configuration)

        assert isinstance(storage, StateStorage)
        assert isinstance(storage, FileStateStorage)

    def test_file_provider_creates_storage_with_custom_path(self):
        """Test provider creates storage with custom path from configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            custom_path = str(Path(temp_dir) / "custom_state.db")
            provider = FileStateStorageProvider()
            configuration = {"state_storage.file_path": custom_path}

            storage = provider.create_state_storage(configuration)

            assert isinstance(storage, FileStateStorage)

            # Test that it uses the custom path by storing and retrieving
            storage.store("test", "key", "value")
            assert storage.get("test", "key") == "value"

            # File should exist at custom path
            assert Path(custom_path).exists()

    def test_file_provider_handles_path_expansion(self):
        """Test provider handles path expansion (~ for home directory)."""
        provider = FileStateStorageProvider()
        configuration = {"state_storage.file_path": "~/test_state.db"}

        storage = provider.create_state_storage(configuration)

        assert isinstance(storage, FileStateStorage)
        # The path should be expanded, but we won't test the actual file creation
        # to avoid creating files in the user's home directory during tests


class TestStateStorageIntegration:
    """Integration tests for state storage system."""

    def test_memory_storage_integration_with_state_manager(self):
        """Test memory storage integration with ConcreteStateManager."""
        from paise2.plugins.core.hosts import ConcreteStateManager

        storage = MemoryStateStorage()
        state_manager = ConcreteStateManager(storage, "test.plugin")

        # Use state manager interface
        state_manager.store("key", "value", version=2)
        result = state_manager.get("key")

        assert result == "value"

        # Verify it was stored with proper partitioning
        direct_result = storage.get("test.plugin", "key")
        assert direct_result == "value"

    def test_file_storage_integration_with_state_manager(self):
        """Test file storage integration with ConcreteStateManager."""
        from paise2.plugins.core.hosts import ConcreteStateManager

        with tempfile.TemporaryDirectory() as temp_dir:
            storage = FileStateStorage(Path(temp_dir) / "state.db")
            state_manager = ConcreteStateManager(storage, "test.plugin")

            # Use state manager interface
            state_manager.store("key", "value", version=2)
            result = state_manager.get("key")

            assert result == "value"

            # Test persistence by creating new instances
            storage2 = FileStateStorage(Path(temp_dir) / "state.db")
            state_manager2 = ConcreteStateManager(storage2, "test.plugin")

            persistent_result = state_manager2.get("key")
            assert persistent_result == "value"
