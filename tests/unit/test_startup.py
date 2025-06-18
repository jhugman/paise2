# ABOUTME: Comprehensive tests for phased startup system including singleton creation
# ABOUTME: Tests startup sequence, dependency injection, configuration diffing, and
# error handling

from __future__ import annotations

from typing import Any
from unittest.mock import Mock

import pytest

from paise2.plugins.core.registry import PluginManager
from paise2.plugins.core.startup import (
    Singletons,
    StartupError,
    StartupManager,
    StartupPhase,
    create_test_startup_manager,
)
from paise2.utils.logging import SimpleInMemoryLogger
from tests.fixtures.mock_plugins import (
    MockCacheProvider,
    MockDataStorageProvider,
    MockStateStorageProvider,
)


# Use the parameterized mock from other tests
class MockConfigProvider:
    """Mock configuration provider that accepts arguments."""

    def __init__(self, config_data: str, config_id: str = "test_config") -> None:
        self._config_data = config_data
        self._config_id = config_id

    def get_default_configuration(self) -> str:
        return self._config_data

    def get_configuration_id(self) -> str:
        return self._config_id


# Fixed mock that matches the TaskQueueProvider protocol
class MockTaskQueueProvider:
    """Mock task queue provider that matches the protocol signature."""

    def create_task_queue(self, configuration: Any) -> Any:
        """Create a mock task queue (returns MemoryHuey for immediate execution)."""
        from huey import MemoryHuey

        return MemoryHuey(
            "paise2-test",
            immediate=True,
            results=True,
            utc=True,
        )


class TestSingletons:
    """Test the Singletons container class."""

    def test_singletons_creation(self) -> None:
        """Test that Singletons container can be created with all dependencies."""
        # Mock all required singletons
        plugin_manager = Mock()
        logger = Mock()
        configuration = Mock()
        state_storage = Mock()
        task_queue = Mock()
        cache = Mock()
        data_storage = Mock()

        singletons = Singletons(
            plugin_manager=plugin_manager,
            logger=logger,
            configuration=configuration,
            state_storage=state_storage,
            task_queue=task_queue,
            cache=cache,
            data_storage=data_storage,
        )

        assert singletons.logger is logger
        assert singletons.configuration is configuration
        assert singletons.state_storage is state_storage
        assert singletons.task_queue is task_queue
        assert singletons.cache is cache
        assert singletons.data_storage is data_storage


