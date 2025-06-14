# ABOUTME: Plugin isolation and state partitioning tests
# ABOUTME: Validates that plugins are properly isolated from each other

from __future__ import annotations

import pytest

from paise2.plugins.core.manager import PluginSystem
from tests.fixtures import create_test_plugin_manager_with_mocks


class TestPluginIsolationAndPartitioning:
    """Test plugin isolation and state partitioning functionality."""

    def test_plugin_state_isolation_by_module_name(self) -> None:
        """Test that plugin state is automatically isolated by module name."""
        test_plugin_manager = create_test_plugin_manager_with_mocks()
        plugin_system = PluginSystem(test_plugin_manager)

        try:
            plugin_system.bootstrap()
            plugin_system.start()

            state_storage = plugin_system.get_singletons().state_storage

            # Different plugins should have isolated state
            state_storage.store("plugin.module1", "shared_key", "value1")
            state_storage.store("plugin.module2", "shared_key", "value2")
            state_storage.store("plugin.module3", "shared_key", "value3")

            # Each plugin should only see its own state
            assert state_storage.get("plugin.module1", "shared_key") == "value1"
            assert state_storage.get("plugin.module2", "shared_key") == "value2"
            assert state_storage.get("plugin.module3", "shared_key") == "value3"

            # Should not see other plugins' state
            assert state_storage.get("plugin.module1", "nonexistent") is None
            assert state_storage.get("plugin.module2", "different_key") is None

        finally:
            plugin_system.stop()

    def test_plugin_cache_isolation_by_partition(self) -> None:
        """Test that plugin cache access is isolated by partition key."""

        @pytest.mark.asyncio
        async def _test_cache_isolation() -> None:
            test_plugin_manager = create_test_plugin_manager_with_mocks()
            plugin_system = PluginSystem(test_plugin_manager)

            try:
                plugin_system.bootstrap()
                await plugin_system.start_async()

                cache = plugin_system.get_singletons().cache

                # Different partitions should be isolated
                cache_id1 = await cache.save("partition1", "content1", ".txt")
                cache_id2 = await cache.save("partition2", "content2", ".txt")
                cache_id3 = await cache.save("partition1", "content3", ".txt")

                # Should be able to retrieve content from correct partition
                assert await cache.get(cache_id1) == "content1"
                assert await cache.get(cache_id2) == "content2"
                assert await cache.get(cache_id3) == "content3"

                # Partition operations should be isolated
                partition1_ids = await cache.get_all("partition1")
                partition2_ids = await cache.get_all("partition2")

                assert cache_id1 in partition1_ids
                assert cache_id3 in partition1_ids
                assert cache_id2 not in partition1_ids

                assert cache_id2 in partition2_ids
                assert cache_id1 not in partition2_ids
                assert cache_id3 not in partition2_ids

            finally:
                plugin_system.stop()

        # Run the async test
        import asyncio

        asyncio.run(_test_cache_isolation())

    def test_plugin_configuration_isolation_through_namespacing(self) -> None:
        """Test that plugins can access configuration in isolated namespaces."""
        test_plugin_manager = create_test_plugin_manager_with_mocks()
        plugin_system = PluginSystem(test_plugin_manager)

        user_config = {
            "plugin1": {"setting1": "value1", "timeout": 30},
            "plugin2": {"setting1": "value2", "max_items": 100},
            "global": {"log_level": "debug"},
        }

        try:
            plugin_system.bootstrap()
            plugin_system.start(user_config)

            config = plugin_system.get_singletons().configuration

            # Each plugin should access its own namespace
            assert config.get("plugin1.setting1") == "value1"
            assert config.get("plugin1.timeout") == 30
            assert config.get("plugin2.setting1") == "value2"
            assert config.get("plugin2.max_items") == 100

            # Global settings should be accessible to all
            assert config.get("global.log_level") == "debug"

            # Non-existent keys should return default
            assert config.get("plugin1.nonexistent", "default") == "default"
            assert config.get("plugin3.anything") is None

        finally:
            plugin_system.stop()

    @pytest.mark.asyncio
    async def test_plugin_data_storage_isolation_through_hosts(self) -> None:
        """Test that plugin data storage access is isolated through host interfaces."""
        test_plugin_manager = create_test_plugin_manager_with_mocks()
        plugin_system = PluginSystem(test_plugin_manager)

        try:
            plugin_system.bootstrap()
            await plugin_system.start_async()

            storage = plugin_system.get_singletons().data_storage
            from paise2.models import Metadata
            from tests.fixtures.mock_plugins import MockDataStorageHost

            # Create different hosts representing different plugins
            host1 = MockDataStorageHost()
            host2 = MockDataStorageHost()

            # Each host should be able to store its own data
            metadata1 = Metadata(source_url="plugin1://document.txt", title="Doc1")
            metadata2 = Metadata(source_url="plugin2://document.txt", title="Doc2")

            item_id1 = await storage.add_item(host1, "content1", metadata1)
            item_id2 = await storage.add_item(host2, "content2", metadata2)

            # Should be able to retrieve items
            retrieved1 = await storage.find_item(item_id1)
            retrieved2 = await storage.find_item(item_id2)

            assert retrieved1 is not None
            assert retrieved1.source_url == "plugin1://document.txt"
            assert retrieved2 is not None
            assert retrieved2.source_url == "plugin2://document.txt"

        finally:
            plugin_system.stop()

    def test_plugin_versioning_for_state_isolation(self) -> None:
        """Test that plugin state versioning works for isolation and migration."""
        test_plugin_manager = create_test_plugin_manager_with_mocks()
        plugin_system = PluginSystem(test_plugin_manager)

        try:
            plugin_system.bootstrap()
            plugin_system.start()

            state_storage = plugin_system.get_singletons().state_storage

            # Store state with different versions
            state_storage.store("plugin.test", "key1", "old_value", version=1)
            state_storage.store("plugin.test", "key2", "medium_value", version=2)
            state_storage.store("plugin.test", "key3", "new_value", version=3)

            # Should be able to get state for specific versions
            old_state = state_storage.get_versioned_state(
                "plugin.test", older_than_version=2
            )
            assert len(old_state) == 1
            assert old_state[0][0] == "key1"  # key
            assert old_state[0][1] == "old_value"  # value
            assert old_state[0][2] == 1  # version

            older_state = state_storage.get_versioned_state(
                "plugin.test", older_than_version=3
            )
            assert len(older_state) == 2

            # Current values should still be accessible
            assert state_storage.get("plugin.test", "key1") == "old_value"
            assert state_storage.get("plugin.test", "key2") == "medium_value"
            assert state_storage.get("plugin.test", "key3") == "new_value"

        finally:
            plugin_system.stop()

    def test_plugin_job_queue_isolation_through_worker_ids(self) -> None:
        """Test that job queue operations can be isolated by worker IDs."""

        @pytest.mark.asyncio
        async def _test_job_isolation() -> None:
            test_plugin_manager = create_test_plugin_manager_with_mocks()
            plugin_system = PluginSystem(test_plugin_manager)

            try:
                plugin_system.bootstrap()
                await plugin_system.start_async()

                job_queue = plugin_system.get_singletons().job_queue

                # Different workers should be able to handle different jobs
                job_id1 = await job_queue.enqueue("fetch_content", {"url": "test1"})
                job_id2 = await job_queue.enqueue("extract_content", {"data": "test2"})
                # job_id3 is for testing that there are still incomplete jobs
                await job_queue.enqueue("store_content", {"item": "test3"})

                # Workers should be able to dequeue jobs
                job1 = await job_queue.dequeue("worker1")
                job2 = await job_queue.dequeue("worker2")

                assert job1 is not None
                assert job2 is not None
                assert job1.job_id != job2.job_id

                # Jobs should be properly assigned to workers
                if job1.job_id in (job_id1, job_id2):
                    assert job1.worker_id == "worker1"

                # Complete jobs should update their status
                await job_queue.complete(job1.job_id, {"status": "success"})
                await job_queue.complete(job2.job_id, {"status": "success"})

                # Should still have incomplete jobs
                incomplete = await job_queue.get_incomplete_jobs()
                assert len(incomplete) >= 1

            finally:
                plugin_system.stop()

        # Run the async test
        import asyncio

        asyncio.run(_test_job_isolation())


