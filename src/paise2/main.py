# ABOUTME: Main application entry point with complete system lifecycle management
# ABOUTME: Provides high-level interface for starting, stopping, and managing PAISE2

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import types

    from paise2.plugins.core.manager import PluginSystem
    from paise2.plugins.core.startup import Singletons

__all__ = ["Application"]


class Application:
    """
    Main application class that provides high-level interface for PAISE2.

    This class orchestrates the complete system lifecycle including startup,
    shutdown, and access to system singletons. It supports different profiles
    (test, development, production) and user configuration overrides.
    """

    def __init__(
        self,
        profile: str = "test",
        user_config: dict[str, Any] | None = None,
        plugin_manager: Any | None = None,
    ):
        """
        Initialize the application with the specified profile.

        Args:
            profile: Profile to use ("test", "development", "production")
            user_config: Optional user configuration overrides
            plugin_manager: Optional plugin manager instance. If not provided,
                           one will be created based on the profile.
        """
        self._user_config = user_config

        from paise2.profiles.factory import create_plugin_manager

        self._plugin_manager = plugin_manager or create_plugin_manager(profile)
        self._plugin_system: PluginSystem | None = None
        self._is_running = False

    def start(self) -> None:
        """Start the application with complete system startup."""
        if self._is_running:
            return

        # Import here to avoid circular dependencies
        from paise2.plugins.core.manager import PluginSystem

        # Create and start plugin system
        self._plugin_system = PluginSystem(self._plugin_manager)
        self._plugin_system.bootstrap()
        self._plugin_system.start(user_config_dict=self._user_config)
        self._is_running = True

    def start_for_worker(self) -> None:
        """Start the application in worker mode with only singleton initialization.

        This method initializes the application up to phase 3 (singleton creation)
        without starting content sources or lifecycle actions. This is intended
        for worker processes that only need access to system services.
        """
        if self._is_running:
            return

        # Import here to avoid circular dependencies
        from paise2.plugins.core.manager import PluginSystem

        # Create and start plugin system in worker mode
        self._plugin_system = PluginSystem(self._plugin_manager)
        self._plugin_system.bootstrap()
        self._plugin_system.start_to_singletons(user_config_dict=self._user_config)
        self._is_running = True

    def stop(self) -> None:
        """Stop the application with graceful shutdown."""
        if not self._is_running:
            return

        if self._plugin_system:
            self._plugin_system.stop()

        self._is_running = False

    def is_running(self) -> bool:
        """Check if the application is currently running."""
        return self._is_running

    def get_singletons(self) -> Singletons:
        """
        Get access to system singletons.

        Returns:
            Singletons container with all system components

        Raises:
            RuntimeError: If application is not running
        """
        if not self._is_running or not self._plugin_system:
            error_msg = "Application must be running to access singletons"
            raise RuntimeError(error_msg)

        # Import here to avoid circular dependencies during type checking
        from paise2.plugins.core.startup import Singletons  # noqa: F401

        return self._plugin_system.get_singletons()

    def __enter__(self) -> Application:  # noqa: PYI034
        """Context manager entry."""
        self.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        """Context manager exit."""
        self.stop()
