# ABOUTME: Reset CLI commands for PAISE2
# ABOUTME: Implements reset command that calls all registered ResetAction plugins

from __future__ import annotations

import click
from rich.console import Console

from paise2.cli import get_plugin_manager
from paise2.main import Application
from paise2.plugins.core.registry import PluginManager, hookimpl
from paise2.plugins.core.startup import LifecycleHostImpl

console = Console()


class ResetCliPlugin:
    """CLI plugin for system reset commands."""

    def __init__(self, plugin_manager: PluginManager | None = None) -> None:
        """Initialize the reset CLI plugin."""
        self._plugin_manager = plugin_manager

    @hookimpl
    def register_commands(self, cli: click.Group) -> None:
        """Register reset command with the main CLI."""
        reset_command = self._create_reset_command()
        cli.add_command(reset_command)

    def _create_reset_command(self) -> click.Command:
        """Create the reset command."""

        @click.command()
        @click.option(
            "--hard",
            is_flag=True,
            help="Perform a hard reset (complete data clearing)",
        )
        def reset(hard: bool) -> None:
            """Reset system components.

            Calls all registered ResetAction plugins to reset various system
            components. Use --hard for complete reset, otherwise performs
            soft reset.
            """
            self._execute_reset_command(hard)

        return reset

    def _execute_reset_command(self, hard: bool) -> None:
        """Implementation of reset command."""
        try:
            # Get plugin manager and initialize system
            plugin_manager = self._plugin_manager or get_plugin_manager()

            # Initialize the system to get singletons and proper configuration
            app = Application(plugin_manager=plugin_manager)
            app.start_for_worker()
            singletons = app.get_singletons()

            # Get all registered reset actions
            reset_actions = plugin_manager.get_reset_actions()

            if not reset_actions:
                console.print("[yellow]No reset actions registered.[/yellow]")
                return

            # Create lifecycle host for reset actions
            host = LifecycleHostImpl(singletons)
            configuration = singletons.configuration

            reset_type = "hard" if hard else "soft"
            console.print(f"[blue]Performing {reset_type} reset...[/blue]")

            # Execute reset actions
            for reset_action in reset_actions:
                action_name = type(reset_action).__name__
                try:
                    if hard:
                        reset_action.hard_reset(host, configuration)
                    else:
                        reset_action.soft_reset(host, configuration)
                    console.print(
                        f"[green]✓[/green] Reset action completed: {action_name}"
                    )
                except Exception as e:
                    console.print(
                        f"[red]✗[/red] Reset action failed: {action_name}: {e}"
                    )
                    # Continue with other reset actions even if one fails

            console.print(f"[green]Reset ({reset_type}) completed.[/green]")

        except Exception as e:
            console.print(f"[red]Error during reset: {e}[/red]")
            raise click.Abort from e
