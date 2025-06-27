# ABOUTME: Unit tests for configuration CLI plugin commands
# ABOUTME: Tests config edit, list, reset, and show commands with proper TDD coverage

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import click
import yaml
from click.testing import CliRunner

from paise2.constants import PAISE_CONFIG_DIR_ENV
from paise2.plugins.cli.config_commands import ConfigCliPlugin
from paise2.plugins.core.interfaces import ConfigurationProvider
from paise2.plugins.core.registry import PluginManager


class MockConfigProvider(ConfigurationProvider):
    """Mock configuration provider for testing."""

    def __init__(self, config_yaml: str, config_id: str = "test_config") -> None:
        self._config_yaml = config_yaml
        self._config_id = config_id

    def get_default_configuration(self) -> str:
        return self._config_yaml

    def get_configuration_id(self) -> str:
        return self._config_id


class TestConfigCliPlugin:
    """Test configuration CLI plugin commands."""

    def setup_method(self) -> None:
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_env = os.environ.get(PAISE_CONFIG_DIR_ENV)
        os.environ[PAISE_CONFIG_DIR_ENV] = self.temp_dir

        # Set up plugin manager with test providers
        self.plugin_manager = PluginManager()
        self.plugin_manager.register_configuration_provider(
            MockConfigProvider(
                "content_fetcher:\n  max_size: 1048576\n  timeout: 30",
                "content_fetcher",
            )
        )
        self.plugin_manager.register_configuration_provider(
            MockConfigProvider(
                "data_storage:\n  sqlite:\n    path: ~/.local/share/paise/content.db",
                "data_storage",
            )
        )

        # Create the CLI plugin instance
        self.cli_plugin = ConfigCliPlugin(self.plugin_manager)

        # Create a test CLI group and register commands
        self.test_cli = click.Group()
        self.cli_plugin.register_commands(self.test_cli)

        self.runner = CliRunner()

    def teardown_method(self) -> None:
        """Clean up test environment."""
        if self.original_env:
            os.environ[PAISE_CONFIG_DIR_ENV] = self.original_env
        else:
            os.environ.pop(PAISE_CONFIG_DIR_ENV, None)

        # Clean up temp directory
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_config_list_command_with_providers(self) -> None:
        """Test config list command shows available configuration providers."""
        result = self.runner.invoke(self.test_cli, ["config", "list"])

        assert result.exit_code == 0
        assert "content_fetcher" in result.output
        assert "data_storage" in result.output

    def test_config_list_command_json_format(self) -> None:
        """Test config list command with JSON output."""
        # Create an override file to test the has_override detection
        override_file = Path(self.temp_dir) / "content_fetcher.yaml"
        override_file.write_text("content_fetcher:\n  max_size: 2097152")

        result = self.runner.invoke(self.test_cli, ["config", "list", "--json"])

        assert result.exit_code == 0
        output_data = yaml.safe_load(result.output)
        assert "configurations" in output_data
        assert len(output_data["configurations"]) == 2

        # Find content_fetcher config
        content_fetcher_config = next(
            c for c in output_data["configurations"] if c["id"] == "content_fetcher"
        )
        assert content_fetcher_config["has_override"] is True

    def test_config_list_command_no_providers(self) -> None:
        """Test config list command with no configuration providers."""
        empty_plugin_manager = PluginManager()
        empty_cli_plugin = ConfigCliPlugin(empty_plugin_manager)
        empty_test_cli = click.Group()
        empty_cli_plugin.register_commands(empty_test_cli)

        result = self.runner.invoke(empty_test_cli, ["config", "list"])

        assert result.exit_code == 0
        assert result.output.strip() == ""

    def test_config_list_command_no_providers_json(self) -> None:
        """Test config list command with no providers in JSON format."""
        empty_plugin_manager = PluginManager()
        empty_cli_plugin = ConfigCliPlugin(empty_plugin_manager)
        empty_test_cli = click.Group()
        empty_cli_plugin.register_commands(empty_test_cli)

        result = self.runner.invoke(empty_test_cli, ["config", "list", "--json"])

        assert result.exit_code == 0
        output_data = yaml.safe_load(result.output)
        assert output_data == {"configurations": []}

    def test_config_show_command_all_configs(self) -> None:
        """Test config show command displays all merged configurations."""
        result = self.runner.invoke(self.test_cli, ["config", "show"])

        assert result.exit_code == 0
        # Should contain merged configuration from both providers
        assert "content_fetcher:" in result.output
        assert "data_storage:" in result.output
        assert "max_size: 1048576" in result.output

    def test_config_show_command_specific_configs(self) -> None:
        """Test config show command with specific config IDs."""
        result = self.runner.invoke(
            self.test_cli, ["config", "show", "content_fetcher"]
        )

        assert result.exit_code == 0
        assert "content_fetcher:" in result.output
        assert "max_size: 1048576" in result.output
        # Should not contain other configs
        assert "data_storage:" not in result.output

    def test_config_show_command_nonexistent_config(self) -> None:
        """Test config show command with nonexistent config ID."""
        result = self.runner.invoke(
            self.test_cli, ["config", "show", "nonexistent_config"]
        )

        assert result.exit_code != 0
        assert "Configuration ID 'nonexistent_config' not found" in result.output

    @patch("editor.editor")
    def test_config_edit_command_existing_file(self, mock_edit: Mock) -> None:
        """Test config edit command opens existing override file."""
        # Create an existing override file
        override_file = Path(self.temp_dir) / "content_fetcher.yaml"
        override_file.write_text("content_fetcher:\n  max_size: 2097152")

        result = self.runner.invoke(
            self.test_cli, ["config", "edit", "content_fetcher"]
        )

        assert result.exit_code == 0
        mock_edit.assert_called_once_with(filename=str(override_file))

    @patch("editor.editor")
    def test_config_edit_command_create_new_file(self, mock_edit: Mock) -> None:
        """Test config edit command creates new file from default config."""
        result = self.runner.invoke(
            self.test_cli, ["config", "edit", "content_fetcher"]
        )

        assert result.exit_code == 0

        # Should create new file with default configuration
        override_file = Path(self.temp_dir) / "content_fetcher.yaml"
        assert override_file.exists()

        # Should contain the default configuration
        content = override_file.read_text()
        assert "content_fetcher:" in content
        assert "max_size: 1048576" in content

        mock_edit.assert_called_once_with(filename=str(override_file))

    def test_config_edit_command_nonexistent_provider(self) -> None:
        """Test config edit command with nonexistent configuration provider."""
        result = self.runner.invoke(
            self.test_cli, ["config", "edit", "nonexistent_config"]
        )

        assert result.exit_code != 0
        assert "Configuration provider 'nonexistent_config' not found" in result.output
        expected_path = str(Path(self.temp_dir) / "nonexistent_config.yaml")
        assert expected_path in result.output

    def test_config_reset_command_specific_config(self) -> None:
        """Test config reset command deletes specific override file."""
        # Create an override file
        override_file = Path(self.temp_dir) / "content_fetcher.yaml"
        override_file.write_text("content_fetcher:\n  max_size: 2097152")

        result = self.runner.invoke(
            self.test_cli, ["config", "reset", "content_fetcher"]
        )

        assert result.exit_code == 0
        assert not override_file.exists()
        assert "Reset configuration for 'content_fetcher'" in result.output

    def test_config_reset_command_nonexistent_file(self) -> None:
        """Test config reset command with nonexistent override file."""
        result = self.runner.invoke(
            self.test_cli, ["config", "reset", "content_fetcher"]
        )

        assert result.exit_code == 0
        assert "No override file found for 'content_fetcher'" in result.output

    def test_config_reset_command_nonexistent_provider(self) -> None:
        """Test config reset command with nonexistent configuration provider."""
        result = self.runner.invoke(
            self.test_cli, ["config", "reset", "nonexistent_config"]
        )

        assert result.exit_code != 0
        assert "Configuration ID 'nonexistent_config' not found" in result.output

    def test_config_reset_command_all_configs(self) -> None:
        """Test config reset command with --all flag."""
        # Create multiple override files
        override1 = Path(self.temp_dir) / "content_fetcher.yaml"
        override2 = Path(self.temp_dir) / "data_storage.yaml"
        random_file = Path(self.temp_dir) / "not_config.txt"

        override1.write_text("content_fetcher:\n  max_size: 2097152")
        override2.write_text("data_storage:\n  path: /custom/path")
        random_file.write_text("should not be deleted")

        result = self.runner.invoke(self.test_cli, ["config", "reset", "--all"])

        assert result.exit_code == 0
        assert not override1.exists()
        assert not override2.exists()
        assert random_file.exists()  # Should not delete non-YAML files
        assert "Reset all configuration overrides" in result.output

    def test_config_reset_command_all_no_files(self) -> None:
        """Test config reset command with --all flag when no override files exist."""
        result = self.runner.invoke(self.test_cli, ["config", "reset", "--all"])

        assert result.exit_code == 0
        assert "No configuration override files found" in result.output
