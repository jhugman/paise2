# ABOUTME: Tests for worker context initialization and management
# ABOUTME: Validates worker context setup, thread isolation, error handling

from __future__ import annotations

import os
import threading
from unittest.mock import Mock, patch

import pytest

from paise2.workers.context import (
    ThreadContextManager,
    WorkerContext,
    cleanup_worker_context,
    get_worker_context,
    initialize_worker_context,
)


class TestWorkerContext:
    """Test the WorkerContext class."""

    def test_worker_context_creation(self) -> None:
        """Test that WorkerContext can be created with singletons."""
        # Create mock singletons
        mock_singletons = Mock()

        # Create worker context
        context = WorkerContext(mock_singletons)

        assert context.singletons is mock_singletons
        assert context.worker_id == threading.current_thread().ident

    def test_worker_context_stores_thread_id(self) -> None:
        """Test that WorkerContext stores the correct thread ID."""
        mock_singletons = Mock()

        # Create context in different thread and verify thread ID
        results = []

        def create_context() -> None:
            context = WorkerContext(mock_singletons)
            results.append((context.worker_id, threading.current_thread().ident))

        thread = threading.Thread(target=create_context)
        thread.start()
        thread.join()

        context_thread_id, actual_thread_id = results[0]
        assert context_thread_id == actual_thread_id


class TestThreadContextManager:
    """Test the ThreadContextManager class."""

    def test_thread_context_manager_creation(self) -> None:
        """Test that ThreadContextManager can be created."""
        manager = ThreadContextManager()
        assert manager is not None
        assert hasattr(manager, "_local")

    def test_set_and_get_context(self) -> None:
        """Test setting and getting context in the same thread."""
        manager = ThreadContextManager()
        mock_singletons = Mock()
        context = WorkerContext(mock_singletons)

        # Set context
        manager.set_context(context)

        # Get context
        retrieved_context = manager.get_context()
        assert retrieved_context is context

    def test_get_context_returns_none_when_not_set(self) -> None:
        """Test that get_context returns None when no context is set."""
        manager = ThreadContextManager()

        context = manager.get_context()
        assert context is None

    def test_clear_context(self) -> None:
        """Test clearing the context."""
        manager = ThreadContextManager()
        mock_singletons = Mock()
        context = WorkerContext(mock_singletons)

        # Set context
        manager.set_context(context)
        assert manager.get_context() is context

        # Clear context
        manager.clear_context()
        assert manager.get_context() is None

    def test_context_isolation_between_threads(self) -> None:
        """Test that contexts are isolated between different threads."""
        manager = ThreadContextManager()
        mock_singletons_1 = Mock()
        mock_singletons_2 = Mock()
        context_1 = WorkerContext(mock_singletons_1)
        context_2 = WorkerContext(mock_singletons_2)

        results = []

        def thread_1_func() -> None:
            manager.set_context(context_1)
            # Give thread 2 time to set its context
            threading.Event().wait(0.1)
            retrieved = manager.get_context()
            results.append(("thread1", retrieved))

        def thread_2_func() -> None:
            manager.set_context(context_2)
            retrieved = manager.get_context()
            results.append(("thread2", retrieved))

        thread_1 = threading.Thread(target=thread_1_func)
        thread_2 = threading.Thread(target=thread_2_func)

        thread_1.start()
        thread_2.start()

        thread_1.join()
        thread_2.join()

        # Each thread should have its own context
        assert len(results) == 2

        thread_1_result = next(r for r in results if r[0] == "thread1")
        thread_2_result = next(r for r in results if r[0] == "thread2")

        assert thread_1_result[1] is context_1
        assert thread_2_result[1] is context_2


