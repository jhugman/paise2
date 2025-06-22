# ABOUTME: Core CLI commands plugin for PAISE2
# ABOUTME: Implements the run, status, validate, and version commands

from __future__ import annotations

import sys
from typing import Any

import click
from rich.console import Console

from paise2.plugins.core.registry import hookimpl


def setup_logging(log_level: str) -> None:
    """Set up logging configuration."""
    import logging

    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _create_validate_command() -> Any:
    """Create the validate command."""

    @click.command()
    def validate() -> None:
        """Validate the PAISE2 system configuration and plugins.

        Performs a dry-run validation of the system without starting it.
        Useful for checking configuration and plugin compatibility.
        """
        from paise2.cli import get_plugin_manager
        from paise2.main import Application

        console = Console()

        try:
            console.print("[bold blue]Validating PAISE2 system")

            # Create and start application with the plugin manager
            app = Application(plugin_manager=get_plugin_manager())
            with app:
                singletons = app.get_singletons()

                # Quick validation checks
                checks = [
                    ("Configuration", singletons.configuration is not None),
                    ("Plugin Manager", singletons.plugin_manager is not None),
                    ("Logger", singletons.logger is not None),
                    ("State Storage", singletons.state_storage is not None),
                    ("Cache", singletons.cache is not None),
                    ("Data Storage", singletons.data_storage is not None),
                ]

                all_passed = True
                for check_name, passed in checks:
                    status = "✓" if passed else "✗"
                    color = "green" if passed else "red"
                    console.print(f"  {status} {check_name}", style=color)
                    if not passed:
                        all_passed = False

                if all_passed:
                    console.print("\n[bold green]✓ All validation checks passed!")
                else:
                    console.print("\n[bold red]✗ Some validation checks failed!")
                    sys.exit(1)

        except Exception as e:
            console.print(f"[bold red]Validation failed: {e}")
            sys.exit(1)

    return validate


@hookimpl
def register_commands(cli: click.Group) -> None:
    """Register core CLI commands with the main CLI group."""

    # Add all core commands to the CLI group
    cli.add_command(_create_validate_command())