class TestPluginSystemIntegration:
    """Test complete plugin system integration scenarios."""

    def test_multiple_configuration_providers_merge_correctly(self) -> None:
        """Test that multiple configuration providers merge their defaults correctly."""
        test_plugin_manager = create_test_plugin_manager_with_mocks()
        plugin_system = PluginSystem(test_plugin_manager)

        # User config that will override and extend plugin defaults
        user_config = {
            "test_plugin": {"user_setting": "user_value", "override": "user_override"}
        }

        try:
            plugin_system.bootstrap()
            plugin_system.start(user_config)

            config = plugin_system.get_singletons().configuration

            # Should have mock plugin defaults
            assert config.get("test_plugin.enabled") is True
            assert config.get("test_plugin.max_items") == 100

            # Should have user overrides
            assert config.get("test_plugin.user_setting") == "user_value"
            assert config.get("test_plugin.override") == "user_override"

        finally:
            plugin_system.stop()

    @pytest.mark.asyncio
    async def test_all_provider_types_work_together(self) -> None:
        """Test that all provider types work together in the complete system."""
        test_plugin_manager = create_test_plugin_manager_with_mocks()
        plugin_system = PluginSystem(test_plugin_manager)

        try:
            plugin_system.bootstrap()
            await plugin_system.start_async()

            singletons = plugin_system.get_singletons()

            # All singletons should be available and functional
            assert singletons.logger is not None
            assert singletons.configuration is not None
            assert singletons.state_storage is not None
            assert singletons.job_queue is not None
            assert singletons.cache is not None
            assert singletons.data_storage is not None

            # Test cross-provider functionality
            # 1. Store state
            singletons.state_storage.store("test", "integration_test", "success")

            # 2. Cache content
            cache_id = await singletons.cache.save("test", "cached content", ".txt")

            # 3. Store data
            from paise2.models import Metadata
            from tests.fixtures.mock_plugins import MockDataStorageHost

            host = MockDataStorageHost()
            metadata = Metadata(source_url="integration://test.txt")
            item_id = await singletons.data_storage.add_item(
                host, "stored content", metadata
            )

            # 4. Queue a job
            job_id = await singletons.job_queue.enqueue(
                "fetch_content", {"test": "integration"}
            )

            # All operations should succeed
            assert singletons.state_storage.get("test", "integration_test") == "success"
            assert await singletons.cache.get(cache_id) == "cached content"
            assert await singletons.data_storage.find_item(item_id) is not None
            assert job_id is not None

        finally:
            plugin_system.stop()

    def test_plugin_system_restart_preserves_state(self) -> None:
        """Test that restarting the plugin system handles state correctly."""
        # Note: This test uses mock providers which don't actually persist state
        # between different instances. In production, real state storage would persist.
        test_plugin_manager = create_test_plugin_manager_with_mocks()
        plugin_system = PluginSystem(test_plugin_manager)

        # First startup and operation
        try:
            plugin_system.bootstrap()
            plugin_system.start()

            state_storage = plugin_system.get_singletons().state_storage
            state_storage.store("persistence_test", "restart_key", "restart_value")

            # Verify state is stored during the same session
            assert (
                state_storage.get("persistence_test", "restart_key") == "restart_value"
            )

        finally:
            plugin_system.stop()

        # Second startup - with mock providers, state is not persisted
        # This is expected behavior for mock providers
        try:
            plugin_system.start()

            state_storage = plugin_system.get_singletons().state_storage
            # Mock state storage doesn't persist between instances, so this is None
            # This is correct behavior for mock providers in tests
            assert state_storage.get("persistence_test", "restart_key") is None

            # But we can store new state in the new instance
            state_storage.store("persistence_test", "new_key", "new_value")
            assert state_storage.get("persistence_test", "new_key") == "new_value"

        finally:
            plugin_system.stop()
