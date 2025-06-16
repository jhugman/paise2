# ABOUTME: Integration tests for TaskQueueProvider with different profiles
# ABOUTME: Tests that all profiles correctly register TaskQueueProvider instances

from __future__ import annotations

from pathlib import Path
from typing import Any

from paise2.plugins.core.registry import PluginManager
from paise2.plugins.providers.task_queue import (
    HueySQLiteTaskQueueProvider,
    NoTaskQueueProvider,
)


def test_test_profile_registers_task_queue_provider() -> None:
    """Test that test profile registers NoTaskQueueProvider."""
    test_profile_path = (
        Path(__file__).parent.parent.parent / "src" / "paise2" / "profiles" / "test"
    )
    plugin_manager = PluginManager()

    # Discover and load plugins from test profile
    plugin_manager.discover_internal_plugins(test_profile_path)
    plugin_manager.load_plugins()

    # Check that TaskQueueProvider was registered
    task_queue_providers = plugin_manager.get_task_queue_providers()
    assert len(task_queue_providers) >= 1

    # Should have NoTaskQueueProvider
    no_providers = [
        p for p in task_queue_providers if isinstance(p, NoTaskQueueProvider)
    ]
    assert len(no_providers) == 1


def test_development_profile_registers_task_queue_providers() -> None:
    """Test that development profile registers multiple TaskQueueProviders."""
    dev_profile_path = (
        Path(__file__).parent.parent.parent
        / "src"
        / "paise2"
        / "profiles"
        / "development"
    )
    plugin_manager = PluginManager()

    # Discover and load plugins from development profile
    plugin_manager.discover_internal_plugins(dev_profile_path)
    plugin_manager.load_plugins()

    # Check that TaskQueueProviders were registered
    task_queue_providers = plugin_manager.get_task_queue_providers()
    assert len(task_queue_providers) >= 2

    # Should have both NoTaskQueueProvider and HueySQLiteTaskQueueProvider
    no_providers = [
        p for p in task_queue_providers if isinstance(p, NoTaskQueueProvider)
    ]
    sqlite_providers = [
        p for p in task_queue_providers if isinstance(p, HueySQLiteTaskQueueProvider)
    ]

    assert len(no_providers) == 1
    assert len(sqlite_providers) == 1


def test_production_profile_registers_task_queue_providers() -> None:
    """Test that production profile registers TaskQueueProviders."""
    prod_profile_path = (
        Path(__file__).parent.parent.parent
        / "src"
        / "paise2"
        / "profiles"
        / "production"
    )
    plugin_manager = PluginManager()

    # Discover and load plugins from production profile
    plugin_manager.discover_internal_plugins(prod_profile_path)
    plugin_manager.load_plugins()

    # Check that TaskQueueProviders were registered
    task_queue_providers = plugin_manager.get_task_queue_providers()
    assert len(task_queue_providers) >= 1

    # Should have HueySQLiteTaskQueueProvider (and possibly HueyRedisTaskQueueProvider)
    sqlite_providers = [
        p for p in task_queue_providers if isinstance(p, HueySQLiteTaskQueueProvider)
    ]
    assert len(sqlite_providers) == 1


def test_task_queue_providers_create_correct_instances() -> None:
    """Test that TaskQueueProviders create the correct Huey instances."""
    # Test NoTaskQueueProvider
    no_provider = NoTaskQueueProvider()

    class MockConfig:
        def get(self, key: str, default: Any = None) -> Any:
            return default

    result = no_provider.create_task_queue(MockConfig())  # type: ignore[arg-type]
    assert result is not None
    from huey import MemoryHuey

    assert isinstance(result, MemoryHuey)
    assert result.immediate is True  # Should execute immediately for testing

    # Test HueySQLiteTaskQueueProvider
    sqlite_provider = HueySQLiteTaskQueueProvider()
    task_queue = sqlite_provider.create_task_queue(MockConfig())  # type: ignore[arg-type]

    assert task_queue is not None
    assert hasattr(task_queue, "task")
    assert hasattr(task_queue, "periodic_task")
