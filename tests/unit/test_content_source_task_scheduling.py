# ABOUTME: Unit tests for ContentSource task scheduling functionality
# ABOUTME: Tests ContentSourceHost with task registry integration and scheduling

from __future__ import annotations

from dataclasses import asdict
from datetime import timedelta
from unittest.mock import MagicMock

from paise2.models import Metadata
from paise2.plugins.core.hosts import ContentSourceHost


class TestContentSourceTaskScheduling:
    """Test ContentSource task scheduling with task registry integration."""

    def test_content_source_host_has_task_access(self) -> None:
        """Test that ContentSourceHost can access singletons and task registry."""
        # Given
        mock_logger = MagicMock()
        mock_config = MagicMock()
        mock_state_storage = MagicMock()
        mock_cache = MagicMock()
        mock_singletons = MagicMock()
        mock_singletons.tasks = {"fetch_content": MagicMock()}

        # When
        host = ContentSourceHost(
            logger=mock_logger,
            configuration=mock_config,
            state_storage=mock_state_storage,
            plugin_module_name="test.plugin",
            cache=mock_cache,
            singletons=mock_singletons,
        )

        # Then
        assert hasattr(host, "_singletons")
        assert host._singletons == mock_singletons  # noqa: SLF001

    def test_schedule_fetch_with_async_task_queue(self) -> None:
        """Test schedule_fetch with async task queue (Huey) integration."""
        # Given
        mock_logger = MagicMock()
        mock_config = MagicMock()
        mock_state_storage = MagicMock()
        mock_cache = MagicMock()
        mock_singletons = MagicMock()

        # Mock fetch task callable
        mock_fetch_task = MagicMock()
        mock_fetch_task.return_value = MagicMock(id="task_123")
        mock_singletons.tasks = {"fetch_content": mock_fetch_task}
        mock_singletons.task_queue = MagicMock()  # Not None = async mode

        host = ContentSourceHost(
            logger=mock_logger,
            configuration=mock_config,
            state_storage=mock_state_storage,
            plugin_module_name="test.plugin",
            cache=mock_cache,
            singletons=mock_singletons,
        )

        metadata = Metadata(source_url="test://example.txt")

        # When
        result = host.schedule_fetch("test://example.txt", metadata)

        # Then
        mock_fetch_task.assert_called_once_with("test://example.txt", asdict(metadata))
        assert result == "task_123"
        mock_logger.info.assert_called_with(
            "Scheduled fetch task for %s", "test://example.txt"
        )

    def test_schedule_fetch_with_sync_task_queue(self) -> None:
        """Test schedule_fetch with synchronous task queue (None) integration."""
        # Given
        mock_logger = MagicMock()
        mock_config = MagicMock()
        mock_state_storage = MagicMock()
        mock_cache = MagicMock()
        mock_singletons = MagicMock()

        # Mock tasks but task_queue is None (sync mode)
        mock_singletons.tasks = {"fetch_content": MagicMock()}
        mock_singletons.task_queue = None  # Sync mode

        host = ContentSourceHost(
            logger=mock_logger,
            configuration=mock_config,
            state_storage=mock_state_storage,
            plugin_module_name="test.plugin",
            cache=mock_cache,
            singletons=mock_singletons,
        )

        metadata = Metadata(source_url="test://example.txt")

        # When
        result = host.schedule_fetch("test://example.txt", metadata)

        # Then
        assert result is None
        mock_logger.info.assert_called_with(
            "Synchronous execution: would fetch %s", "test://example.txt"
        )

    def test_schedule_fetch_without_metadata(self) -> None:
        """Test schedule_fetch works without metadata parameter."""
        # Given
        mock_logger = MagicMock()
        mock_config = MagicMock()
        mock_state_storage = MagicMock()
        mock_cache = MagicMock()
        mock_singletons = MagicMock()

        mock_fetch_task = MagicMock()
        mock_fetch_task.return_value = MagicMock(id="task_456")
        mock_singletons.tasks = {"fetch_content": mock_fetch_task}
        mock_singletons.task_queue = MagicMock()  # Async mode

        host = ContentSourceHost(
            logger=mock_logger,
            configuration=mock_config,
            state_storage=mock_state_storage,
            plugin_module_name="test.plugin",
            cache=mock_cache,
            singletons=mock_singletons,
        )

        # When
        result = host.schedule_fetch("test://example.txt")

        # Then
        mock_fetch_task.assert_called_once_with("test://example.txt", None)
        assert result == "task_456"

    def test_schedule_next_run_with_async_task_queue(self) -> None:
        """Test schedule_next_run with async task queue integration."""
        # Given
        mock_logger = MagicMock()
        mock_config = MagicMock()
        mock_state_storage = MagicMock()
        mock_cache = MagicMock()
        mock_singletons = MagicMock()

        # Mock task queue with schedule method
        mock_task_queue = MagicMock()
        mock_singletons.task_queue = mock_task_queue
        mock_singletons.tasks = {}

        host = ContentSourceHost(
            logger=mock_logger,
            configuration=mock_config,
            state_storage=mock_state_storage,
            plugin_module_name="test.plugin",
            cache=mock_cache,
            singletons=mock_singletons,
        )

        time_interval = timedelta(hours=1)

        # When
        host.schedule_next_run(time_interval)

        # Then
        mock_logger.info.assert_called_with(
            "Scheduled next content source run in %s", time_interval
        )

    def test_schedule_next_run_with_sync_task_queue(self) -> None:
        """Test schedule_next_run with synchronous task queue (None)."""
        # Given
        mock_logger = MagicMock()
        mock_config = MagicMock()
        mock_state_storage = MagicMock()
        mock_cache = MagicMock()
        mock_singletons = MagicMock()

        mock_singletons.task_queue = None  # Sync mode
        mock_singletons.tasks = {}

        host = ContentSourceHost(
            logger=mock_logger,
            configuration=mock_config,
            state_storage=mock_state_storage,
            plugin_module_name="test.plugin",
            cache=mock_cache,
            singletons=mock_singletons,
        )

        time_interval = timedelta(minutes=30)

        # When
        host.schedule_next_run(time_interval)

        # Then
        mock_logger.info.assert_called_with(
            "Synchronous execution: would schedule next run in %s", time_interval
        )

    def test_schedule_fetch_no_task_available(self) -> None:
        """Test schedule_fetch when no fetch_content task is available."""
        # Given
        mock_logger = MagicMock()
        mock_config = MagicMock()
        mock_state_storage = MagicMock()
        mock_cache = MagicMock()
        mock_singletons = MagicMock()

        mock_singletons.tasks = {}  # No fetch_content task
        mock_singletons.task_queue = MagicMock()  # Async mode

        host = ContentSourceHost(
            logger=mock_logger,
            configuration=mock_config,
            state_storage=mock_state_storage,
            plugin_module_name="test.plugin",
            cache=mock_cache,
            singletons=mock_singletons,
        )

        # When
        result = host.schedule_fetch("test://example.txt")

        # Then
        assert result is None
        mock_logger.warning.assert_called_with(
            "No fetch_content task available in task registry"
        )


class TestContentSourceRegistration:
    """Test ContentSource plugin registration system."""

    def test_plugin_manager_exists(self) -> None:
        """Test that PluginManager can be imported and created."""
        from paise2.plugins.core.registry import PluginManager

        plugin_manager = PluginManager()

        # Check that plugin manager was created successfully
        assert plugin_manager is not None
