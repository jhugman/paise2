from __future__ import annotations

import json
import sys
import time
from typing import Any

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from paise2.plugins.core.registry import hookimpl


def format_rich_status(health_report: Any) -> None:
    """Format health report using Rich for beautiful colored output."""
    console = Console()

    # Status color based on health
    status_color = {"healthy": "green", "degraded": "yellow", "unhealthy": "red"}.get(
        health_report.status.lower(), "white"
    )

    # Main header
    title = Text("PAISE2 System Health Report", style="bold blue")
    status_text = Text(
        f"Status: {health_report.status.upper()}", style=f"bold {status_color}"
    )

    # Create main info panel
    timestamp_str = time.strftime(
        "%Y-%m-%d %H:%M:%S", time.localtime(health_report.timestamp)
    )

    header_text = f"{title}\n{status_text}\nTimestamp: {timestamp_str}"
    console.print(Panel(header_text, style=status_color))

    # Components table
    table = Table(
        title="System Components", show_header=True, header_style="bold magenta"
    )
    table.add_column("Component", style="cyan", no_wrap=True)
    table.add_column("Status", justify="center")
    table.add_column("Details", style="dim")

    for component_name, component_info in health_report.components.items():
        component_status = component_info.get("status", "unknown")
        status_style = {
            "healthy": "green",
            "degraded": "yellow",
            "unhealthy": "red",
            "disabled": "dim",
        }.get(component_status, "white")

        # Format details
        details = []
        for key, value in component_info.items():
            if key != "status":
                details.append(f"{key}: {value}")
        details_str = ", ".join(details) if details else ""

        table.add_row(
            component_name.replace("_", " ").title(),
            Text(component_status.upper(), style=f"bold {status_style}"),
            details_str,
        )

    console.print(table)

    # Metrics table if available
    if health_report.metrics:
        metrics_table = Table(
            title="System Metrics", show_header=True, header_style="bold green"
        )
        metrics_table.add_column("Metric", style="cyan")
        metrics_table.add_column("Value", justify="right", style="yellow")

        for metric_name, metric_value in health_report.metrics.items():
            metrics_table.add_row(
                metric_name.replace("_", " ").title(), str(metric_value)
            )

        console.print(metrics_table)

    # Errors if any
    if health_report.errors:
        error_panel = Panel(
            "\n".join(health_report.errors), title="[bold red]Errors", style="red"
        )
        console.print(error_panel)


def _create_status_command() -> Any:
    """Create the status command."""

    @click.command()
    @click.option(
        "--format",
        "output_format",
        type=click.Choice(["text", "json"], case_sensitive=False),
        default="text",
        help="Output format (default: text)",
    )
    def status(output_format: str) -> None:
        """Check the current status of the PAISE2 system.

        Provides detailed health information about all system components
        including configuration, plugin manager, task queue, cache, and storage.
        """
        from paise2.main import Application

        try:
            from paise2.cli import get_plugin_manager
            from paise2.main import Application
            from paise2.monitoring import SystemHealthMonitor

            # Create and start application with the plugin manager
            app = Application(plugin_manager=get_plugin_manager())
            with app:
                singletons = app.get_singletons()

                # Use the comprehensive health monitoring system
                health_monitor = SystemHealthMonitor()
                health_report = health_monitor.check_system_health(singletons)

            if output_format == "json":
                formatted_report = health_monitor.format_health_report(
                    health_report, "json"
                )
                click.echo(formatted_report)
            else:
                # Use rich formatting for text output
                format_rich_status(health_report)

        except Exception as e:
            error_info = {
                "status": "error",
                "error": str(e),
                "timestamp": time.time(),
            }

            if output_format == "json":
                click.echo(json.dumps(error_info, indent=2))
            else:
                click.echo(f"Status: error - {e}", err=True)
                sys.exit(1)

    return status


@hookimpl
def register_commands(cli: click.Group) -> None:
    """Register core CLI commands with the main CLI group."""

    # Add all core commands to the CLI group
    cli.add_command(_create_status_command())
