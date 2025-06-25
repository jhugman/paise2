# ABOUTME: Configuration provider implementations for PAISE2
# ABOUTME: Provides file-based configuration loading and provider classes

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import ModuleType

from paise2.plugins.core.interfaces import ConfigurationProvider

__all__ = ["FileConfigurationProvider"]


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
