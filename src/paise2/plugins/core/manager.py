# ABOUTME: Main PluginSystem class that orchestrates the complete plugin lifecycle
# ABOUTME: from discovery through startup, operation, and graceful shutdown.

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from paise2.plugins.core.registry import PluginManager
    from paise2.plugins.core.startup import Singletons

from paise2.plugins.core.startup import StartupManager
from paise2.profiles.factory import create_development_plugin_manager


class PluginSystem:
    """
    Main PluginSystem class that manages the complete plugin lifecycle.

    Coordinates plugin discovery, registration, startup, operation, and shutdown.
    Provides the main entry point for the PAISE2 plugin system.
    """

    def __init__(self, plugin_manager: PluginManager | None = None) -> None:
        """Initialize the PluginSystem with optional plugin manager."""
        self._startup_manager: StartupManager | None = None
        self._singletons: Singletons | None = None
        self._is_running = False
        self._plugin_manager = plugin_manager

    def bootstrap(self) -> None:
        """
        Initialize the bootstrap phase of the plugin system.

        Creates the StartupManager with a development plugin manager and
        prepares for the startup sequence. Must be called before start().
        """
        if self._startup_manager is not None:
            return  # Already bootstrapped

        plugin_manager = (
            self._plugin_manager
            if self._plugin_manager is not None
            else create_development_plugin_manager()
        )
        self._startup_manager = StartupManager(plugin_manager)

    def start(self, user_config_dict: dict[str, Any] | None = None) -> None:
        """
        Start the plugin system by running the complete startup sequence.

        Args:
            user_config_dict: Optional user configuration overrides.

        Raises:
            RuntimeError: If bootstrap() has not been called first.
        """
        if self._startup_manager is None:
            msg = "Must call bootstrap() before start()"
            raise RuntimeError(msg)

        if self._is_running:
            return  # Already running

        try:
            # Run the complete startup sequence (async)
            self._singletons = asyncio.run(
                self._startup_manager.execute_startup(user_config_dict)
            )
            self._is_running = True
        except Exception:
            # Ensure clean state on startup failure
            self._singletons = None
            self._is_running = False
            raise

    async def start_async(self, user_config_dict: dict[str, Any] | None = None) -> None:
        """
        Start the plugin system asynchronously by running the complete startup sequence.

        This method should be used when calling from an async context to avoid
        the "asyncio.run() cannot be called from a running event loop" error.

        Args:
            user_config_dict: Optional user configuration overrides.

        Raises:
            RuntimeError: If bootstrap() has not been called first.
        """
        if self._startup_manager is None:
            msg = "Must call bootstrap() before start_async()"
            raise RuntimeError(msg)

        if self._is_running:
            return  # Already running

        try:
            # Run the complete startup sequence (async)
            self._singletons = await self._startup_manager.execute_startup(
                user_config_dict
            )
            self._is_running = True
        except Exception:
            # Ensure clean state on startup failure
            self._singletons = None
            self._is_running = False
            raise

    def stop(self) -> None:
        """
        Stop the plugin system and perform cleanup.

        Gracefully shuts down all components and resets system state.
        Safe to call even if system is not running.
        """
        if not self._is_running:
            self._is_running = False
            self._singletons = None
            return

        try:
            # Graceful shutdown will be implemented when needed
            # For now, just reset state
            pass
        finally:
            # Always reset state
            self._is_running = False
            self._singletons = None

    def is_running(self) -> bool:
        """
        Check if the plugin system is currently running.

        Returns:
            True if the system is running, False otherwise.
        """
        return self._is_running

    def get_singletons(self) -> Singletons:
        """
        Get the system singletons container.

        Returns:
            The Singletons container with all system services.

        Raises:
            RuntimeError: If the system is not currently running.
        """
        if not self._is_running or self._singletons is None:
            msg = "System is not running. Call start() first."
            raise RuntimeError(msg)

        return self._singletons

    def get_plugin_manager(self) -> PluginManager:
        """
        Get the plugin manager for direct plugin system access.

        Returns:
            The PluginManager instance.

        Raises:
            RuntimeError: If bootstrap() has not been called.
        """
        if self._startup_manager is None:
            msg = "Must call bootstrap() before accessing plugin manager"
            raise RuntimeError(msg)

        return self._startup_manager.plugin_manager