class TestWorkerContextInitialization:
    """Test worker context initialization functions."""

    @patch("paise2.main.Application")
    @patch.dict(os.environ, {"PAISE2_PROFILE": "test"})
    def test_initialize_worker_context_success(
        self, mock_application_class: Mock
    ) -> None:
        """Test successful worker context initialization."""
        # Setup mocks
        mock_app = Mock()
        mock_singletons = Mock()
        mock_logger = Mock()
        mock_singletons.logger = mock_logger

        mock_app.get_singletons.return_value = mock_singletons
        mock_application_class.return_value = mock_app

        # Initialize worker context
        initialize_worker_context()

        # Verify Application was created with correct profile
        mock_application_class.assert_called_once_with(profile="test")

        # Verify app was started
        mock_app.start.assert_called_once()

        # Verify singletons were retrieved
        mock_app.get_singletons.assert_called_once()

        # Verify logger was called
        mock_logger.info.assert_called_once()

        # Verify context was set
        context = get_worker_context()
        assert context.singletons is mock_singletons

    @patch("paise2.main.Application")
    @patch.dict(os.environ, {}, clear=True)  # Clear PAISE2_PROFILE
    def test_initialize_worker_context_default_profile(
        self, mock_application_class: Mock
    ) -> None:
        """Test worker context initialization with default profile."""
        # Setup mocks
        mock_app = Mock()
        mock_singletons = Mock()
        mock_singletons.logger = Mock()

        mock_app.get_singletons.return_value = mock_singletons
        mock_application_class.return_value = mock_app

        # Initialize worker context
        initialize_worker_context()

        # Verify Application was created with development profile
        mock_application_class.assert_called_once_with(profile="development")

    @patch("paise2.main.Application")
    def test_initialize_worker_context_application_failure(
        self, mock_application_class: Mock
    ) -> None:
        """Test worker context initialization when Application creation fails."""
        # Setup mock to raise exception
        mock_application_class.side_effect = Exception("Application creation failed")

        # Should raise RuntimeError
        with pytest.raises(RuntimeError, match="Worker context initialization failed"):
            initialize_worker_context()

    @patch("paise2.main.Application")
    def test_initialize_worker_context_startup_failure(
        self, mock_application_class: Mock
    ) -> None:
        """Test worker context initialization when app.start() fails."""
        # Setup mocks
        mock_app = Mock()
        mock_app.start.side_effect = Exception("Startup failed")
        mock_application_class.return_value = mock_app

        # Should raise RuntimeError
        with pytest.raises(RuntimeError, match="Worker context initialization failed"):
            initialize_worker_context()

    @patch("paise2.main.Application")
    def test_initialize_worker_context_profile_propagation(
        self, mock_application_class: Mock
    ) -> None:
        """Test that profile is correctly propagated from environment."""
        # Setup mocks
        mock_app = Mock()
        mock_singletons = Mock()
        mock_singletons.logger = Mock()

        mock_app.get_singletons.return_value = mock_singletons
        mock_application_class.return_value = mock_app

        profiles = ["test", "development", "production"]

        for profile in profiles:
            with patch.dict(os.environ, {"PAISE2_PROFILE": profile}):
                # Reset mock for each iteration
                mock_application_class.reset_mock()

                # Initialize worker context
                initialize_worker_context()

                # Verify correct profile was used
                mock_application_class.assert_called_once_with(profile=profile)


class TestWorkerContextCleanup:
    """Test worker context cleanup functions."""

    def test_cleanup_worker_context_with_context(self) -> None:
        """Test cleanup when worker context exists."""
        # Setup context
        mock_singletons = Mock()
        mock_logger = Mock()
        mock_singletons.logger = mock_logger

        context = WorkerContext(mock_singletons)

        # Use the global thread context manager
        from paise2.workers.context import _thread_context_manager

        _thread_context_manager.set_context(context)

        # Cleanup
        cleanup_worker_context()

        # Verify logger was called
        mock_logger.info.assert_called_once()

        # Verify context was cleared
        assert _thread_context_manager.get_context() is None

    def test_cleanup_worker_context_without_context(self) -> None:
        """Test cleanup when no worker context exists."""
        # Ensure no context is set
        from paise2.workers.context import _thread_context_manager

        _thread_context_manager.clear_context()

        # Should not raise an exception
        cleanup_worker_context()

        # Should still have no context
        assert _thread_context_manager.get_context() is None

    def test_cleanup_worker_context_exception_handling(self) -> None:
        """Test that cleanup handles exceptions gracefully."""
        # Setup context with logger that raises exception
        mock_singletons = Mock()
        mock_logger = Mock()
        mock_logger.info.side_effect = Exception("Logger failed")
        mock_singletons.logger = mock_logger

        context = WorkerContext(mock_singletons)

        from paise2.workers.context import _thread_context_manager

        _thread_context_manager.set_context(context)

        # Should not raise an exception
        cleanup_worker_context()


