# ABOUTME: Test suite for host infrastructure including BaseHost and StateManager.
# ABOUTME: Tests state partitioning, host factory functions, and basic functionality.

from __future__ import annotations

from unittest.mock import Mock

from paise2.plugins.core.hosts import BaseHost, create_base_host, create_state_manager
from paise2.plugins.core.interfaces import StateManager, StateStorage
from paise2.utils.logging import SimpleInMemoryLogger
from tests.fixtures import MockConfiguration


class TestStateManager:
    """Test StateManager with automatic partitioning by plugin module name."""

    def test_state_manager_creation(self) -> None:
        """Test StateManager creation with proper partitioning."""
        mock_storage = Mock(spec=StateStorage)
        plugin_module_name = "paise2.plugins.test_plugin"

        state_manager = create_state_manager(mock_storage, plugin_module_name)

        assert isinstance(state_manager, StateManager)
        assert hasattr(state_manager, "store")
        assert hasattr(state_manager, "get")

    def test_state_partitioning_by_module_name(self) -> None:
        """Test that state is automatically partitioned by plugin module name."""
        mock_storage = Mock(spec=StateStorage)
        plugin_module_name = "paise2.plugins.test_plugin"

        state_manager = create_state_manager(mock_storage, plugin_module_name)

        # Store a value
        state_manager.store("test_key", "test_value")

        # Verify storage was called with partition key (module name)
        mock_storage.store.assert_called_once_with(
            plugin_module_name, "test_key", "test_value", 1
        )

    def test_state_get_with_partitioning(self) -> None:
        """Test state retrieval uses correct partition."""
        mock_storage = Mock(spec=StateStorage)
        mock_storage.get.return_value = "retrieved_value"
        plugin_module_name = "paise2.plugins.test_plugin"

        state_manager = create_state_manager(mock_storage, plugin_module_name)

        result = state_manager.get("test_key", "default_value")

        mock_storage.get.assert_called_once_with(
            plugin_module_name, "test_key", "default_value"
        )
        assert result == "retrieved_value"

    def test_state_isolation_between_plugins(self) -> None:
        """Test that different plugins get isolated state storage."""
        mock_storage = Mock(spec=StateStorage)

        # Create state managers for two different plugins
        plugin1_state = create_state_manager(mock_storage, "paise2.plugins.plugin1")
        plugin2_state = create_state_manager(mock_storage, "paise2.plugins.plugin2")

        # Store values in each
        plugin1_state.store("key", "value1")
        plugin2_state.store("key", "value2")

        # Verify each used its own partition
        calls = mock_storage.store.call_args_list
        assert len(calls) == 2
        assert calls[0][0] == ("paise2.plugins.plugin1", "key", "value1", 1)
        assert calls[1][0] == ("paise2.plugins.plugin2", "key", "value2", 1)

    def test_state_versioning_support(self) -> None:
        """Test versioning support for plugin updates."""
        mock_storage = Mock(spec=StateStorage)
        mock_storage.get_versioned_state.return_value = [
            ("key1", "value1", 1),
            ("key2", "value2", 2),
        ]
        plugin_module_name = "paise2.plugins.test_plugin"

        state_manager = create_state_manager(mock_storage, plugin_module_name)

        result = state_manager.get_versioned_state(3)

        mock_storage.get_versioned_state.assert_called_once_with(plugin_module_name, 3)
        assert result == [("key1", "value1", 1), ("key2", "value2", 2)]

    def test_state_get_all_keys_with_value(self) -> None:
        """Test querying keys by value."""
        mock_storage = Mock(spec=StateStorage)
        mock_storage.get_all_keys_with_value.return_value = ["key1", "key2"]
        plugin_module_name = "paise2.plugins.test_plugin"

        state_manager = create_state_manager(mock_storage, plugin_module_name)

        result = state_manager.get_all_keys_with_value("target_value")

        mock_storage.get_all_keys_with_value.assert_called_once_with(
            plugin_module_name, "target_value"
        )
        assert result == ["key1", "key2"]

    def test_state_store_with_version(self) -> None:
        """Test storing state with explicit version."""
        mock_storage = Mock(spec=StateStorage)
        plugin_module_name = "paise2.plugins.test_plugin"

        state_manager = create_state_manager(mock_storage, plugin_module_name)

        state_manager.store("test_key", "test_value", version=5)

        mock_storage.store.assert_called_once_with(
            plugin_module_name, "test_key", "test_value", 5
        )