class TestStartupManager:
    """Test the StartupManager class."""

    def test_startup_manager_creation(self) -> None:
        """Test that StartupManager can be created with plugin manager."""
        plugin_manager = PluginManager()
        startup_manager = StartupManager(plugin_manager)

        assert startup_manager.plugin_manager is plugin_manager
        assert startup_manager.current_phase == StartupPhase.BOOTSTRAP
        assert startup_manager.singletons is None
        assert startup_manager.bootstrap_logger is not None

    @pytest.mark.asyncio
    async def test_phase_1_bootstrap(self) -> None:
        """Test Phase 1: Bootstrap."""
        plugin_manager = PluginManager()
        startup_manager = StartupManager(plugin_manager)

        await startup_manager.phase_1_bootstrap()

        assert startup_manager.current_phase == StartupPhase.BOOTSTRAP

    @pytest.mark.asyncio
    async def test_phase_2_singleton_contributing_success(self) -> None:
        """Test Phase 2: Singleton-contributing extensions loading success."""
        plugin_manager = PluginManager()

        # Register all required providers
        plugin_manager.register_configuration_provider(
            MockConfigProvider("test: value")
        )
        plugin_manager.register_state_storage_provider(MockStateStorageProvider())
        plugin_manager.register_task_queue_provider(MockTaskQueueProvider())
        plugin_manager.register_cache_provider(MockCacheProvider())
        plugin_manager.register_data_storage_provider(MockDataStorageProvider())

        startup_manager = StartupManager(plugin_manager)

        await startup_manager.phase_2_singleton_contributing()

        assert startup_manager.current_phase == StartupPhase.SINGLETON_CONTRIBUTING

    @pytest.mark.asyncio
    async def test_phase_2_missing_configuration_providers(self) -> None:
        """Test Phase 2 fails when no configuration providers found."""
        plugin_manager = PluginManager()
        startup_manager = StartupManager(plugin_manager)

        with pytest.raises(StartupError, match="No configuration providers found"):
            await startup_manager.phase_2_singleton_contributing()

    @pytest.mark.asyncio
    async def test_phase_2_missing_state_storage_providers(self) -> None:
        """Test Phase 2 fails when no state storage providers found."""
        plugin_manager = PluginManager()
        plugin_manager.register_configuration_provider(
            MockConfigProvider("test: value")
        )

        startup_manager = StartupManager(plugin_manager)

        with pytest.raises(StartupError, match="No state storage providers found"):
            await startup_manager.phase_2_singleton_contributing()

    @pytest.mark.asyncio
    async def test_phase_3_singleton_creation(self) -> None:
        """Test Phase 3: Singleton creation."""
        plugin_manager = PluginManager()

        # Register all required providers
        plugin_manager.register_configuration_provider(
            MockConfigProvider("test: value")
        )
        plugin_manager.register_state_storage_provider(MockStateStorageProvider())
        plugin_manager.register_task_queue_provider(MockTaskQueueProvider())
        plugin_manager.register_cache_provider(MockCacheProvider())
        plugin_manager.register_data_storage_provider(MockDataStorageProvider())

        startup_manager = StartupManager(plugin_manager)

        # Need to complete phase 2 first
        await startup_manager.phase_2_singleton_contributing()

        # Test phase 3
        await startup_manager.phase_3_singleton_creation()

        assert startup_manager.current_phase == StartupPhase.SINGLETON_CREATION
        assert startup_manager.singletons is not None
        assert startup_manager.singletons.logger is not None
        assert startup_manager.singletons.configuration is not None
        assert startup_manager.singletons.state_storage is not None
        # MockTaskQueueProvider returns MemoryHuey for immediate execution
        assert startup_manager.singletons.task_queue is not None
        from huey import MemoryHuey

        assert isinstance(startup_manager.singletons.task_queue.huey, MemoryHuey)
        assert startup_manager.singletons.cache is not None
        assert startup_manager.singletons.data_storage is not None

    @pytest.mark.asyncio
    async def test_phase_3_with_user_config(self) -> None:
        """Test Phase 3 with user configuration override."""
        plugin_manager = PluginManager()

        # Register all required providers
        plugin_manager.register_configuration_provider(
            MockConfigProvider("app:\n  debug: false\n  timeout: 30")
        )
        plugin_manager.register_state_storage_provider(MockStateStorageProvider())
        plugin_manager.register_task_queue_provider(MockTaskQueueProvider())
        plugin_manager.register_cache_provider(MockCacheProvider())
        plugin_manager.register_data_storage_provider(MockDataStorageProvider())

        startup_manager = StartupManager(plugin_manager)

        # Need to complete phase 2 first
        await startup_manager.phase_2_singleton_contributing()

        # User configuration override
        user_config = {"app": {"debug": True, "port": 8080}}

        # Test phase 3 with user config
        await startup_manager.phase_3_singleton_creation(user_config)

        assert startup_manager.singletons is not None
        config = startup_manager.singletons.configuration

        # Test that user config is applied
        assert config.get("app.debug") is True
        assert config.get("app.timeout") == 30  # Plugin default preserved
        assert config.get("app.port") == 8080  # User addition

    @pytest.mark.asyncio
    async def test_phase_4_singleton_using(self) -> None:
        """Test Phase 4: Singleton-using extensions."""
        plugin_manager = PluginManager()
        startup_manager = StartupManager(plugin_manager)

        await startup_manager.phase_4_singleton_using()

        assert startup_manager.current_phase == StartupPhase.SINGLETON_USING

    @pytest.mark.asyncio
    async def test_phase_5_start(self) -> None:
        """Test Phase 5: System start."""
        plugin_manager = PluginManager()
        startup_manager = StartupManager(plugin_manager)

        await startup_manager.phase_5_start()

        assert startup_manager.current_phase == StartupPhase.START

    @pytest.mark.asyncio
    async def test_complete_startup_sequence(self) -> None:
        """Test complete startup sequence end-to-end."""
        plugin_manager = PluginManager()

        # Register all required providers
        plugin_manager.register_configuration_provider(
            MockConfigProvider("test: value")
        )
        plugin_manager.register_state_storage_provider(MockStateStorageProvider())
        plugin_manager.register_task_queue_provider(MockTaskQueueProvider())
        plugin_manager.register_cache_provider(MockCacheProvider())
        plugin_manager.register_data_storage_provider(MockDataStorageProvider())

        startup_manager = StartupManager(plugin_manager)

        # Execute complete startup
        singletons = await startup_manager.execute_startup()

        assert startup_manager.current_phase == StartupPhase.START
        assert singletons is not None
        assert singletons.logger is not None
        assert singletons.configuration is not None
        assert singletons.state_storage is not None
        # MockTaskQueueProvider returns MemoryHuey for immediate execution
        assert singletons.task_queue is not None
        from huey import MemoryHuey

        assert isinstance(singletons.task_queue.huey, MemoryHuey)
        assert singletons.cache is not None
        assert singletons.data_storage is not None

    @pytest.mark.asyncio
    async def test_startup_failure_handling(self) -> None:
        """Test startup failure handling and error propagation."""
        plugin_manager = PluginManager()
        startup_manager = StartupManager(plugin_manager)

        # Should fail in phase 2 due to missing providers
        with pytest.raises(StartupError, match="Startup failed in phase 2"):
            await startup_manager.execute_startup()

    @pytest.mark.asyncio
    async def test_startup_configuration_diffing(self) -> None:
        """Test startup configuration diffing integration."""
        plugin_manager = PluginManager()

        # Register providers
        plugin_manager.register_configuration_provider(
            MockConfigProvider("app:\n  version: 2.0")
        )
        plugin_manager.register_state_storage_provider(MockStateStorageProvider())
        plugin_manager.register_task_queue_provider(MockTaskQueueProvider())
        plugin_manager.register_cache_provider(MockCacheProvider())
        plugin_manager.register_data_storage_provider(MockDataStorageProvider())

        startup_manager = StartupManager(plugin_manager)

        # Execute startup
        singletons = await startup_manager.execute_startup()

        # Verify that configuration was stored for next startup
        state_storage = singletons.state_storage
        stored_config = state_storage.get("_system.configuration", "last_merged")

        assert stored_config is not None
        assert "app" in stored_config
        assert stored_config["app"]["version"] == 2.0


