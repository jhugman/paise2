# ABOUTME: Test-specific factory functions for creating plugin managers with mocks
# ABOUTME: Provides factory functions for test environments with mock plugins

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from paise2.plugins.core.registry import PluginManager

from paise2.profiles.factory import create_test_plugin_manager


def create_test_plugin_manager_with_mocks() -> PluginManager:
    """
    Create a plugin manager with test profile plugins plus mock test fixtures.

    This version includes both the test profile plugins and manually registers
    the mock plugins from tests.fixtures.mock_plugins for comprehensive testing.

    Returns:
        PluginManager configured for testing with mock plugins
    """
    # Start with test profile plugins
    plugin_manager = create_test_plugin_manager()

    # Manually register mock plugins from test fixtures
    try:
        from tests.fixtures.mock_plugins import (
            MockCacheProvider,
            MockConfigurationProvider,
            MockContentExtractor,
            MockContentFetcher,
            MockContentSource,
            MockDataStorageProvider,
            MockJobQueueProvider,
            MockLifecycleAction,
            MockStateStorageProvider,
        )

        # Register each mock plugin directly
        plugin_manager.register_configuration_provider(MockConfigurationProvider())
        plugin_manager.register_content_extractor(MockContentExtractor())
        plugin_manager.register_content_source(MockContentSource())
        plugin_manager.register_content_fetcher(MockContentFetcher())
        plugin_manager.register_lifecycle_action(MockLifecycleAction())
        plugin_manager.register_data_storage_provider(MockDataStorageProvider())
        plugin_manager.register_job_queue_provider(MockJobQueueProvider())
        plugin_manager.register_state_storage_provider(MockStateStorageProvider())
        plugin_manager.register_cache_provider(MockCacheProvider())

    except ImportError:
        # If mock plugins aren't available, just use regular test manager
        pass

    return plugin_manager
