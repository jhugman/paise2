# ABOUTME: Command-line interface for PAISE2 system operations and management
# ABOUTME: Provides CLI commands for starting, stopping, monitoring, and managing

from __future__ import annotations

import json
import logging
import signal
import sys
import time
from pathlib import Path
from typing import Any, NoReturn

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from paise2.main import Application

__all__ = ["main"]

logger = logging.getLogger(__name__)


def setup_logging(log_level: str) -> None:
    """Set up logging configuration."""
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


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


def load_config_from_file(config_path: Path) -> dict[str, Any]:
    """Load configuration from a JSON file."""
    try:
        with config_path.open() as f:
            return json.load(f)  # type: ignore[no-any-return]
    except FileNotFoundError:
        logger.exception("Configuration file not found: %s", config_path)
        sys.exit(1)
    except json.JSONDecodeError:
        logger.exception("Invalid JSON in configuration file")
        sys.exit(1)


@click.group()
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
    default="INFO",
    help="Set logging level (default: INFO)",
)
@click.version_option(version="2.0.0", prog_name="paise2")
def cli(log_level: str) -> None:
    """PAISE2 Content Indexing System.

    A desktop search engine indexer with extensible plugin system.
    """
    setup_logging(log_level.upper())


@cli.command()
@click.option(
    "--profile",
    type=click.Choice(["test", "development", "production"], case_sensitive=False),
    default="development",
    help="Profile to use (default: development)",
)
@click.option(
    "--config",
    type=click.Path(exists=True, path_type=Path),
    help="Path to custom configuration file (JSON)",
)
def run(profile: str, config: Path | None) -> None:
    """Start the PAISE2 content indexing system.

    Examples:
      paise2 run --profile development     # Start with development profile
      paise2 run --config config.json     # Start with custom configuration
    """
    # Load custom configuration if provided
    user_config = None
    if config:
        user_config = load_config_from_file(config)

    logger.info("Starting PAISE2 with profile: %s", profile)
    if user_config:
        logger.info("Using custom configuration from: %s", config)

    # Create and start application
    app = Application(profile=profile, user_config=user_config)

    # Set up signal handlers for graceful shutdown
    def signal_handler(signum: int, frame: Any) -> NoReturn:  # noqa: ARG001
        logger.info("Received signal %d, shutting down gracefully...", signum)
        try:
            app.stop()
            logger.info("Shutdown complete.")
        except Exception:
            logger.exception("Error during shutdown")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        with app:
            logger.info("System started successfully. Press Ctrl+C to stop.")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Shutting down...")
    except Exception:
        logger.exception("Error starting system")
        sys.exit(1)


@cli.command()
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
    try:
        from paise2.monitoring import SystemHealthMonitor

        app = Application(profile="test")
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


@cli.command()
@click.option(
    "--profile",
    type=click.Choice(["test", "development", "production"], case_sensitive=False),
    default="test",
    help="Profile to validate (default: test)",
)
def validate(profile: str) -> None:
    """Validate the PAISE2 system configuration and plugins.

    Performs a dry-run validation of the system without starting it.
    Useful for checking configuration and plugin compatibility.
    """
    console = Console()

    try:
        console.print(f"[bold blue]Validating PAISE2 system with profile: {profile}")

        app = Application(profile=profile)
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


@cli.command()
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


def main() -> None:
    """Main CLI entry point."""
    cli()


if __name__ == "__main__":
    main()
