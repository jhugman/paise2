# ABOUTME: Tests for task definition and singleton integration (PROMPT 18)
# ABOUTME: Tests the two-phase initialization pattern with task registry

from __future__ import annotations

from unittest.mock import Mock

from huey import MemoryHuey

from paise2.plugins.core.startup import Singletons, setup_tasks
from paise2.utils.logging import SimpleInMemoryLogger


class TestSetupTasks:
    """Test the setup_tasks function with different configurations."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        # Create mock singletons for testing
        self.mock_singletons = Singletons(
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
        assert fetch_result["status"] == "success"
        assert "http://example.com" in fetch_result["message"]

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
        singletons = Singletons(
            logger=logger,
            configuration=Mock(),
            state_storage=Mock(),
            task_queue=None,
            cache=Mock(),
            data_storage=Mock(),
        )

        huey = MemoryHuey(immediate=True)
        tasks = setup_tasks(huey, singletons)

        # Execute a task
        tasks["fetch_content"]("http://example.com")

        # Verify logger was used
        logs = logger.get_logs()
        assert len(logs) == 1
        assert logs[0][1] == "INFO"  # log level
        assert "Fetch task scheduled" in logs[0][2]  # log message


class TestSingletonsWithTasks:
    """Test the Singletons dataclass with task registry integration."""

    def test_singletons_creation_without_tasks(self) -> None:
        """Test creating Singletons without tasks parameter."""
        singletons = Singletons(
            logger=SimpleInMemoryLogger(),
            configuration=Mock(),
            state_storage=Mock(),
            task_queue=None,
            cache=Mock(),
            data_storage=Mock(),
        )

        # tasks should default to empty dict
        assert singletons.tasks == {}
        assert isinstance(singletons.tasks, dict)

    def test_singletons_creation_with_tasks(self) -> None:
        """Test creating Singletons with tasks parameter."""
        test_tasks = {"test_task": lambda: "result"}

        singletons = Singletons(
            logger=SimpleInMemoryLogger(),
            configuration=Mock(),
            state_storage=Mock(),
            task_queue=None,
            cache=Mock(),
            data_storage=Mock(),
            tasks=test_tasks,
        )

        assert singletons.tasks == test_tasks
        assert singletons.tasks["test_task"]() == "result"

    def test_singletons_creation_with_none_tasks(self) -> None:
        """Test creating Singletons with tasks=None."""
        singletons = Singletons(
            logger=SimpleInMemoryLogger(),
            configuration=Mock(),
            state_storage=Mock(),
            task_queue=None,
            cache=Mock(),
            data_storage=Mock(),
            tasks=None,
        )

        # Should default to empty dict
        assert singletons.tasks == {}


class TestTwoPhaseInitialization:
    """Test the two-phase initialization pattern."""

    def test_synchronous_execution_mode(self) -> None:
        """Test two-phase initialization with synchronous execution (no Huey)."""
        # Phase 1: Create singletons without tasks
        initial_singletons = Singletons(
            logger=SimpleInMemoryLogger(),
            configuration=Mock(),
            state_storage=Mock(),
            task_queue=None,  # No Huey for sync execution
            cache=Mock(),
            data_storage=Mock(),
        )

        # Phase 2: Setup tasks and create final singletons
        tasks = setup_tasks(None, initial_singletons)
        final_singletons = Singletons(
            logger=initial_singletons.logger,
            configuration=initial_singletons.configuration,
            state_storage=initial_singletons.state_storage,
            task_queue=initial_singletons.task_queue,
            cache=initial_singletons.cache,
            data_storage=initial_singletons.data_storage,
            tasks=tasks,
        )

        # Verify synchronous mode setup
        assert final_singletons.task_queue is None
        assert final_singletons.tasks == {}

    def test_asynchronous_execution_mode(self) -> None:
        """Test two-phase initialization with asynchronous execution (with Huey)."""
        huey = MemoryHuey(immediate=True)

        # Phase 1: Create singletons without tasks
        initial_singletons = Singletons(
            logger=SimpleInMemoryLogger(),
            configuration=Mock(),
            state_storage=Mock(),
            task_queue=huey,
            cache=Mock(),
            data_storage=Mock(),
        )

        # Phase 2: Setup tasks and create final singletons
        tasks = setup_tasks(huey, initial_singletons)
        final_singletons = Singletons(
            logger=initial_singletons.logger,
            configuration=initial_singletons.configuration,
            state_storage=initial_singletons.state_storage,
            task_queue=initial_singletons.task_queue,
            cache=initial_singletons.cache,
            data_storage=initial_singletons.data_storage,
            tasks=tasks,
        )

        # Verify asynchronous mode setup
        assert final_singletons.task_queue is huey
        assert len(final_singletons.tasks) == 4
        assert "fetch_content" in final_singletons.tasks
        assert "extract_content" in final_singletons.tasks
        assert "store_content" in final_singletons.tasks
        assert "cleanup_cache" in final_singletons.tasks

    def test_task_registry_consistency(self) -> None:
        """Test task registry consistency across different Huey configurations."""
        huey_configs = [
            MemoryHuey(immediate=True),
            MemoryHuey(immediate=False),
            None,  # Synchronous execution
        ]

        singletons = Singletons(
            logger=SimpleInMemoryLogger(),
            configuration=Mock(),
            state_storage=Mock(),
            task_queue=None,  # Will be updated per test
            cache=Mock(),
            data_storage=Mock(),
        )

        for huey in huey_configs:
            tasks = setup_tasks(huey, singletons)

            if huey is None:
                # Synchronous execution should return empty dict
                assert tasks == {}
            else:
                # Asynchronous execution should return consistent task registry
                expected_tasks = {
                    "fetch_content",
                    "extract_content",
                    "store_content",
                    "cleanup_cache",
                }
                assert set(tasks.keys()) == expected_tasks


class TestTaskRegistryIntegration:
    """Test integration between task registry and singletons."""

    def test_tasks_have_access_to_singletons(self) -> None:
        """Test that tasks can access and use singletons correctly."""
        logger = SimpleInMemoryLogger()
        huey = MemoryHuey(immediate=True)

        singletons = Singletons(
            logger=logger,
            configuration=Mock(),
            state_storage=Mock(),
            task_queue=huey,
            cache=Mock(),
            data_storage=Mock(),
        )

        tasks = setup_tasks(huey, singletons)

        # Execute all tasks and verify they can access singletons
        tasks["fetch_content"]("http://test.com")
        tasks["extract_content"]("test content", {})
        tasks["store_content"]({}, {})
        tasks["cleanup_cache"]([])

        # All tasks should have logged messages
        logs = logger.get_logs()
        assert len(logs) == 4

        # Verify log messages from each task
        log_messages = [log[2] for log in logs]
        assert "Fetch task scheduled" in log_messages
        assert "Extract task scheduled" in log_messages
        assert "Store task scheduled for processed content" in log_messages
        assert "Cache cleanup task scheduled" in log_messages

    def test_task_registry_storage_in_singletons(self) -> None:
        """Test that task registry is properly stored in singletons."""
        huey = MemoryHuey(immediate=True)

        # Simulate the two-phase initialization as done in startup
        initial_singletons = Singletons(
            logger=SimpleInMemoryLogger(),
            configuration=Mock(),
            state_storage=Mock(),
            task_queue=huey,
            cache=Mock(),
            data_storage=Mock(),
        )

        # Setup tasks
        tasks = setup_tasks(huey, initial_singletons)

        # Create final singletons with tasks
        final_singletons = Singletons(
            logger=initial_singletons.logger,
            configuration=initial_singletons.configuration,
            state_storage=initial_singletons.state_storage,
            task_queue=initial_singletons.task_queue,
            cache=initial_singletons.cache,
            data_storage=initial_singletons.data_storage,
            tasks=tasks,
        )

        # Verify task registry is accessible via singletons
        assert final_singletons.tasks is tasks
        assert len(final_singletons.tasks) == 4

        # Verify tasks can be called via singletons
        result_obj = final_singletons.tasks["fetch_content"]("http://example.com")
        result = result_obj()  # Get actual result when immediate=True
        assert result["status"] == "success"
