# ABOUTME: Example plugin demonstrating CLI command registration extension point
# ABOUTME: Shows how plugins can add new commands to the PAISE2 CLI

from __future__ import annotations

import click

from paise2.plugins.core.registry import hookimpl


@hookimpl
def register_commands(cli: click.Group) -> None:
    """Register CLI commands with the main CLI group."""

    @cli.command(name="example-hello")
    @click.option("--name", default="World", help="Name to greet")
    @click.option("--verbose", is_flag=True, help="Enable verbose output")
    def hello_command(name: str, verbose: bool) -> None:
        """Say hello from the example plugin."""
        if verbose:
            click.echo(f"Verbose: Executing hello command with name='{name}'")
        click.echo(f"Hello, {name}! This is from the example CLI plugin.")

    @cli.group(name="example")
    def example_group() -> None:
        """Example plugin commands."""

    @example_group.command(name="status")
    @click.option(
        "--format", "output_format", type=click.Choice(["text", "json"]), default="text"
    )
    def status_command(output_format: str) -> None:
        """Show example plugin status."""
        if output_format == "json":
            import json

            click.echo(json.dumps({"status": "active", "plugin": "example"}))
        else:
            click.echo("Example plugin status: active")

    @example_group.command(name="info")
    def info_command() -> None:
        """Show information about the example plugin."""
        click.echo("Example CLI Plugin v1.0")
        click.echo("Demonstrates CLI extension point capabilities")
        click.echo("Available commands:")
        click.echo("  - paise2 example-hello: Simple greeting command")
        click.echo("  - paise2 example status: Show plugin status")
        click.echo("  - paise2 example info: Show plugin information")

        # Demonstrate accessing the plugin manager from CLI commands
        try:
            from paise2.cli import get_plugin_manager

            plugin_manager = get_plugin_manager()
            click.echo(f"Plugin manager type: {type(plugin_manager).__name__}")
        except RuntimeError:
            click.echo("Plugin manager not available in test context")
        click.echo("  - paise2 example info: Show this information")
