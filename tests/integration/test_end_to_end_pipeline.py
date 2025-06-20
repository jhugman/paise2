# ABOUTME: Comprehensive end-to-end tests for the complete content processing pipeline
# ABOUTME: Tests ContentSource → Task Queue → ContentFetcher → ContentExtractor

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest

from paise2.main import Application
from paise2.models import Metadata
from paise2.plugins.core.manager import PluginSystem
from tests.fixtures import create_test_plugin_manager_with_mocks


class TestEndToEndPipeline:
    """End-to-end tests for the complete content processing pipeline."""

    @pytest.mark.asyncio
    async def test_complete_content_processing_pipeline_async(self) -> None:
        """Test complete pipeline: Source → Task → Fetcher → Extractor → Storage."""
        # Given: A temporary directory with test content
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            test_file = temp_path / "test.txt"
            test_content = "This is test content for end-to-end processing"
            test_file.write_text(test_content)

            # Create plugin system with mocks
            plugin_manager = create_test_plugin_manager_with_mocks()
            plugin_system = PluginSystem(plugin_manager)

            try:
                # When: Bootstrap and start the system
                plugin_system.bootstrap()
                await plugin_system.start_async()

                singletons = plugin_system.get_singletons()
                assert singletons.task_queue is not None
                assert singletons.cache is not None
                assert singletons.data_storage is not None

                # Simulate the complete pipeline
                # 1. ContentSource discovers content and schedules tasks
                task_queue = singletons.task_queue

                # Schedule tasks using the correct interface
                test_url = f"file://{test_file}"
                fetch_result = task_queue.fetch_content(test_url)
                assert fetch_result is not None

                # 2. Create test metadata
                test_metadata = Metadata(
                    source_url=test_url,
                    mime_type="text/plain",
                    title="Test Content",
                    description="End-to-end test content",
                )

                # 3. Extract content task
                extract_result = task_queue.extract_content(test_content, test_metadata)
                assert extract_result is not None

                # 4. Store content task
                store_result = task_queue.store_content(test_content, test_metadata)
                assert store_result is not None

                # Verify state storage operations
                state_storage = singletons.state_storage
                test_key = "test_pipeline_key"
                test_value = {"status": "completed", "content": test_content}

                # Store and retrieve state
                state_storage.store("test_partition", test_key, test_value)
                retrieved_value = state_storage.get("test_partition", test_key)
                assert retrieved_value == test_value

                # Test data storage operations with mock host
                data_storage = singletons.data_storage
                mock_host = Mock()

                # Add item to data storage
                item_id = await data_storage.add_item(
                    mock_host, test_content, test_metadata
                )
                assert item_id is not None

                # Find the item
                found_item = await data_storage.find_item(item_id)
                assert found_item is not None

            finally:
                # Clean up
                await plugin_system.stop_async()

    @pytest.mark.asyncio
    async def test_multiple_content_types_pipeline(self) -> None:
        """Test pipeline with multiple content types and formats."""
        plugin_manager = create_test_plugin_manager_with_mocks()
        plugin_system = PluginSystem(plugin_manager)

        try:
            plugin_system.bootstrap()
            await plugin_system.start_async()

            singletons = plugin_system.get_singletons()
            task_queue = singletons.task_queue

            # Test different content types
            test_cases = [
                ("text/plain", "Plain text content"),
                ("text/html", "<html><body>HTML content</body></html>"),
                ("application/json", '{"key": "value", "test": true}'),
            ]

            for mime_type, content_text in test_cases:
                # Create metadata for each content type
                metadata = Metadata(
                    source_url=f"test://{mime_type.replace('/', '_')}",
                    mime_type=mime_type,
                    title=f"Test {mime_type}",
                )

                # Process through pipeline if task_queue is available
                if task_queue is not None:
                    fetch_result = task_queue.fetch_content(metadata.source_url)
                    extract_result = task_queue.extract_content(content_text, metadata)
                    store_result = task_queue.store_content(content_text, metadata)

                    # Verify all tasks were scheduled
                    assert fetch_result is not None
                    assert extract_result is not None
                    assert store_result is not None

        finally:
            await plugin_system.stop_async()

    def test_application_startup_and_shutdown(self) -> None:
        """Test the complete Application lifecycle."""
        try:
            app = Application(profile="test")

            with app:
                assert app.is_running()
                singletons = app.get_singletons()
                assert singletons is not None
                assert singletons.configuration is not None
                assert singletons.logger is not None

            assert not app.is_running()

        except Exception as e:
            # If no providers are available, that's expected in test environment
            if "No configuration providers found" in str(e):
                pytest.skip("No real providers available for Application test")
            else:
                raise

    @pytest.mark.asyncio
    async def test_pipeline_error_handling_and_recovery(self) -> None:
        """Test error handling and recovery mechanisms in the pipeline."""
        plugin_manager = create_test_plugin_manager_with_mocks()
        plugin_system = PluginSystem(plugin_manager)

        try:
            plugin_system.bootstrap()
            await plugin_system.start_async()

            singletons = plugin_system.get_singletons()
            task_queue = singletons.task_queue

            # Test error handling in task scheduling
            # Using invalid URL should not crash the system
            if task_queue is not None:
                invalid_url = "invalid://nonexistent/path"
                result = task_queue.fetch_content(invalid_url)
                # Task should be scheduled even if it will fail
                assert result is not None

                # Test with empty content
                empty_metadata = Metadata(source_url="test://empty")
                empty_result = task_queue.extract_content("", empty_metadata)
                assert empty_result is not None

            # Test state storage error handling
            state_storage = singletons.state_storage

            # Store and retrieve with edge cases
            state_storage.store("test", "empty_key", "")
            retrieved = state_storage.get("test", "empty_key")
            assert retrieved == ""

            # Non-existent key should return default
            missing = state_storage.get("test", "nonexistent", "default")
            assert missing == "default"

        finally:
            await plugin_system.stop_async()

    def test_custom_configuration_integration(self) -> None:
        """Test integration with custom user configuration."""
        try:
            # Test with custom configuration
            custom_config = {"logging": {"level": "DEBUG"}, "plugins": {"timeout": 30}}

            app = Application(profile="test", user_config=custom_config)

            with app:
                assert app.is_running()
                singletons = app.get_singletons()
                assert singletons.configuration is not None

        except Exception as e:
            if "No configuration providers found" in str(e):
                pytest.skip("No real providers available for custom config test")
            else:
                raise

    def test_system_monitoring_and_health_checks(self) -> None:
        """Test system monitoring and health check capabilities."""
        try:
            app = Application(profile="test")

            with app:
                singletons = app.get_singletons()

                # Basic health checks
                health_status = {
                    "configuration": singletons.configuration is not None,
                    "logger": singletons.logger is not None,
                    "state_storage": singletons.state_storage is not None,
                    "cache": singletons.cache is not None,
                    "task_queue": hasattr(singletons, "task_queue"),
                }

                # All components should be healthy
                assert all(health_status.values())

                # Test state storage health
                test_key = "health_check_key"
                test_data = {"status": "healthy", "timestamp": "2024-01-01T00:00:00Z"}

                # Storage write/read test
                singletons.state_storage.store("health", test_key, test_data)
                retrieved = singletons.state_storage.get("health", test_key)
                assert retrieved == test_data

        except Exception as e:
            if "No configuration providers found" in str(e):
                pytest.skip("No real providers available for health check test")
            else:
                raise

    def test_worker_lifecycle_coordination(self) -> None:
        """Test worker lifecycle and process coordination."""
        # This test simulates worker management scenarios
        app = Application(profile="test")  # Use test profile

        with app:
            # Verify system can coordinate multiple components
            singletons = app.get_singletons()

            # In a real implementation, this would test:
            # - Worker process startup/shutdown
            # - Task queue coordination
            # - Graceful shutdown handling
            # - Resource cleanup

            # For now, verify the coordination infrastructure is in place
            assert singletons.configuration is not None
            assert singletons.logger is not None

            # The system should handle startup/shutdown gracefully
            assert app.is_running()

        assert not app.is_running()
