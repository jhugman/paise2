# ABOUTME: Test fixtures and mock implementations for unit testing
# ABOUTME: Includes mock objects for various interfaces and test data

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from paise2.config.models import ConfigurationDict

# Import test factories
from tests.fixtures.factory import create_test_plugin_manager_with_mocks

from .mock_plugins import (
    MockBaseHost,
    MockCacheManager,
    MockCacheProvider,
    MockConfigurationProvider,
    MockContentExtractor,
    MockContentExtractorHost,
    MockContentFetcher,
    MockContentFetcherHost,
    MockContentSource,
    MockContentSourceHost,
    MockDataStorage,
    MockDataStorageProvider,
    MockJobQueue,
    MockJobQueueProvider,
    MockLifecycleAction,
    MockLifecycleHost,
    MockLogger,
    MockStateManager,
    MockStateStorage,
    MockStateStorageProvider,
)


class MockConfiguration:
    """
    Mock configuration implementation for testing.

    Supports both simple key access and dotted path notation.
    Provides a complete implementation of the Configuration protocol.
    """

    def __init__(self, config_dict: dict[str, Any] | None = None) -> None:
        """Initialize with configuration data."""
        self._config = config_dict or {}

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key.

        Supports dotted path notation (e.g., "plugin.setting").
        """
        # Simple key access
        return self._config.get(key, default)

    def get_section(self, section: str) -> ConfigurationDict:
        """Get configuration section."""
        return self._config.get(section, {})

    def addition(self, key: str, default: Any = None) -> Any:
        """Get added configuration value (always returns default for mock)."""
        return default

    def removal(self, key: str, default: Any = None) -> Any:
        """Get removed configuration value (always returns default for mock)."""
        return default

    def has_changed(self, key: str) -> bool:
        """Check if configuration key has changed (always returns False for mock)."""
        return False

    @property
    def last_diff(self) -> Any:
        """Get last configuration diff (always returns None for mock)."""
        return None


__all__ = [
    "MockBaseHost",
    "MockCacheManager",
    "MockCacheProvider",
    "MockConfiguration",
    "MockConfigurationProvider",
    "MockContentExtractor",
    "MockContentExtractorHost",
    "MockContentFetcher",
    "MockContentFetcherHost",
    "MockContentSource",
    "MockContentSourceHost",
    "MockDataStorage",
    "MockDataStorageProvider",
    "MockJobQueue",
    "MockJobQueueProvider",
    "MockLifecycleAction",
    "MockLifecycleHost",
    "MockLogger",
    "MockStateManager",
    "MockStateStorage",
    "MockStateStorageProvider",
    "create_test_plugin_manager_with_mocks",
]
