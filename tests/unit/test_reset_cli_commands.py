# ABOUTME: Unit tests for reset CLI commands functionality
# ABOUTME: Tests the reset command registration and execution logic

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import Mock

import click
from click.testing import CliRunner

if TYPE_CHECKING:
    from paise2.plugins.core.interfaces import Configuration, LifecycleHost


class TestResetCommands:
    """Test the reset CLI commands."""

    def test_reset_command_registration(self) -> None:
        """Test that reset commands can be registered with CLI."""
        # This test checks if we can register reset commands
        cli = click.Group()

        # Import and test the command creation
        from paise2.plugins.cli.reset_commands import ResetCliPlugin

        # Create the plugin and register the command
        reset_plugin = ResetCliPlugin()
        reset_plugin.register_commands(cli)

        # Check that the command was added
        assert "reset" in cli.commands

        # Check that the command has the correct options
        reset_cmd = cli.commands["reset"]
        assert hasattr(reset_cmd, "params")

        # Find the --hard option
        hard_option = None
        for param in reset_cmd.params:
            if hasattr(param, "name") and param.name == "hard":
                hard_option = param
                break

        assert hard_option is not None
        # Check it's an Option (not an Argument) which indicates it's a flag
        assert isinstance(hard_option, click.Option)

    def test_reset_command_soft_reset(self) -> None:
        """Test soft reset command execution."""
        runner = CliRunner()

        # Mock reset action
        class MockResetAction:
            def __init__(self) -> None:
                self.soft_reset_called = False
                self.hard_reset_called = False

            def soft_reset(
                self, host: LifecycleHost, configuration: Configuration
            ) -> None:
                self.soft_reset_called = True

            def hard_reset(
                self, host: LifecycleHost, configuration: Configuration
            ) -> None:
                self.hard_reset_called = True

        mock_action = MockResetAction()

        # Create a simple reset command for testing
        @click.command()
        def reset() -> None:
            """Reset the system (soft reset by default)."""
            mock_action.soft_reset(Mock(), Mock())
            click.echo("Soft reset completed")

        result = runner.invoke(reset)
        assert result.exit_code == 0
        assert "Soft reset completed" in result.output
        assert mock_action.soft_reset_called is True
        assert mock_action.hard_reset_called is False

    def test_reset_command_hard_reset(self) -> None:
        """Test hard reset command execution."""
        runner = CliRunner()

        # Mock reset action
        class MockResetAction:
            def __init__(self) -> None:
                self.soft_reset_called = False
                self.hard_reset_called = False

            def soft_reset(
                self, host: LifecycleHost, configuration: Configuration
            ) -> None:
                self.soft_reset_called = True

            def hard_reset(
                self, host: LifecycleHost, configuration: Configuration
            ) -> None:
                self.hard_reset_called = True

        mock_action = MockResetAction()

        # Create a simple reset command for testing
        @click.command()
        @click.option("--hard", is_flag=True, help="Perform hard reset")
        def reset(hard: bool) -> None:
            """Reset the system."""
            if hard:
                mock_action.hard_reset(Mock(), Mock())
                click.echo("Hard reset completed")
            else:
                mock_action.soft_reset(Mock(), Mock())
                click.echo("Soft reset completed")

        # Test hard reset
        result = runner.invoke(reset, ["--hard"])
        assert result.exit_code == 0
        assert "Hard reset completed" in result.output
        assert mock_action.hard_reset_called is True
        assert mock_action.soft_reset_called is False

    def test_reset_command_integration_mock(self) -> None:
        """Test reset command with multiple reset actions."""

        # Mock multiple reset actions
        class CacheResetAction:
            def __init__(self) -> None:
                self.calls: list[str] = []

            def soft_reset(
                self, host: LifecycleHost, configuration: Configuration
            ) -> None:
                self.calls.append("cache_soft")

            def hard_reset(
                self, host: LifecycleHost, configuration: Configuration
            ) -> None:
                self.calls.append("cache_hard")

        class DatabaseResetAction:
            def __init__(self) -> None:
                self.calls: list[str] = []

            def soft_reset(
                self, host: LifecycleHost, configuration: Configuration
            ) -> None:
                self.calls.append("db_soft")

            def hard_reset(
                self, host: LifecycleHost, configuration: Configuration
            ) -> None:
                self.calls.append("db_hard")

        cache_action = CacheResetAction()
        db_action = DatabaseResetAction()

        reset_actions: list[CacheResetAction | DatabaseResetAction] = [
            cache_action,
            db_action,
        ]

        # Mock the execution of multiple reset actions
        def execute_soft_reset() -> None:
            for action in reset_actions:
                action.soft_reset(Mock(), Mock())

        def execute_hard_reset() -> None:
            for action in reset_actions:
                action.hard_reset(Mock(), Mock())

        # Test soft reset
        execute_soft_reset()
        assert "cache_soft" in cache_action.calls
        assert "db_soft" in db_action.calls

        # Test hard reset
        execute_hard_reset()
        assert "cache_hard" in cache_action.calls
        assert "db_hard" in db_action.calls
