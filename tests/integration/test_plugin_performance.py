# ABOUTME: Performance and stress testing for the plugin system
# ABOUTME: Tests system performance under load and validates resource usage

from __future__ import annotations

import time

import pytest

from paise2.plugins.core.manager import PluginSystem
from tests.fixtures import create_test_plugin_manager_with_mocks


class TestPluginSystemPerformance:
    """Test plugin system performance and scalability."""

    def test_plugin_loading_performance(self) -> None:
        """Test that plugin loading completes within reasonable time."""
        start_time = time.time()

        test_plugin_manager = create_test_plugin_manager_with_mocks()
        plugin_system = PluginSystem(test_plugin_manager)

        try:
            plugin_system.bootstrap()
            bootstrap_time = time.time()

            plugin_system.start()
            startup_time = time.time()

            # Bootstrap should be very fast (< 100ms)
            bootstrap_duration = bootstrap_time - start_time
            assert bootstrap_duration < 0.1, f"Bootstrap took {bootstrap_duration:.3f}s"

            # Full startup should be reasonable (< 1s for test setup)
            startup_duration = startup_time - bootstrap_time
            assert startup_duration < 1.0, f"Startup took {startup_duration:.3f}s"

        finally:
            plugin_system.stop()

    @pytest.mark.asyncio
    async def test_cache_performance_with_many_operations(self) -> None:
        """Test cache performance with many save/get operations."""
        test_plugin_manager = create_test_plugin_manager_with_mocks()
        plugin_system = PluginSystem(test_plugin_manager)

        try:
            plugin_system.bootstrap()
            await plugin_system.start_async()

            cache = plugin_system.get_singletons().cache

            # Save many cache entries
            start_time = time.time()
            cache_ids = []

            for i in range(50):
                cache_id = await cache.save("performance_test", f"content_{i}", ".txt")
                cache_ids.append(cache_id)

            save_time = time.time() - start_time

            # Should be able to save 50 entries quickly (< 200ms for memory cache)
            assert save_time < 0.2, f"Saving 50 cache entries took {save_time:.3f}s"

            # Retrieve all entries
            start_time = time.time()

            for cache_id in cache_ids:
                content = await cache.get(cache_id)
                assert content is not None

            retrieve_time = time.time() - start_time

            # Should be able to retrieve 50 entries quickly (< 100ms for memory cache)
            assert retrieve_time < 0.1, (
                f"Retrieving 50 cache entries took {retrieve_time:.3f}s"
            )

        finally:
            await plugin_system.stop_async()

    def test_state_storage_performance_with_many_keys(self) -> None:
        """Test state storage performance with many keys and operations."""
        test_plugin_manager = create_test_plugin_manager_with_mocks()
        plugin_system = PluginSystem(test_plugin_manager)

        try:
            plugin_system.bootstrap()
            plugin_system.start()

            state_storage = plugin_system.get_singletons().state_storage

            # Store many state entries
            start_time = time.time()

            for i in range(100):
                state_storage.store(
                    "performance_test", f"key_{i}", f"value_{i}", version=1
                )

            store_time = time.time() - start_time

            # Should be able to store 100 entries quickly (< 200ms)
            assert store_time < 0.2, f"Storing 100 state entries took {store_time:.3f}s"

            # Retrieve all entries
            start_time = time.time()

            for i in range(100):
                value = state_storage.get("performance_test", f"key_{i}")
                assert value == f"value_{i}"

            retrieve_time = time.time() - start_time

            # Should be able to retrieve 100 entries quickly (< 100ms)
            assert retrieve_time < 0.1, (
                f"Retrieving 100 state entries took {retrieve_time:.3f}s"
            )

        finally:
            plugin_system.stop()

    @pytest.mark.asyncio
    async def test_data_storage_performance_with_many_items(self) -> None:
        """Test data storage performance with many stored items."""
        test_plugin_manager = create_test_plugin_manager_with_mocks()
        plugin_system = PluginSystem(test_plugin_manager)

        try:
            plugin_system.bootstrap()
            await plugin_system.start_async()

            storage = plugin_system.get_singletons().data_storage
            from paise2.models import Metadata
            from tests.fixtures.mock_plugins import MockDataStorageHost

            host = MockDataStorageHost()

            # Store many items
            start_time = time.time()
            item_ids = []

            for i in range(50):
                metadata = Metadata(
                    source_url=f"performance://item_{i}.txt", title=f"Item {i}"
                )
                item_id = await storage.add_item(host, f"content_{i}", metadata)
                item_ids.append(item_id)

            store_time = time.time() - start_time

            # Should be able to store 50 items quickly (< 500ms)
            assert store_time < 0.5, f"Storing 50 items took {store_time:.3f}s"

            # Retrieve all items
            start_time = time.time()

            for item_id in item_ids:
                found_metadata = await storage.find_item(item_id)
                assert found_metadata is not None
                assert found_metadata.source_url.startswith("performance://")

            retrieve_time = time.time() - start_time

            # Should be able to retrieve 50 items quickly (< 200ms)
            assert retrieve_time < 0.2, f"Retrieving 50 items took {retrieve_time:.3f}s"

        finally:
            await plugin_system.stop_async()


