# ABOUTME: Profile-based plugin manager factory functions
# ABOUTME: Provides convenient functions to create plugin managers for
# different profiles

from pathlib import Path

import paise2
from paise2.plugins.core.registry import PluginManager


def create_production_plugin_manager() -> PluginManager:
    """
    Create a plugin manager with production profile plugins.

    Production profile includes:
    - File-based state storage (persistent)
    - SQLite job queues (when implemented)
    - File-based caching (when implemented)

    Returns:
        PluginManager configured for production use
    """
    production_root = Path(paise2.__file__).parent / "profiles" / "production"
    return PluginManager(profile=str(production_root))


def create_development_plugin_manager() -> PluginManager:
    """
    Create a plugin manager with development profile plugins.

    Development profile includes:
    - Both memory and file-based state storage
    - Multiple job queue options
    - Flexible caching options

    Returns:
        PluginManager configured for development use
    """
    development_root = Path(paise2.__file__).parent / "profiles" / "development"
    return PluginManager(profile=str(development_root))


def create_test_plugin_manager() -> PluginManager:
    """
    Create a plugin manager with test profile plugins.

    Test profile includes:
    - Memory-only state storage (fast)
    - Synchronous job processing
    - Memory-only caching

    Returns:
        PluginManager configured for testing
    """
    test_root = Path(paise2.__file__).parent / "profiles" / "test"
    return PluginManager(profile=str(test_root))


def create_default_plugin_manager() -> PluginManager:
    """
    Create a plugin manager with the default no internal plugins.

    Returns:
        PluginManager with no internal plugins
    """
    return PluginManager()  # Uses default paise2.__file__ root
