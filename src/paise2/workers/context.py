# ABOUTME: Worker context initialization and management for PAISE2 background workers
# ABOUTME: Provides Huey worker startup hooks and thread-local context storage

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Any

from paise2.profiles.factory import create_plugin_manager_from_env

if TYPE_CHECKING:
    from paise2.main import Application
    from paise2.plugins.core.startup import Singletons

__all__ = [
    "WorkerContext",
    "cleanup_worker_context",
    "get_worker_context",
    "initialize_worker_context",
]


class WorkerContext:
    """Container for worker-specific application context.

    Holds the complete PAISE2 application singletons that are recreated
    in each worker process to ensure complete isolation.
    """

    def __init__(self, singletons: Singletons, app: Application | None = None) -> None:
        """Initialize worker context with application singletons.

        Args:
            singletons: Complete application singletons container
        """
        self.singletons = singletons
        self.app = app
        self.worker_id = threading.current_thread().ident


class ThreadContextManager:
    """Thread-local storage manager for worker contexts.

    Provides thread-safe access to worker contexts, ensuring each worker
    thread has its own isolated application context.
    """

    def __init__(self) -> None:
        """Initialize the thread context manager."""
        self._local = threading.local()

    def set_context(self, context: WorkerContext) -> None:
        """Set the worker context for the current thread.

        Args:
            context: Worker context to set for current thread
        """
        self._local.context = context

    def get_context(self) -> WorkerContext | None:
        """Get the worker context for the current thread.

        Returns:
            Worker context for current thread, or None if not set
        """
        return getattr(self._local, "context", None)

    def clear_context(self) -> None:
        """Clear the worker context for the current thread."""
        if hasattr(self._local, "context"):
            delattr(self._local, "context")


# Global thread context manager
_thread_context_manager = ThreadContextManager()


def initialize_worker_context() -> None:
    """Initialize worker context using complete PAISE2 application startup.

    This function recreates the complete application context in the worker
    process by using the same Application startup sequence as the main process.

    Profile is determined by the PAISE2_PROFILE environment variable.
    Falls back to 'development' if not set.

    This function is designed to be called by Huey's @huey.on_startup() hook.

    Raises:
        RuntimeError: If worker context initialization fails
    """
    try:
        # Import here to avoid circular dependencies
        from paise2.main import Application

        # Create and start complete application context
        plugin_manager = create_plugin_manager_from_env()
        app = Application(plugin_manager=plugin_manager)
        app.start()

        # Get the complete singletons container
        singletons = app.get_singletons()

        # Create worker context and store in thread-local storage
        worker_context = WorkerContext(singletons, app)
        _thread_context_manager.set_context(worker_context)

        # Log successful initialization
        singletons.logger.info(
            "Worker context initialized: worker ID: %s",
            worker_context.worker_id,
        )

    except Exception as e:
        # Log error and re-raise
        # Since we might not have a logger yet, we'll use a simple print
        error_msg = f"Worker context initialization failed: {e}"
        print(error_msg)  # noqa: T201
        raise RuntimeError(error_msg) from e


def cleanup_worker_context() -> None:
    """Clean up worker context and resources.

    This function should be called when a worker is shutting down to ensure
    proper resource cleanup.

    This function is designed to be called by Huey's @huey.on_shutdown() hook
    if available, or manually during worker shutdown.
    """
    try:
        # Get current worker context
        worker_context = _thread_context_manager.get_context()

        if worker_context is not None:
            # Log cleanup
            worker_context.singletons.logger.info(
                "Cleaning up worker context for worker ID: %s",
                worker_context.worker_id,
            )

            # Note: The Application class doesn't currently expose stop()
            # in a way that's accessible from the singletons. This is a
            # placeholder for future enhancement.
            # In a full implementation, we'd want to call app.stop()
            if worker_context.app is not None:
                worker_context.app.stop()

            # Clear the thread-local context
            _thread_context_manager.clear_context()

    except Exception as e:
        # Log error but don't re-raise during cleanup
        error_msg = f"Worker context cleanup failed: {e}"
        print(error_msg)  # noqa: T201


def get_worker_context() -> WorkerContext:
    """Get the current worker context.

    Returns:
        Current worker context with application singletons

    Raises:
        RuntimeError: If no worker context is available (not in worker process)
    """
    context = _thread_context_manager.get_context()

    if context is None:
        error_msg = (
            "No worker context available. "
            "This function should only be called from within a Huey worker process "
            "after initialize_worker_context() has been called."
        )
        raise RuntimeError(error_msg)

    return context


def get_worker_singletons() -> Singletons:
    """Get the application singletons from the current worker context.

    Convenience function for accessing singletons directly.

    Returns:
        Application singletons container

    Raises:
        RuntimeError: If no worker context is available
    """
    return get_worker_context().singletons


# Convenience functions for common singleton access patterns
def get_worker_logger() -> Any:
    """Get the logger from the current worker context."""
    return get_worker_singletons().logger


def get_worker_configuration() -> Any:
    """Get the configuration from the current worker context."""
    return get_worker_singletons().configuration


def get_worker_data_storage() -> Any:
    """Get the data storage from the current worker context."""
    return get_worker_singletons().data_storage


def get_worker_cache() -> Any:
    """Get the cache from the current worker context."""
    return get_worker_singletons().cache


def get_worker_state_storage() -> Any:
    """Get the state storage from the current worker context."""
    return get_worker_singletons().state_storage