class TestWorkerContextAccess:
    """Test worker context access functions."""

    def test_get_worker_context_success(self) -> None:
        """Test getting worker context when it exists."""
        # Setup context
        mock_singletons = Mock()
        context = WorkerContext(mock_singletons)

        from paise2.workers.context import _thread_context_manager

        _thread_context_manager.set_context(context)

        # Get context
        retrieved_context = get_worker_context()
        assert retrieved_context is context

    def test_get_worker_context_no_context(self) -> None:
        """Test getting worker context when none exists."""
        # Clear any existing context
        from paise2.workers.context import _thread_context_manager

        _thread_context_manager.clear_context()

        # Should raise RuntimeError
        with pytest.raises(RuntimeError, match="No worker context available"):
            get_worker_context()

    def test_get_worker_singletons(self) -> None:
        """Test getting singletons from worker context."""
        # Setup context
        mock_singletons = Mock()
        context = WorkerContext(mock_singletons)

        from paise2.workers.context import _thread_context_manager

        _thread_context_manager.set_context(context)

        # Get singletons using convenience function
        from paise2.workers.context import get_worker_singletons

        retrieved_singletons = get_worker_singletons()
        assert retrieved_singletons is mock_singletons

    def test_convenience_access_functions(self) -> None:
        """Test convenience functions for accessing specific singletons."""
        # Setup mock singletons with all required attributes
        mock_singletons = Mock()
        mock_logger = Mock()
        mock_config = Mock()
        mock_data_storage = Mock()
        mock_cache = Mock()
        mock_state_storage = Mock()

        mock_singletons.logger = mock_logger
        mock_singletons.configuration = mock_config
        mock_singletons.data_storage = mock_data_storage
        mock_singletons.cache = mock_cache
        mock_singletons.state_storage = mock_state_storage

        context = WorkerContext(mock_singletons)

        from paise2.workers.context import (
            _thread_context_manager,
            get_worker_cache,
            get_worker_configuration,
            get_worker_data_storage,
            get_worker_logger,
            get_worker_state_storage,
        )

        _thread_context_manager.set_context(context)

        # Test all convenience functions
        assert get_worker_logger() is mock_logger
        assert get_worker_configuration() is mock_config
        assert get_worker_data_storage() is mock_data_storage
        assert get_worker_cache() is mock_cache
        assert get_worker_state_storage() is mock_state_storage


class TestWorkerContextIntegration:
    """Test worker context integration scenarios."""

    @patch("paise2.main.Application")
    def test_multiple_worker_initialization(self, mock_application_class: Mock) -> None:
        """Test that multiple workers can initialize contexts independently."""

        # Setup mocks
        def create_mock_app(*args: object, **kwargs: object) -> Mock:  # noqa: ARG001
            mock_app = Mock()
            mock_singletons = Mock()
            mock_singletons.logger = Mock()
            mock_app.get_singletons.return_value = mock_singletons
            return mock_app

        mock_application_class.side_effect = create_mock_app

        results = []

        def worker_func(worker_id: int) -> None:
            # Each worker initializes its own context
            initialize_worker_context()
            context = get_worker_context()
            results.append((worker_id, context.worker_id, context.singletons))

        # Start multiple worker threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=worker_func, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify each worker has its own context
        assert len(results) == 3

        worker_ids = [r[1] for r in results]
        singletons = [r[2] for r in results]

        # All worker IDs should be different
        assert len(set(worker_ids)) == 3

        # All singletons should be different instances
        assert len({id(s) for s in singletons}) == 3

    def test_worker_context_thread_safety(self) -> None:
        """Test thread safety of worker context operations."""
        from paise2.workers.context import _thread_context_manager

        results: list[tuple[str, int] | tuple[str, int, str]] = []

        def worker_operations(worker_id: int) -> None:
            try:
                # Create context for this worker
                mock_singletons = Mock()
                # Store worker_id in a way we can access it
                mock_singletons.test_worker_id = worker_id
                context = WorkerContext(mock_singletons)

                # Set context
                _thread_context_manager.set_context(context)

                # Perform multiple context operations
                for _ in range(10):
                    retrieved = _thread_context_manager.get_context()
                    assert retrieved is not None
                    assert retrieved is context
                    # Just verify we got the same context back
                    assert retrieved.singletons is mock_singletons

                # Clear context
                _thread_context_manager.clear_context()
                assert _thread_context_manager.get_context() is None

                results.append(("success", worker_id))

            except Exception as e:
                results.append(("error", worker_id, str(e)))

        # Start multiple worker threads performing operations concurrently
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker_operations, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify all operations succeeded
        assert len(results) == 5
        for result in results:
            assert result[0] == "success"