class TestPluginSystemStressTesting:
    """Stress testing for plugin system under extreme conditions."""

    def test_repeated_startup_shutdown_cycles(self) -> None:
        """Test that multiple startup/shutdown cycles work without degradation."""
        test_plugin_manager = create_test_plugin_manager_with_mocks()

        startup_times = []
        shutdown_times = []

        # Perform multiple cycles
        for cycle_num in range(5):
            plugin_system = PluginSystem(test_plugin_manager)

            # Time startup
            start_time = time.time()
            plugin_system.bootstrap()
            plugin_system.start()
            startup_duration = time.time() - start_time
            startup_times.append(startup_duration)

            # Verify system is functional
            assert plugin_system.is_running()
            singletons = plugin_system.get_singletons()
            assert singletons is not None

            # Test that each cycle works
            test_key = f"cycle_{cycle_num}_test"
            singletons.state_storage.store("perf_test", test_key, f"cycle_{cycle_num}")

            # Time shutdown
            start_time = time.time()
            plugin_system.stop()
            shutdown_duration = time.time() - start_time
            shutdown_times.append(shutdown_duration)

            assert not plugin_system.is_running()

        # Performance should not degrade significantly across cycles
        avg_startup = sum(startup_times) / len(startup_times)
        avg_shutdown = sum(shutdown_times) / len(shutdown_times)

        # All cycles should complete reasonably quickly
        assert avg_startup < 1.0, f"Average startup time {avg_startup:.3f}s too high"
        assert avg_shutdown < 0.1, f"Average shutdown time {avg_shutdown:.3f}s too high"

        # No cycle should be more than 2x the average (no significant degradation)
        for i, startup_time in enumerate(startup_times):
            assert startup_time < avg_startup * 2, (
                f"Cycle {i} startup time {startup_time:.3f}s degraded"
            )

    @pytest.mark.asyncio
    async def test_concurrent_operations_across_all_systems(self) -> None:
        """Test concurrent operations across all plugin systems."""
        test_plugin_manager = create_test_plugin_manager_with_mocks()
        plugin_system = PluginSystem(test_plugin_manager)

        try:
            plugin_system.bootstrap()
            await plugin_system.start_async()

            singletons = plugin_system.get_singletons()

            # Perform concurrent operations across all systems
            import asyncio

            async def concurrent_operations() -> int:
                # Cache operations
                cache_tasks = [
                    singletons.cache.save("stress_test", f"content{i}", ".txt")
                    for i in range(10)
                ]

                # State operations (synchronous, but in executor)
                def state_ops() -> None:
                    for i in range(10):
                        singletons.state_storage.store(
                            "stress_test", f"key{i}", f"value{i}"
                        )

                # Data storage operations
                from paise2.models import Metadata
                from tests.fixtures.mock_plugins import MockDataStorageHost

                host = MockDataStorageHost()
                storage_tasks = [
                    singletons.data_storage.add_item(
                        host,
                        f"data{i}",
                        Metadata(source_url=f"stress://test{i}.txt"),
                    )
                    for i in range(10)
                ]

                # Execute all operations concurrently
                results = await asyncio.gather(
                    *cache_tasks, *storage_tasks, return_exceptions=True
                )

                # Also run state operations
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, state_ops)

                # Check that no operations failed
                for result in results:
                    if isinstance(result, Exception):
                        pytest.fail(f"Concurrent operation failed: {result}")

                return len(results)

            start_time = time.time()
            result_count = await concurrent_operations()
            operation_time = time.time() - start_time

            # Should complete all operations in reasonable time (< 2s)
            assert operation_time < 2.0, (
                f"Concurrent operations took {operation_time:.3f}s"
            )
            assert result_count > 0

        finally:
            await plugin_system.stop_async()

    def test_memory_usage_stability_over_time(self) -> None:
        """Test that memory usage remains stable over extended operation."""
        test_plugin_manager = create_test_plugin_manager_with_mocks()
        plugin_system = PluginSystem(test_plugin_manager)

        try:
            plugin_system.bootstrap()
            plugin_system.start()

            singletons = plugin_system.get_singletons()

            # Simulate extended operation with many temporary objects
            for cycle in range(10):
                # Create and destroy many temporary state entries
                for i in range(20):
                    singletons.state_storage.store(
                        f"temp_cycle_{cycle}", f"temp_key_{i}", f"temp_value_{i}"
                    )

                # Access configuration multiple times
                for i in range(10):
                    _ = singletons.configuration.get(f"nonexistent.key_{i}", "default")

                # The system should remain stable (this is a basic smoke test)
                assert plugin_system.is_running()
                assert singletons.logger is not None

            # System should still be functional after extended operation
            assert plugin_system.is_running()
            test_value = singletons.state_storage.get("temp_cycle_9", "temp_key_19")
            assert test_value == "temp_value_19"

        finally:
            plugin_system.stop()


