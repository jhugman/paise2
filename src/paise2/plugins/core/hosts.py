# ABOUTME: Host infrastructure for plugin system including BaseHost and StateManager.
# ABOUTME: Provides state partitioning, host factories, and basic host functionality.

from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from paise2.models import Metadata
    from paise2.plugins.core.interfaces import (
        Configuration,
        StateManager,
        StateStorage,
    )


class ConcreteStateManager:
    """StateManager implementation with automatic partitioning by plugin module name."""

    def __init__(self, state_storage: StateStorage, plugin_module_name: str):
        self.state_storage = state_storage
        self.partition_key = plugin_module_name

    def store(self, key: str, value: Any, version: int = 1) -> None:
        """Store state with automatic partitioning."""
        self.state_storage.store(self.partition_key, key, value, version)

    def get(self, key: str, default: Any = None) -> Any:
        """Get state with automatic partitioning."""
        return self.state_storage.get(self.partition_key, key, default)

    def get_versioned_state(
        self, older_than_version: int
    ) -> list[tuple[str, Any, int]]:
        """Get versioned state for plugin updates."""
        return self.state_storage.get_versioned_state(
            self.partition_key, older_than_version
        )

    def get_all_keys_with_value(self, value: Any) -> list[str]:
        """Get all keys with a specific value."""
        return self.state_storage.get_all_keys_with_value(self.partition_key, value)


class BaseHost:
    """Base host class providing common functionality to all plugin hosts."""

    def __init__(
        self,
        logger: Any,
        configuration: Configuration,
        state_storage: StateStorage,
        plugin_module_name: str,
    ):
        self._logger = logger
        self._configuration = configuration
        self._state = ConcreteStateManager(state_storage, plugin_module_name)

    @property
    def logger(self) -> Any:
        """Get the logger instance."""
        return self._logger

    @property
    def configuration(self) -> Configuration:
        """Get the configuration dictionary."""
        return self._configuration

    @property
    def state(self) -> StateManager:
        """Get the state manager for this plugin."""
        return self._state

    def schedule_fetch(self, url: str, metadata: Metadata | None = None) -> None:
        """Schedule a fetch operation (placeholder implementation)."""
        # NOTE: This will be implemented when job queue integration is added


def get_plugin_module_name_from_frame() -> str:
    """Extract plugin module name from the call stack."""
    # Get the calling frame information
    frame = inspect.currentframe()
    try:
        # Go up the stack to find the calling module
        current_frame = frame
        while current_frame:
            current_frame = current_frame.f_back
            if current_frame:
                module = inspect.getmodule(current_frame)
                if module and module.__name__:
                    module_name = module.__name__
                    # Skip internal frames and return the first meaningful module
                    if (
                        not module_name.startswith("_pytest")
                        and module_name != "__main__"
                    ):
                        return module_name
    finally:
        del frame  # Prevent reference cycles

    # Fallback - for test environments, try to get the test module name
    frame = inspect.currentframe()
    try:
        if frame and frame.f_back:
            caller_frame = frame.f_back
            module = inspect.getmodule(caller_frame)
            if module and module.__name__:
                return module.__name__
    finally:
        del frame

    return "unknown.module"


def create_state_manager(
    state_storage: StateStorage, plugin_module_name: str
) -> StateManager:
    """Create a StateManager with automatic partitioning."""
    return ConcreteStateManager(state_storage, plugin_module_name)


def create_base_host(
    logger: Any,
    configuration: Configuration,
    state_storage: StateStorage,
    plugin_module_name: str,
) -> BaseHost:
    """Create a BaseHost instance."""
    return BaseHost(logger, configuration, state_storage, plugin_module_name)
