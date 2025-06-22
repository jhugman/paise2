# ABOUTME: Second example plugin for testing multiple CLI command registration
# ABOUTME: Shows how multiple plugins can add different commands to the PAISE2 CLI

from __future__ import annotations

import click

from paise2.plugins.core.registry import hookimpl


@hookimpl
def register_commands(cli: click.Group) -> None:
    """Register second plugin CLI commands with the main CLI group."""

    @cli.command(name="second-plugin-cmd")
    def second_command() -> None:
        """Command from second plugin."""
        click.echo("Hello from second plugin!")

    @cli.group(name="second")
    def second_group() -> None:
        """Second plugin commands."""

    @second_group.command(name="test")
    def test_command() -> None:
        """Test command from second plugin."""
        click.echo("Test command from second plugin")