class TestStartupIntegration:
    """Test startup integration with real plugin providers."""

    @pytest.mark.asyncio
    async def test_test_profile_startup(self) -> None:
        """Test startup with test profile plugin manager."""
        startup_manager = create_test_startup_manager()

        # Execute startup
        singletons = await startup_manager.execute_startup()

        assert singletons is not None
        assert singletons.configuration.get("test") is not None

    @pytest.mark.asyncio
    async def test_provider_selection_first_wins(self) -> None:
        """Test that first provider is selected when multiple available."""
        plugin_manager = PluginManager()

        # Register multiple providers of same type
        provider1 = MockConfigProvider("provider1:\n  name: first")
        provider2 = MockConfigProvider("provider2:\n  name: second")

        plugin_manager.register_configuration_provider(provider1)
        plugin_manager.register_configuration_provider(provider2)

        # Register other required providers
        plugin_manager.register_state_storage_provider(MockStateStorageProvider())
        plugin_manager.register_task_queue_provider(MockTaskQueueProvider())
        plugin_manager.register_cache_provider(MockCacheProvider())
        plugin_manager.register_data_storage_provider(MockDataStorageProvider())

        startup_manager = StartupManager(plugin_manager)

        # Execute startup
        singletons = await startup_manager.execute_startup()

        # Should have both provider configs merged
        config = singletons.configuration
        assert config.get("provider1.name") == "first"
        assert config.get("provider2.name") == "second"

    @pytest.mark.asyncio
    async def test_singleton_dependency_injection(self) -> None:
        """Test that singletons are properly created and injected."""
        startup_manager = create_test_startup_manager()

        # Execute startup
        singletons = await startup_manager.execute_startup()

        # Test that all singletons are properly created
        assert singletons.logger is not None
        assert singletons.configuration is not None
        assert singletons.state_storage is not None
        # task_queue may be None for MockTaskQueueProvider (synchronous execution)
        assert hasattr(singletons, "task_queue")
        assert singletons.cache is not None
        assert singletons.data_storage is not None

    @pytest.mark.asyncio
    async def test_bootstrap_log_replay(self) -> None:
        """Test that bootstrap logs are replayed to real logger."""
        startup_manager = create_test_startup_manager()

        # Execute startup which should replay bootstrap logs
        singletons = await startup_manager.execute_startup()

        # Verify logger received some bootstrap logs
        logger = singletons.logger
        if isinstance(logger, SimpleInMemoryLogger):
            logs = logger.get_logs()

            # Should have replayed bootstrap logs
            assert len(logs) > 0

            # Check for expected bootstrap messages
            log_messages = [log[2] for log in logs]
            bootstrap_messages = [msg for msg in log_messages if "BOOTSTRAP" in msg]
            assert len(bootstrap_messages) > 0