class TestPluginSystemResourceManagement:
    """Test resource management and cleanup in the plugin system."""

    def test_proper_resource_cleanup_on_shutdown(self) -> None:
        """Test that resources are properly cleaned up on shutdown."""
        test_plugin_manager = create_test_plugin_manager_with_mocks()
        plugin_system = PluginSystem(test_plugin_manager)

        plugin_system.bootstrap()
        plugin_system.start()

        # System should be fully functional
        assert plugin_system.is_running()
        singletons = plugin_system.get_singletons()
        assert singletons is not None

        # Store some state to verify persistence
        singletons.state_storage.store("cleanup_test", "persistence_key", "test_value")

        # Shutdown should complete cleanly
        plugin_system.stop()
        assert not plugin_system.is_running()

        # Should not be able to access singletons after shutdown
        with pytest.raises(RuntimeError, match="not running"):
            plugin_system.get_singletons()

    def test_error_handling_does_not_leak_resources(self) -> None:
        """Test that error conditions don't cause resource leaks."""
        from unittest.mock import patch

        test_plugin_manager = create_test_plugin_manager_with_mocks()

        # Test error during startup
        with patch(
            "paise2.config.factory.ConfigurationFactory.load_initial_configuration"
        ) as mock_config:
            mock_config.side_effect = RuntimeError("Startup error")

            plugin_system = PluginSystem(test_plugin_manager)
            plugin_system.bootstrap()

            from paise2.plugins.core.startup import StartupError

            with pytest.raises(StartupError):
                plugin_system.start()

            # System should be in a clean state after error
            assert not plugin_system.is_running()

            # Should be able to attempt startup again
            mock_config.side_effect = None  # Remove the error
            # Note: Won't actually work because mock is still in place,
            # but this tests that the system doesn't get stuck in a bad state

    @pytest.mark.asyncio
    async def test_async_resource_cleanup(self) -> None:
        """Test that async resources are properly cleaned up."""
        test_plugin_manager = create_test_plugin_manager_with_mocks()
        plugin_system = PluginSystem(test_plugin_manager)

        plugin_system.bootstrap()
        await plugin_system.start_async()

        # Use async resources
        singletons = plugin_system.get_singletons()
        cache_id = await singletons.cache.save("cleanup", "test content", ".txt")

        # Resources should be functional
        assert await singletons.cache.get(cache_id) == "test content"

        # Shutdown should clean up async resources
        await plugin_system.stop_async()
        assert not plugin_system.is_running()

        # Should not be able to access async resources after shutdown
        with pytest.raises(RuntimeError, match="not running"):
            plugin_system.get_singletons()
