# ABOUTME: Tests for ProfileFileConfigurationProvider functionality
# ABOUTME: Tests profile-sensitive configuration file loading and validation

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from paise2.plugins.core.interfaces import ConfigurationProvider


class TestProfileFileConfigurationProvider:
    """Test ProfileFileConfigurationProvider implementation."""

    def test_provider_implements_protocol(self) -> None:
        """Test provider implements ConfigurationProvider protocol."""
        from paise2.config.providers import ProfileFileConfigurationProvider

        provider = ProfileFileConfigurationProvider("test-config.yaml")
        assert isinstance(provider, ConfigurationProvider)

    def test_provider_finds_config_in_profile_directory(self) -> None:
        """Test provider finds config file in profile directory."""
        from paise2.config.providers import ProfileFileConfigurationProvider

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create directory structure:
            # temp_dir/
            #   base/
            #     logging.py (registration location)
            #   production/
            #     logging-config.yaml (target file)
            base_dir = Path(temp_dir) / "base"
            production_dir = Path(temp_dir) / "production"
            base_dir.mkdir()
            production_dir.mkdir()

            # Create the configuration file
            config_file = production_dir / "logging-config.yaml"
            config_data = {"logging": {"level": "INFO"}}
            with config_file.open("w") as f:
                yaml.dump(config_data, f)

            # Create a mock module in the base directory
            import types

            mock_module = types.ModuleType("mock_module")
            mock_module.__file__ = str(base_dir / "logging.py")

            # Test with PAISE2_PROFILE=production
            with patch.dict(os.environ, {"PAISE2_PROFILE": "production"}):
                provider = ProfileFileConfigurationProvider(
                    "logging-config.yaml", plugin_module=mock_module
                )

                config_yaml = provider.get_default_configuration()
                loaded_data = yaml.safe_load(config_yaml)
                assert loaded_data == config_data

    def test_provider_raises_error_when_file_not_found(self) -> None:
        """Test provider raises FileNotFoundError when file doesn't exist."""
        from paise2.config.providers import ProfileFileConfigurationProvider

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create directory structure with missing config file:
            # temp_dir/
            #   base/
            #     logging.py (registration location)
            #   production/
            #     (no logging-config.yaml file)
            base_dir = Path(temp_dir) / "base"
            production_dir = Path(temp_dir) / "production"
            base_dir.mkdir()
            production_dir.mkdir()

            # Create a mock module in the base directory
            import types

            mock_module = types.ModuleType("mock_module")
            mock_module.__file__ = str(base_dir / "logging.py")

            # Test with PAISE2_PROFILE=production and missing file
            with patch.dict(os.environ, {"PAISE2_PROFILE": "production"}):
                provider = ProfileFileConfigurationProvider(
                    "logging-config.yaml", plugin_module=mock_module
                )

                with pytest.raises(
                    FileNotFoundError, match="Configuration file not found"
                ):
                    provider.get_default_configuration()

    def test_provider_uses_development_as_default_profile(self) -> None:
        """Test provider defaults to development when PAISE2_PROFILE not set."""
        from paise2.config.providers import ProfileFileConfigurationProvider

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create directory structure:
            # temp_dir/
            #   base/
            #     logging.py (registration location)
            #   development/
            #     logging-config.yaml (target file)
            base_dir = Path(temp_dir) / "base"
            development_dir = Path(temp_dir) / "development"
            base_dir.mkdir()
            development_dir.mkdir()

            # Create the configuration file in development
            config_file = development_dir / "logging-config.yaml"
            config_data = {"logging": {"level": "DEBUG"}}
            with config_file.open("w") as f:
                yaml.dump(config_data, f)

            # Create a mock module in the base directory
            import types

            mock_module = types.ModuleType("mock_module")
            mock_module.__file__ = str(base_dir / "logging.py")

            # Test without PAISE2_PROFILE set (should default to development)
            with patch.dict(os.environ, {}, clear=True):
                provider = ProfileFileConfigurationProvider(
                    "logging-config.yaml", plugin_module=mock_module
                )

                config_yaml = provider.get_default_configuration()
                loaded_data = yaml.safe_load(config_yaml)
                assert loaded_data == config_data

    def test_provider_generates_correct_config_id(self) -> None:
        """Test provider generates configuration ID from filename."""
        from paise2.config.providers import ProfileFileConfigurationProvider

        provider = ProfileFileConfigurationProvider("my-config.yaml")
        assert provider.get_configuration_id() == "my-config"

    def test_provider_with_custom_config_id(self) -> None:
        """Test provider accepts custom configuration ID."""
        from paise2.config.providers import ProfileFileConfigurationProvider

        provider = ProfileFileConfigurationProvider(
            "my-config.yaml", config_id="custom_id"
        )
        assert provider.get_configuration_id() == "custom_id"

    def test_provider_requires_plugin_module_for_relative_resolution(self) -> None:
        """Test provider requires plugin_module for relative path resolution."""
        from paise2.config.providers import ProfileFileConfigurationProvider

        # Test without PAISE2_PROFILE set and without plugin_module
        with patch.dict(os.environ, {}, clear=True):
            provider = ProfileFileConfigurationProvider("logging-config.yaml")

            with pytest.raises(ValueError, match="plugin_module is required"):
                provider.get_default_configuration()

    def test_provider_with_absolute_file_path(self) -> None:
        """Test provider works with absolute file paths without plugin_module."""
        from paise2.config.providers import ProfileFileConfigurationProvider

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create absolute path to config file
            config_file = Path(temp_dir) / "absolute-config.yaml"
            config_data = {"test": "absolute_path"}
            with config_file.open("w") as f:
                yaml.dump(config_data, f)

            provider = ProfileFileConfigurationProvider(str(config_file))
            config_yaml = provider.get_default_configuration()
            loaded_data = yaml.safe_load(config_yaml)
            assert loaded_data == config_data