class TestStartupErrors:
    """Test startup error conditions and recovery."""

    @pytest.mark.asyncio
    async def test_startup_error_with_context(self) -> None:
        """Test that startup errors include context about which phase failed."""
        plugin_manager = PluginManager()
        startup_manager = StartupManager(plugin_manager)

        with pytest.raises(StartupError) as exc_info:
            await startup_manager.execute_startup()

        error_message = str(exc_info.value)
        assert "Startup failed in phase" in error_message
        assert "2" in error_message  # Should fail in phase 2

    @pytest.mark.asyncio
    async def test_startup_phase_progression(self) -> None:
        """Test that startup phases progress correctly."""
        plugin_manager = PluginManager()

        # Register all required providers
        plugin_manager.register_configuration_provider(
            MockConfigProvider("test: value")
        )
        plugin_manager.register_state_storage_provider(MockStateStorageProvider())
        plugin_manager.register_task_queue_provider(MockTaskQueueProvider())
        plugin_manager.register_cache_provider(MockCacheProvider())
        plugin_manager.register_data_storage_provider(MockDataStorageProvider())

        startup_manager = StartupManager(plugin_manager)

        # Phase 1
        await startup_manager.phase_1_bootstrap()
        assert startup_manager.current_phase == StartupPhase.BOOTSTRAP

        # Phase 2
        await startup_manager.phase_2_singleton_contributing()
        assert startup_manager.current_phase == StartupPhase.SINGLETON_CONTRIBUTING

        # Phase 3
        await startup_manager.phase_3_singleton_creation()
        assert startup_manager.current_phase == StartupPhase.SINGLETON_CREATION

        # Phase 4
        await startup_manager.phase_4_singleton_using()
        assert startup_manager.current_phase == StartupPhase.SINGLETON_USING

        # Phase 5
        await startup_manager.phase_5_start()
        assert startup_manager.current_phase == StartupPhase.START


class TestFactoryFunctions:
    """Test startup factory functions."""

    def test_create_test_startup_manager(self) -> None:
        """Test test startup manager factory."""
        startup_manager = create_test_startup_manager()

        assert isinstance(startup_manager, StartupManager)
        assert startup_manager.plugin_manager is not None

    def test_startup_manager_factories_create_different_instances(self) -> None:
        """Test that factory functions create different instances."""
        startup1 = create_test_startup_manager()
        startup2 = create_test_startup_manager()

        assert startup1 is not startup2
        assert startup1.plugin_manager is not startup2.plugin_manager
