# ABOUTME: Configuration data models and types for PAISE2
# ABOUTME: Provides Configuration protocol and related configuration types

from __future__ import annotations

from typing import Any, Dict, Protocol, runtime_checkable

__all__ = ["Configuration", "ConfigurationDict"]

# Configuration dictionary type for YAML data
ConfigurationDict = Dict[str, Any]


@runtime_checkable
class Configuration(Protocol):
    """
    Configuration protocol for accessing merged configuration data.

    This protocol provides methods for accessing configuration values with
    support for dotted path access and section-based retrieval.
    """

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value by key with optional default.

        Supports dotted path access like 'plugin.section.key'.

        Args:
            key: Configuration key (supports dotted paths)
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        ...

    def get_section(self, section: str) -> ConfigurationDict:
        """
        Get an entire configuration section.

        Args:
            section: Section name

        Returns:
            Dictionary containing section configuration
        """
        ...
