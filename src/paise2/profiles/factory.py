# ABOUTME: Profile-based plugin manager factory functions
# ABOUTME: Provides convenient functions to create plugin managers for
# different profiles

import os
from pathlib import Path

import paise2
from paise2.plugins.core.registry import PluginManager


def create_plugin_manager(profile: str) -> PluginManager:
    # Create plugin manager based on profile
    if profile == "test":
        return create_test_plugin_manager()
    if profile == "development":
        return create_development_plugin_manager()
    if profile == "production":
        return create_production_plugin_manager()

    error_msg = f"Unknown profile: {profile}"
    raise ValueError(error_msg)


def _profile(profile: str) -> Path:
    return Path(paise2.__file__).parent / "profiles" / profile


def _base_profile() -> Path:
    return _profile("base")


def _create_plugin_manager(profile: str) -> PluginManager:
    root = _profile(profile)
    plugin_manager = PluginManager(profile=str(root))
    plugin_manager.discover_internal_plugins(_base_profile())
    return plugin_manager


def create_production_plugin_manager() -> PluginManager:
    """
    Create a plugin manager with production profile plugins and base plugins.

    Production profile includes:
    - Base profile plugins (core CLI commands)
    - File-based state storage (persistent)
    - SQLite job queues (when implemented)
    - File-based caching (when implemented)

    Returns:
        PluginManager configured for production use
    """
    # Create plugin manager for production profile
    return _create_plugin_manager("production")


def create_development_plugin_manager() -> PluginManager:
    """
    Create a plugin manager with development profile plugins and base plugins.

    Development profile includes:
    - Base profile plugins (core CLI commands)
    - Both memory and file-based state storage
    - Multiple job queue options
    - Flexible caching options

    Returns:
        PluginManager configured for development use
    """
    # Create plugin manager for development profile
    return _create_plugin_manager("development")


def create_test_plugin_manager() -> PluginManager:
    """
    Create a plugin manager with test profile plugins and base plugins.

    Test profile includes:
    - Base profile plugins (core CLI commands)
    - Memory-only state storage (fast)
    - Synchronous job processing
    - Memory-only caching

    Returns:
        PluginManager configured for testing
    """
    # Create plugin manager for test profile
    return _create_plugin_manager("test")


def create_default_plugin_manager() -> PluginManager:
    """
    Create a plugin manager with the default no internal plugins.

    Returns:
        PluginManager with no internal plugins
    """
    return PluginManager()  # Uses default paise2.__file__ root


def create_plugin_manager_from_env() -> PluginManager:
    """
    Create a plugin manager based on the PAISE2_PROFILE environment variable.

    Defaults to 'development' if PAISE2_PROFILE is not set.

    Returns:
        PluginManager configured for the specified profile

    Raises:
        ValueError: If an unknown profile is specified
    """
    profile = os.getenv("PAISE2_PROFILE", "development").lower()
    return create_plugin_manager(profile)
