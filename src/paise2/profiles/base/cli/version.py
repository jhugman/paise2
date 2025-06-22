from __future__ import annotations

from typing import Any

import click
from rich.console import Console
from rich.panel import Panel

from paise2.plugins.core.registry import hookimpl


def _create_version_command() -> Any:
    """Create the version command."""

    @click.command()
    def version() -> None:
        """Show detailed version information."""
        console = Console()

        # Create a nice version display
        version_info = Panel.fit(
            "[bold blue]PAISE2[/bold blue] Content Indexing System\n"
            "[dim]Version:[/dim] [bold yellow]2.0.0[/bold yellow]\n"
            "[dim]Plugin Architecture:[/dim] [green]Complete[/green]\n"
            "[dim]Status:[/dim] [green]Production Ready[/green]",
            title="Version Information",
            border_style="blue",
        )

        console.print(version_info)

    return version


@hookimpl
def register_commands(cli: click.Group) -> None:
    """Register core CLI commands with the main CLI group."""

    # Add all core commands to the CLI group)
    cli.add_command(_create_version_command())
