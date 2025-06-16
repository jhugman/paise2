# ABOUTME: Unit tests for TaskQueueProvider registration in the plugin system
# ABOUTME: Tests that TaskQueueProvider registration works correctly with plugin manager

from __future__ import annotations

from typing import Any

from paise2.plugins.core.registry import PluginManager
from paise2.plugins.providers.task_queue import (
    HueySQLiteTaskQueueProvider,
    NoTaskQueueProvider,
)


class MockConfiguration:
    """Mock configuration for testing."""

    def __init__(self, data: dict[str, Any] | None = None) -> None:
        self._data = data or {}

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        keys = key.split(".")
        current = self._data
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return default
        return current

    def get_section(self, section: str) -> dict[str, Any]:
        """Get configuration section."""
        return self._data.get(section, {})


def test_plugin_manager_can_register_task_queue_provider() -> None:
    """Test that PluginManager can register TaskQueueProvider instances."""
    plugin_manager = PluginManager()
    provider = NoTaskQueueProvider()

    # Register the provider
    result = plugin_manager.register_task_queue_provider(provider)

    assert result is True
    providers = plugin_manager.get_task_queue_providers()
    assert len(providers) == 1
    assert providers[0] is provider


def test_plugin_manager_can_register_multiple_task_queue_providers() -> None:
    """Test that PluginManager can register multiple TaskQueueProvider instances."""
    plugin_manager = PluginManager()
    provider1 = NoTaskQueueProvider()
    provider2 = HueySQLiteTaskQueueProvider()

    # Register both providers
    result1 = plugin_manager.register_task_queue_provider(provider1)
    result2 = plugin_manager.register_task_queue_provider(provider2)

    assert result1 is True
    assert result2 is True
    providers = plugin_manager.get_task_queue_providers()
    assert len(providers) == 2
    assert provider1 in providers
    assert provider2 in providers


def test_plugin_manager_validates_task_queue_provider() -> None:
    """Test that PluginManager validates TaskQueueProvider instances."""
    plugin_manager = PluginManager()
    invalid_provider = "not a provider"

    # Try to register invalid provider
    result = plugin_manager.register_task_queue_provider(invalid_provider)  # type: ignore[arg-type]

    assert result is False
    providers = plugin_manager.get_task_queue_providers()
    assert len(providers) == 0


def test_get_task_queue_providers_returns_copy() -> None:
    """Test that get_task_queue_providers returns a copy of the providers list."""
    plugin_manager = PluginManager()
    provider = NoTaskQueueProvider()
    plugin_manager.register_task_queue_provider(provider)

    # Get providers list
    providers1 = plugin_manager.get_task_queue_providers()
    providers2 = plugin_manager.get_task_queue_providers()

    # Should be different list objects (copies)
    assert providers1 is not providers2
    assert providers1 == providers2

    # Modifying returned list shouldn't affect internal state
    providers1.clear()
    providers3 = plugin_manager.get_task_queue_providers()
    assert len(providers3) == 1