class TestBaseHost:
    """Test BaseHost class functionality."""

    def test_base_host_creation(self) -> None:
        """Test BaseHost creation with mock dependencies."""
        # Use SimpleInMemoryLogger instead of Mock
        mock_logger = SimpleInMemoryLogger()
        mock_configuration = MockConfiguration({"test": "config"})
        mock_state_storage = Mock(spec=StateStorage)
        plugin_module_name = "paise2.plugins.test_plugin"

        host = BaseHost(
            logger=mock_logger,
            configuration=mock_configuration,
            state_storage=mock_state_storage,
            plugin_module_name=plugin_module_name,
        )

        assert host.logger is mock_logger
        assert hasattr(host, "configuration")
        assert hasattr(host, "state")

    def test_base_host_state_property(self) -> None:
        """Test that BaseHost.state returns a StateManager."""
        mock_logger = SimpleInMemoryLogger()
        mock_configuration = MockConfiguration({"test": "config"})
        mock_state_storage = Mock(spec=StateStorage)
        plugin_module_name = "paise2.plugins.test_plugin"

        host = BaseHost(
            logger=mock_logger,
            configuration=mock_configuration,
            state_storage=mock_state_storage,
            plugin_module_name=plugin_module_name,
        )

        assert isinstance(host.state, StateManager)

    def test_base_host_state_uses_module_name(self) -> None:
        """Test that BaseHost creates state manager with correct module name."""
        mock_logger = SimpleInMemoryLogger()
        mock_configuration = MockConfiguration({"test": "config"})
        mock_state_storage = Mock(spec=StateStorage)
        plugin_module_name = "paise2.plugins.test_plugin"

        host = BaseHost(
            logger=mock_logger,
            configuration=mock_configuration,
            state_storage=mock_state_storage,
            plugin_module_name=plugin_module_name,
        )

        # Test that state operations use the correct partition
        host.state.store("test_key", "test_value")

        mock_state_storage.store.assert_called_once_with(
            plugin_module_name, "test_key", "test_value", 1
        )

    def test_base_host_schedule_fetch_placeholder(self) -> None:
        """Test that BaseHost has schedule_fetch method (placeholder for now)."""
        mock_logger = SimpleInMemoryLogger()
        mock_configuration = MockConfiguration({"test": "config"})
        mock_state_storage = Mock(spec=StateStorage)
        plugin_module_name = "paise2.plugins.test_plugin"

        host = BaseHost(
            logger=mock_logger,
            configuration=mock_configuration,
            state_storage=mock_state_storage,
            plugin_module_name=plugin_module_name,
        )

        # Should have the method but it's a placeholder for now
        assert hasattr(host, "schedule_fetch")
        # For now, just verify it doesn't crash when called
        host.schedule_fetch("http://example.com")


class TestHostFactories:
    """Test host factory functions."""

    def test_create_base_host_factory(self) -> None:
        """Test base host creation through factory function."""
        mock_logger = SimpleInMemoryLogger()
        mock_configuration = MockConfiguration({"test": "config"})
        mock_state_storage = Mock(spec=StateStorage)
        plugin_module_name = "paise2.plugins.test_plugin"

        # Import the factory function we'll create

        host = create_base_host(
            logger=mock_logger,
            configuration=mock_configuration,
            state_storage=mock_state_storage,
            plugin_module_name=plugin_module_name,
        )

        assert isinstance(host, BaseHost)
        assert host.logger is mock_logger
        assert hasattr(host, "configuration")


class TestModuleNameDetection:
    """Test automatic plugin module name detection."""

    def test_get_plugin_module_name_from_frame(self) -> None:
        """Test extracting plugin module name from call stack."""
        from paise2.plugins.core.hosts import get_plugin_module_name_from_frame

        # This test will validate the helper function we'll create
        # For now, just test that it returns a string
        module_name = get_plugin_module_name_from_frame()
        assert isinstance(module_name, str)
        assert "test_hosts" in module_name  # Should detect this test module


class TestStateManagerImplementation:
    """Test the concrete StateManager implementation."""

    def test_state_manager_implements_protocol(self) -> None:
        """Test that our StateManager implementation matches the protocol."""
        from paise2.plugins.core.hosts import ConcreteStateManager

        mock_storage = Mock(spec=StateStorage)

        state_manager = ConcreteStateManager(mock_storage, "test.module")

        # Verify it implements the StateManager protocol
        assert isinstance(state_manager, StateManager)
        assert hasattr(state_manager, "store")
        assert hasattr(state_manager, "get")
        assert hasattr(state_manager, "get_versioned_state")
        assert hasattr(state_manager, "get_all_keys_with_value")

    def test_concrete_state_manager_store_operation(self) -> None:
        """Test ConcreteStateManager store operation."""
        from paise2.plugins.core.hosts import ConcreteStateManager

        mock_storage = Mock(spec=StateStorage)

        state_manager = ConcreteStateManager(mock_storage, "test.module")
        state_manager.store("key", "value", version=2)

        mock_storage.store.assert_called_once_with("test.module", "key", "value", 2)

    def test_concrete_state_manager_get_operation(self) -> None:
        """Test ConcreteStateManager get operation."""
        from paise2.plugins.core.hosts import ConcreteStateManager

        mock_storage = Mock(spec=StateStorage)
        mock_storage.get.return_value = "retrieved"

        state_manager = ConcreteStateManager(mock_storage, "test.module")
        result = state_manager.get("key", "default")

        mock_storage.get.assert_called_once_with("test.module", "key", "default")
        assert result == "retrieved"
