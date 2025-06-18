# ABOUTME: Tests for task definition and singleton integration (PROMPT 18)
# ABOUTME: Tests the two-phase initialization pattern with task registry

from __future__ import annotations

from unittest.mock import Mock

from huey import MemoryHuey

from paise2.models import Metadata
from paise2.plugins.core.registry import PluginManager
from paise2.plugins.core.startup import Singletons
from paise2.plugins.core.tasks import TaskQueue, setup_tasks
from paise2.utils.logging import SimpleInMemoryLogger
from tests.fixtures import MockConfiguration
from tests.fixtures.mock_plugins import (
    MockCacheManager,
    MockContentFetcher,
    MockDataStorage,
    MockStateStorage,
)


class TestSetupTasks:
    """Test the setup_tasks function with different configurations."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        # Create mock plugin manager with required methods
        plugin_manager = PluginManager()
        # Empty list for basic tests - will cause "no fetcher found" error

        # Create mock singletons for testing
        self.mock_singletons = Singletons(
            plugin_manager=plugin_manager,
            logger=SimpleInMemoryLogger(),
            configuration=Mock(),
            state_storage=Mock(),
            task_queue=None,  # Will be set per test
            cache=Mock(),
            data_storage=Mock(),
        )

    def test_setup_tasks_with_none_huey_returns_empty_dict(self) -> None:
        """Test that setup_tasks returns empty dict when huey is None."""
        result = setup_tasks(None, self.mock_singletons)

        assert result == {}
        assert isinstance(result, dict)

    def test_setup_tasks_with_huey_returns_task_registry(self) -> None:
        """Test that setup_tasks returns task registry when huey is provided."""
        huey = MemoryHuey(immediate=True)

        result = setup_tasks(huey, self.mock_singletons)

        # Verify all expected tasks are present
        expected_tasks = {
            "fetch_content",
            "extract_content",
            "store_content",
            "cleanup_cache",
        }
        assert set(result.keys()) == expected_tasks

        # Verify all values are callable (task functions)
        for task_func in result.values():
            assert callable(task_func)

    def test_task_functions_are_properly_decorated(self) -> None:
        """Test that task functions can be called and return expected results."""
        huey = MemoryHuey(immediate=True)

        tasks = setup_tasks(huey, self.mock_singletons)

        # Test fetch_content_task
        fetch_result_obj = tasks["fetch_content"](
            "http://example.com", {"source": "test"}
        )
        fetch_result = fetch_result_obj()  # Get actual result when immediate=True
        assert fetch_result["status"] == "error"  # No fetchers available in mock
        assert "No fetcher found" in fetch_result["message"]

        # Test extract_content_task
        extract_result_obj = tasks["extract_content"]("test content", {"type": "text"})
        extract_result = extract_result_obj()
        assert extract_result["status"] == "success"
        assert extract_result["message"] == "Content extraction completed"

        # Test store_content_task
        store_result_obj = tasks["store_content"]({"data": "test"}, {"type": "text"})
        store_result = store_result_obj()
        assert store_result["status"] == "success"
        assert store_result["message"] == "Content stored successfully"

        # Test cleanup_cache_task
        cleanup_result_obj = tasks["cleanup_cache"](["id1", "id2", "id3"])
        cleanup_result = cleanup_result_obj()
        assert cleanup_result["status"] == "success"
        assert "3 cache entries" in cleanup_result["message"]

    def test_task_functions_use_singletons_logger(self) -> None:
        """Test that task functions properly use the singletons logger."""
        logger = SimpleInMemoryLogger()

        # Create mock plugin manager that returns empty list for get_content_fetchers
        mock_plugin_manager = Mock()
        mock_plugin_manager.get_content_fetchers.return_value = []

        singletons = Singletons(
            plugin_manager=mock_plugin_manager,
            logger=logger,
            configuration=MockConfiguration(),
            state_storage=MockStateStorage(),
            task_queue=None,
            cache=MockCacheManager(),
            data_storage=MockDataStorage(),
        )

        huey = MemoryHuey(immediate=True)
        task_queue = TaskQueue(huey, singletons)

        # Execute a task
        task_queue.fetch_content("http://example.com")

        # Verify logger was used
        logs = logger.get_logs()
        assert len(logs) == 1
        assert logs[0][1] == "WARNING"  # log level - warning for no fetcher found
        assert "No fetcher found" in logs[0][2]  # log message


class TestTwoPhaseInitialization:
    """Test the two-phase initialization pattern."""

    def test_asynchronous_execution_mode(self) -> None:
        """Test two-phase initialization with asynchronous execution (with Huey)."""
        huey = MemoryHuey(immediate=True)

        # Phase 1: Create singletons without tasks
        initial_singletons = Singletons(
            plugin_manager=Mock(),
            logger=SimpleInMemoryLogger(),
            configuration=MockConfiguration(),
            state_storage=MockStateStorage(),
            task_queue=None,
            cache=MockCacheManager(),
            data_storage=MockDataStorage(),
        )
        task_queue = TaskQueue(huey, initial_singletons)

        # Phase 2: Setup tasks and create final singletons
        final_singletons = Singletons(
            plugin_manager=initial_singletons.plugin_manager,
            logger=initial_singletons.logger,
            configuration=initial_singletons.configuration,
            state_storage=initial_singletons.state_storage,
            task_queue=task_queue,
            cache=initial_singletons.cache,
            data_storage=initial_singletons.data_storage,
        )

        # Verify asynchronous mode setup
        assert final_singletons.task_queue is task_queue


class TestTaskRegistryIntegration:
    """Test integration between task registry and singletons."""

    def test_tasks_have_access_to_singletons(self) -> None:
        """Test that tasks can access and use singletons correctly."""
        logger = SimpleInMemoryLogger()
        huey = MemoryHuey(immediate=True)
        plugin_manager = PluginManager()
        plugin_manager.register_content_fetcher(MockContentFetcher())

        singletons = Singletons(
            plugin_manager=plugin_manager,
            logger=logger,
            configuration=MockConfiguration(),
            state_storage=MockStateStorage(),
            task_queue=None,
            cache=MockCacheManager(),
            data_storage=MockDataStorage(),
        )

        task_queue = TaskQueue(huey, singletons)

        # Execute all tasks and verify they can access singletons
        task_queue.fetch_content("test://test.com")
        task_queue.extract_content("test content", Metadata("test://test.com"))
        task_queue.store_content("test content", Metadata("test://test.com"))
        task_queue.cleanup_cache([])

        # All tasks should have logged messages
        # fetch_content logs 2 messages: "Using fetcher" and async completion
        # extract_content logs 1 message: "Extract task scheduled"
        # store_content logs 1 message: "Store task scheduled for processed content"
        # cleanup_cache logs 1 message: "Cache cleanup task scheduled"
        logs = logger.get_logs()
        assert len(logs) == 5  # Updated to match actual count

        # Verify key log messages from each task
        log_messages = [log[2] for log in logs]
        assert any("Using fetcher MockContentFetcher" in msg for msg in log_messages)
        assert any("Extract task scheduled" in msg for msg in log_messages)
        assert any("Store task scheduled" in msg for msg in log_messages)
        assert any("Cache cleanup task scheduled" in msg for msg in log_messages)

    def test_task_registry_storage_in_singletons(self) -> None:
        """Test that task registry is properly stored in singletons."""
        huey = MemoryHuey(immediate=True)

        # Create mock plugin manager that returns empty list for get_content_fetchers
        mock_plugin_manager = Mock()
        mock_plugin_manager.get_content_fetchers.return_value = []

        # Simulate the two-phase initialization as done in startup
        initial_singletons = Singletons(
            plugin_manager=mock_plugin_manager,
            logger=SimpleInMemoryLogger(),
            configuration=MockConfiguration(),
            state_storage=MockStateStorage(),
            task_queue=None,
            cache=MockCacheManager(),
            data_storage=MockDataStorage(),
        )

        task_queue = TaskQueue(huey, initial_singletons)

        # Verify tasks can be called via singletons
        result = task_queue.fetch_content("http://example.com")
        # In immediate mode, result should be available via result.result or result()
        actual_result = result()

        assert isinstance(actual_result, dict)

        status = actual_result["status"]
        assert isinstance(status, str)
        assert status == "error"  # No fetcher available

        message = actual_result["message"]
        assert isinstance(message, str)
        assert "No fetcher found" in message
