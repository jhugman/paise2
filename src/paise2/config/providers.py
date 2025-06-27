# ABOUTME: Configuration provider implementations for PAISE2
# ABOUTME: Provides file-based configuration loading and provider classes

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from paise2.constants import get_profile

if TYPE_CHECKING:
    from types import ModuleType

from paise2.plugins.core.interfaces import ConfigurationProvider

__all__ = ["FileConfigurationProvider", "ProfileFileConfigurationProvider"]


class FileConfigurationProvider(ConfigurationProvider):
    """
    File-based configuration provider that loads YAML configuration files.

    Supports both absolute and relative file paths. When a plugin module is provided,
    relative paths are resolved relative to the plugin module's directory.
    """

    def __init__(
        self,
        file_path: str,
        plugin_module: ModuleType | None = None,
        config_id: str | None = None,
    ):
        """
        Initialize FileConfigurationProvider.

        Args:
            file_path: Path to configuration file (absolute or relative)
            plugin_module: Plugin module for relative path resolution
        """
        # Handle relative paths to plugin module if provided
        if plugin_module and not Path(file_path).is_absolute():
            module_path = Path(plugin_module.__file__ or "")
            module_dir = module_path.parent
            self.file_path = str(module_dir / file_path)
        else:
            self.file_path = file_path

        self._config_id = config_id or Path(file_path).stem

    def get_default_configuration(self) -> str:
        """
        Load and return YAML configuration as string.

        Returns:
            YAML configuration string, empty string if file doesn't exist
        """
        try:
            path = Path(self.file_path)
            if path.exists():
                return path.read_text(encoding="utf-8")
        except OSError:
            pass
        return ""

    def get_configuration_id(self) -> str:
        """
        Get configuration identifier (filename).

        Returns:
            Configuration identifier
        """
        return self._config_id


class ProfileFileConfigurationProvider(ConfigurationProvider):
    """
    Profile-sensitive configuration provider that loads YAML configuration files.

    Looks for configuration files in the profile directory relative to where
    the provider is registered. Uses PAISE2_PROFILE environment variable to
    determine which profile directory to search.

    For example, if registered in 'base/logging.py' and PAISE2_PROFILE=production,
    it will look for the file in '../production/filename.yaml'.
    """

    def __init__(
        self,
        file_path: str,
        plugin_module: ModuleType | None = None,
        config_id: str | None = None,
    ):
        """
        Initialize ProfileFileConfigurationProvider.

        Args:
            file_path: Path to configuration file (absolute or relative)
            plugin_module: Plugin module for relative path resolution
            config_id: Optional custom configuration ID
        """
        self.file_path = file_path
        self.plugin_module = plugin_module
        self._config_id = config_id or Path(file_path).stem

    def _resolve_profile_file_path(self) -> Path:
        """Resolve the full path to the configuration file based on current profile."""
        # Get current profile from environment
        profile = get_profile()

        # Handle absolute paths - use as-is
        if Path(self.file_path).is_absolute():
            return Path(self.file_path)

        # For relative paths, we need the plugin module
        if self.plugin_module is None:
            msg = "plugin_module is required for relative path resolution"
            raise ValueError(msg)

        # Get the directory where the provider is registered
        module_path = Path(self.plugin_module.__file__ or "")
        module_dir = module_path.parent

        # Go up one level and then into the profile directory
        profile_dir = module_dir.parent / profile

        # Return the full path to the configuration file
        return profile_dir / self.file_path

    def get_default_configuration(self) -> str:
        """
        Load and return YAML configuration as string from profile directory.

        Returns:
            YAML configuration string

        Raises:
            FileNotFoundError: If the configuration file doesn't exist
        """
        config_path = self._resolve_profile_file_path()

        if not config_path.exists():
            profile = get_profile()
            msg = f"Configuration file not found: {config_path}. Profile: {profile}"
            raise FileNotFoundError(msg)

        try:
            return config_path.read_text(encoding="utf-8")
        except OSError as e:
            msg = f"Failed to read configuration file {config_path}: {e}"
            raise FileNotFoundError(msg) from e

    def get_configuration_id(self) -> str:
        """
        Get configuration identifier (filename stem).

        Returns:
            Configuration identifier
        """
        return self._config_id
