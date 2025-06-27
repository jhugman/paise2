# ABOUTME: Unit tests for configuration system
# ABOUTME: Tests configuration loading, merging, and provider functionality

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

import pytest
import yaml

from paise2.config.diffing import ConcreteConfiguration
from paise2.config.models import Configuration
from paise2.constants import PAISE_CONFIG_DIR_ENV


class TestConfiguration(unittest.TestCase):
    """Test configuration protocol and implementation."""

    def test_configuration_protocol_compliance(self) -> None:
        """Test that Configuration protocol can be implemented."""
        config_data = {
            "plugin1": {"key1": "value1"},
            "plugin2": {"nested": {"key2": "value2"}},
        }
        config = ConcreteConfiguration(config_data)

        # Test protocol compliance
        assert isinstance(config, Configuration)  # Should not raise
        assert config.get("plugin1.key1") == "value1"
        assert config.get("plugin2.nested.key2") == "value2"
        assert config.get("nonexistent", "default") == "default"
        assert config.get_section("plugin1") == {"key1": "value1"}


class TestFileConfigurationProvider(unittest.TestCase):
    """Test file-based configuration provider."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = Path(self.temp_dir) / "test_config.yaml"
        self.config_data = {
            "plugin1": {"setting1": "value1", "setting2": ["item1", "item2"]},
            "plugin2": {"nested": {"key": "value"}},
        }

        # Write test configuration file
        with self.config_file.open("w") as f:
            yaml.dump(self.config_data, f)

    def tearDown(self) -> None:
        """Clean up test fixtures."""
        if self.config_file.exists():
            self.config_file.unlink()
        Path(self.temp_dir).rmdir()

    def test_file_configuration_provider_creation(self) -> None:
        """Test creating FileConfigurationProvider with file path."""
        from paise2.config.providers import FileConfigurationProvider

        provider = FileConfigurationProvider(str(self.config_file))
        assert provider.get_configuration_id() == "test_config"

    def test_file_configuration_provider_load_yaml(self) -> None:
        """Test loading YAML configuration from file."""
        from paise2.config.providers import FileConfigurationProvider

        provider = FileConfigurationProvider(str(self.config_file))
        config_yaml = provider.get_default_configuration()

        # Should load and return YAML string
        loaded_data = yaml.safe_load(config_yaml)
        assert loaded_data == self.config_data

    def test_file_configuration_provider_relative_path(self) -> None:
        """Test handling relative paths with plugin modules."""
        import paise2.config.models as test_module
        from paise2.config.providers import FileConfigurationProvider

        # Create config file relative to test module
        module_dir = Path(test_module.__file__).parent
        rel_config_file = module_dir / "test_relative.yaml"

        try:
            # Create relative config file
            with rel_config_file.open("w") as f:
                yaml.dump({"test": "relative"}, f)

            provider = FileConfigurationProvider("test_relative.yaml", test_module)
            config_yaml = provider.get_default_configuration()

            loaded_data = yaml.safe_load(config_yaml)
            assert loaded_data == {"test": "relative"}
        finally:
            if rel_config_file.exists():
                rel_config_file.unlink()

    def test_file_configuration_provider_missing_file(self) -> None:
        """Test handling missing configuration files."""
        from paise2.config.providers import FileConfigurationProvider

        provider = FileConfigurationProvider("/nonexistent/file.yaml")

        # Should handle missing files gracefully
        config_yaml = provider.get_default_configuration()
        assert config_yaml == ""  # Empty string for missing files


class TestConfigurationMerging(unittest.TestCase):
    """Test configuration merging logic."""

    def test_merge_scalar_values_last_wins(self) -> None:
        """Test that later plugin scalar values override earlier ones."""
        from paise2.config.manager import ConfigurationManager

        config1 = {"plugin1": {"setting": "value1"}}
        config2 = {"plugin1": {"setting": "value2"}}

        manager = ConfigurationManager()
        merged = manager.merge_plugin_configurations([config1, config2])

        assert merged["plugin1"]["setting"] == "value2"

    def test_merge_list_concatenation(self) -> None:
        """Test that lists are concatenated during merging."""
        from paise2.config.manager import ConfigurationManager

        config1 = {"plugin1": {"items": ["a", "b"]}}
        config2 = {"plugin1": {"items": ["c", "d"]}}

        manager = ConfigurationManager()
        merged = manager.merge_plugin_configurations([config1, config2])

        assert merged["plugin1"]["items"] == ["a", "b", "c", "d"]

    def test_merge_dict_recursive(self) -> None:
        """Test recursive dictionary merging."""
        from paise2.config.manager import ConfigurationManager

        config1 = {"plugin1": {"nested": {"key1": "value1"}}}
        config2 = {"plugin1": {"nested": {"key2": "value2"}}}

        manager = ConfigurationManager()
        merged = manager.merge_plugin_configurations([config1, config2])

        expected = {"plugin1": {"nested": {"key1": "value1", "key2": "value2"}}}
        assert merged == expected

    def test_user_config_overrides_plugin_config(self) -> None:
        """Test that user configuration completely overrides plugin defaults."""
        from paise2.config.manager import ConfigurationManager

        plugin_config = {"plugin1": {"setting": "plugin_value", "list": ["a", "b"]}}
        user_config = {"plugin1": {"setting": "user_value"}}

        manager = ConfigurationManager()
        merged = manager.merge_configurations(plugin_config, user_config)

        # User config should completely override plugin config for same keys
        assert merged["plugin1"]["setting"] == "user_value"
        # But non-overridden keys should remain
        assert merged["plugin1"]["list"] == ["a", "b"]

    def test_empty_configuration_handling(self) -> None:
        """Test handling of empty or None configurations."""
        from paise2.config.manager import ConfigurationManager

        manager = ConfigurationManager()

        # Empty list should return empty dict
        assert manager.merge_plugin_configurations([]) == {}

        # None values should be handled gracefully
        result = manager.merge_plugin_configurations([None, {"key": "value"}, None])
        assert result == {"key": "value"}


class TestConfigurationManager(unittest.TestCase):
    """Test the configuration manager implementation."""

    def setUp(self) -> None:
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_env = os.environ.get(PAISE_CONFIG_DIR_ENV)
        os.environ[PAISE_CONFIG_DIR_ENV] = self.temp_dir

    def tearDown(self) -> None:
        """Clean up test environment."""
        if self.original_env:
            os.environ[PAISE_CONFIG_DIR_ENV] = self.original_env
        else:
            del os.environ[PAISE_CONFIG_DIR_ENV]

        # Clean up temp directory
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_paise_config_dir_environment_variable(self) -> None:
        """Test that PAISE_CONFIG_DIR environment variable is respected."""
        from paise2.config.manager import ConfigurationManager

        # Create a config file in the temp directory
        config_file = Path(self.temp_dir) / "user_config.yaml"
        config_data = {"test": {"setting": "user_value"}}

        with config_file.open("w") as f:
            yaml.dump(config_data, f)

        manager = ConfigurationManager()
        # Test that it finds the config in PAISE_CONFIG_DIR
        # Implementation details will depend on actual ConfigurationManager interface
        assert manager.get_config_dir() == self.temp_dir

    def test_configuration_error_handling(self) -> None:
        """Test proper error handling for invalid YAML."""
        from paise2.config.manager import ConfigurationManager

        # Create invalid YAML file
        invalid_yaml_file = Path(self.temp_dir) / "invalid.yaml"
        with invalid_yaml_file.open("w") as f:
            f.write("invalid: yaml: content: [unclosed")

        manager = ConfigurationManager()

        # Should handle invalid YAML gracefully - using specific yaml.YAMLError
        with pytest.raises(yaml.YAMLError):
            manager.load_configuration_file(str(invalid_yaml_file))


if __name__ == "__main__":
    unittest.main()
