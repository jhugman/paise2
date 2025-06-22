# ABOUTME: Tests for CLI command registration extension point
# ABOUTME: Validates that plugins can extend the CLI with new commands

import click
from click.testing import CliRunner

from paise2.plugins.core.registry import PluginManager


def test_register_commands_hook_spec_exists() -> None:
    """Test that the register_commands hook specification exists."""
    plugin_manager = PluginManager()
    assert hasattr(plugin_manager.pm.hook, "register_commands")


def test_cli_command_registration() -> None:
    """Test that plugins can register CLI commands."""
    plugin_manager = PluginManager()

    # Create a fresh CLI group for this test
    @click.group()
    def test_cli() -> None:
        """Test CLI for plugin command registration."""

    # Register the example plugin module directly
    import tests.fixtures.cli.example_cli_plugin

    plugin_manager.pm.register(tests.fixtures.cli.example_cli_plugin)

    # Load CLI commands into the test CLI group
    plugin_manager.load_cli_commands(test_cli)

    # Test that the commands were registered
    runner = CliRunner()

    # Test the simple hello command
    result = runner.invoke(test_cli, ["example-hello", "--name", "Test"])
    assert result.exit_code == 0
    assert "Hello, Test!" in result.output
    assert "example CLI plugin" in result.output

    # Test verbose flag
    result = runner.invoke(test_cli, ["example-hello", "--verbose"])
    assert result.exit_code == 0
    assert "Verbose:" in result.output
    assert "Hello, World!" in result.output


def test_cli_registration() -> None:
    """Test that plugins can register CLI command groups."""
    plugin_manager = PluginManager()

    # Create a fresh CLI group for this test
    @click.group()
    def test_cli() -> None:
        """Test CLI for plugin group registration."""

    # Register the example plugin module directly
    import tests.fixtures.cli.example_cli_plugin

    plugin_manager.pm.register(tests.fixtures.cli.example_cli_plugin)

    # Load CLI commands into the test CLI group
    plugin_manager.load_cli_commands(test_cli)

    runner = CliRunner()

    # Test the group status command
    result = runner.invoke(test_cli, ["example", "status"])
    assert result.exit_code == 0
    assert "Example plugin status: active" in result.output

    # Test status command with JSON format
    result = runner.invoke(test_cli, ["example", "status", "--format", "json"])
    assert result.exit_code == 0
    assert '"status": "active"' in result.output
    assert '"plugin": "example"' in result.output

    # Test the info command
    result = runner.invoke(test_cli, ["example", "info"])
    assert result.exit_code == 0
    assert "Example CLI Plugin v1.0" in result.output
    assert "Available commands:" in result.output
    # In test context, plugin manager is not available globally
    assert "Plugin manager not available in test context" in result.output


def test_cli_help_includes_plugin_commands() -> None:
    """Test that plugin commands appear in CLI help."""
    plugin_manager = PluginManager()

    # Create a fresh CLI group for this test
    @click.group()
    def test_cli() -> None:
        """Test CLI for plugin help."""

    # Register the example plugin module directly
    import tests.fixtures.cli.example_cli_plugin

    plugin_manager.pm.register(tests.fixtures.cli.example_cli_plugin)

    # Load CLI commands into the test CLI group
    plugin_manager.load_cli_commands(test_cli)

    runner = CliRunner()

    # Test main help includes plugin commands
    result = runner.invoke(test_cli, ["--help"])
    assert result.exit_code == 0
    assert "example-hello" in result.output
    assert "example" in result.output

    # Test group help
    result = runner.invoke(test_cli, ["example", "--help"])
    assert result.exit_code == 0
    assert "status" in result.output
    assert "info" in result.output


def test_multiple_plugins_can_register_commands() -> None:
    """Test that multiple plugins can register different commands."""
    plugin_manager = PluginManager()

    # Create a fresh CLI group for this test
    @click.group()
    def test_cli() -> None:
        """Test CLI for multiple plugins."""

    # Register both plugin modules
    import tests.fixtures.cli.example_cli_plugin
    import tests.fixtures.cli.second_cli_plugin

    plugin_manager.pm.register(tests.fixtures.cli.example_cli_plugin)
    plugin_manager.pm.register(tests.fixtures.cli.second_cli_plugin)

    # Load CLI commands into the test CLI group
    plugin_manager.load_cli_commands(test_cli)

    runner = CliRunner()

    # Test first plugin command
    result = runner.invoke(test_cli, ["example-hello"])
    assert result.exit_code == 0
    assert "example CLI plugin" in result.output

    # Test second plugin command
    result = runner.invoke(test_cli, ["second-plugin-cmd"])
    assert result.exit_code == 0
    assert "Hello from second plugin!" in result.output

    # Test second plugin group command
    result = runner.invoke(test_cli, ["second", "test"])
    assert result.exit_code == 0
    assert "Test command from second plugin" in result.output
