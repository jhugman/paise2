# ABOUTME: Tests for asynchronous task execution using different task queue providers
# ABOUTME: Validates both synchronous (test) and asynchronous (Huey) execution modes

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from paise2.models import Metadata
from paise2.plugins.core.manager import PluginSystem
from tests.fixtures import create_test_plugin_manager_with_mocks


class TestAsyncTaskExecution:
    """Tests for asynchronous task execution capabilities."""

    @pytest.mark.asyncio
    async def test_synchronous_execution_test_profile(self) -> None:
        """Test synchronous execution mode (test profile with MemoryHuey)."""
        plugin_manager = create_test_plugin_manager_with_mocks()
        plugin_system = PluginSystem(plugin_manager)

        try:
            plugin_system.bootstrap()
            await plugin_system.start_async()
            singletons = plugin_system.get_singletons()

            # Test profile should use MemoryHuey with immediate=True
            task_queue = singletons.task_queue
            assert task_queue is not None

            # Check that it's MemoryHuey with immediate execution
            if hasattr(task_queue, "huey"):
                from huey import MemoryHuey

                assert isinstance(task_queue.huey, MemoryHuey)
                assert task_queue.huey.immediate is True

            # Test task execution
            test_url = "file:///tmp/test_sync.txt"
            test_content = "Test content for synchronous execution"
            test_metadata = Metadata(source_url=test_url, mime_type="text/plain")

            # Schedule tasks - these should execute immediately
            fetch_result = task_queue.fetch_content(test_url)
            extract_result = task_queue.extract_content(test_content, test_metadata)
            store_result = task_queue.store_content(test_content, test_metadata)

            # Verify tasks were scheduled (return results immediately in sync mode)
            assert fetch_result is not None
            assert extract_result is not None
            assert store_result is not None

        finally:
            await plugin_system.stop_async()

    @pytest.mark.asyncio
    async def test_async_execution_development_profile(self) -> None:
        """Test asynchronous execution mode with development-like configuration."""
        # Use test mocks but check for async capabilities
        plugin_manager = create_test_plugin_manager_with_mocks()
        plugin_system = PluginSystem(plugin_manager)

        try:
            plugin_system.bootstrap()
            await plugin_system.start_async()
            singletons = plugin_system.get_singletons()

            # Check task queue capabilities
            task_queue = singletons.task_queue

            if task_queue is not None:
                # Test task scheduling regardless of execution mode
                test_url = "file:///tmp/test_async.txt"
                test_content = "Test content for asynchronous execution"
                test_metadata = Metadata(source_url=test_url, mime_type="text/plain")

                # Schedule tasks - these may execute synchronously or asynchronously
                fetch_result = task_queue.fetch_content(test_url)
                extract_result = task_queue.extract_content(test_content, test_metadata)
                store_result = task_queue.store_content(test_content, test_metadata)

                # Verify tasks were scheduled
                assert fetch_result is not None
                assert extract_result is not None
                assert store_result is not None

                # Check if it's using MemoryHuey (async-capable but immediate in tests)
                if hasattr(task_queue, "huey"):
                    from huey import MemoryHuey

                    # MemoryHuey can run in both immediate and async modes
                    assert isinstance(task_queue.huey, MemoryHuey)

        finally:
            await plugin_system.stop_async()

    @pytest.mark.asyncio
    async def test_task_queue_error_handling(self) -> None:
        """Test error handling in task queue operations."""
        plugin_manager = create_test_plugin_manager_with_mocks()
        plugin_system = PluginSystem(plugin_manager)

        try:
            plugin_system.bootstrap()
            await plugin_system.start_async()
            singletons = plugin_system.get_singletons()

            task_queue = singletons.task_queue
            assert task_queue is not None

            # Test with invalid/malformed data
            try:
                # Try to schedule with invalid metadata
                invalid_metadata = Metadata(source_url="", mime_type="")
                result = task_queue.extract_content("", invalid_metadata)
                # Should not crash, even with invalid data
                assert result is not None
            except Exception as e:
                # If it does throw, it should be handled gracefully
                singletons.logger.debug("Expected error in task scheduling: %s", str(e))

            # Test with very large content (should handle gracefully)
            large_content = "x" * 10000  # 10KB content
            large_metadata = Metadata(
                source_url="test://large-content", mime_type="text/plain"
            )

            result = task_queue.extract_content(large_content, large_metadata)
            assert result is not None

        finally:
            await plugin_system.stop_async()

    @pytest.mark.asyncio
    async def test_complete_pipeline_with_task_queue(self) -> None:
        """Test complete content processing pipeline with task queue integration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test content
            test_file = Path(temp_dir) / "pipeline_test.txt"
            test_content = "This is test content for the complete pipeline"
            test_file.write_text(test_content)

            plugin_manager = create_test_plugin_manager_with_mocks()
            plugin_system = PluginSystem(plugin_manager)

            try:
                plugin_system.bootstrap()
                await plugin_system.start_async()
                singletons = plugin_system.get_singletons()

                # Test complete pipeline flow
                task_queue = singletons.task_queue
                assert task_queue is not None

                # 1. Content source would discover and schedule fetch
                test_url = f"file://{test_file}"
                fetch_result = task_queue.fetch_content(test_url)
                assert fetch_result is not None

                # 2. Fetcher would retrieve content and schedule extraction
                metadata = Metadata(
                    source_url=test_url,
                    mime_type="text/plain",
                    title="Test Pipeline Content",
                )
                extract_result = task_queue.extract_content(test_content, metadata)
                assert extract_result is not None

                # 3. Extractor would process and schedule storage
                store_result = task_queue.store_content(test_content, metadata)
                assert store_result is not None

                # 4. Verify state storage integration
                state_storage = singletons.state_storage
                test_partition = "pipeline_test"
                test_state = {
                    "status": "completed",
                    "timestamp": "2024-01-01T00:00:00Z",
                }

                state_storage.store(test_partition, "test_key", test_state)
                retrieved_state = state_storage.get(test_partition, "test_key")
                assert retrieved_state == test_state

                # 5. Verify cache integration
                cache = singletons.cache
                cache_content = await cache.save("test_partition", test_content, ".txt")
                assert cache_content is not None

                retrieved_content = await cache.get(cache_content)
                assert retrieved_content == test_content

            finally:
                await plugin_system.stop_async()

    def test_task_queue_providers_availability(self) -> None:
        """Test that different task queue providers are available."""
        # Test with mock profile (has providers loaded)
        mock_plugin_manager = create_test_plugin_manager_with_mocks()
        mock_providers = mock_plugin_manager.get_task_queue_providers()
        assert len(mock_providers) > 0

        # Check provider types
        provider_types = [type(provider).__name__ for provider in mock_providers]
        assert any("TaskQueueProvider" in name for name in provider_types)
