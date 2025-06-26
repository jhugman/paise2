# ABOUTME: Worker management CLI commands for PAISE2 background task processing
# ABOUTME: Provides start, stop, status commands for worker lifecycle management

from __future__ import annotations

import os
import signal
import sys
import time
from typing import TYPE_CHECKING, Any, NoReturn

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from paise2.plugins.core.registry import hookimpl

if TYPE_CHECKING:
    from paise2.plugins.core.startup import Singletons


def _create_worker_command_group() -> Any:
    """Create the worker command group with all subcommands."""

    @click.group()
    def worker() -> None:
        """Manage PAISE2 background workers.

        Background workers process tasks asynchronously for improved performance.
        Different profiles have different worker behavior:

        - Test profile: Uses immediate execution (no background workers)
        - Development profile: Optional background workers for debugging
        - Production profile: Full background worker support
        """

    worker.add_command(_create_start_command())
    worker.add_command(_create_stop_command())
    worker.add_command(_create_status_command())

    return worker


def _create_start_command() -> Any:
    """Create the start command."""

    @click.command()
    @click.option(
        "--concurrency",
        "-c",
        type=int,
        default=None,
        help="Number of worker processes (default: from configuration)",
    )
    @click.option(
        "--daemonize",
        "-d",
        is_flag=True,
        help="Run workers in background (future enhancement)",
    )
    def start(concurrency: int | None, daemonize: bool) -> None:
        """Start background workers to process tasks.

        Examples:
          paise2 worker start                    # Start with default concurrency
          paise2 worker start --concurrency 2   # Start with 2 workers
          paise2 worker start --daemonize        # Start in background (future)
        """
        _execute_start_command(concurrency, daemonize)

    return start


def _create_stop_command() -> Any:
    """Create the stop command."""

    @click.command()
    def stop() -> None:
        """Stop running background workers.

        Note: This is a basic implementation. Advanced process management
        with PID tracking will be added in future enhancements.
        """
        click.echo("Basic worker stop functionality.")
        click.echo(
            "For now, use Ctrl+C to stop workers running in foreground.\n"
            "Advanced PID-based worker management will be added in future versions."
        )

    return stop


def _create_status_command() -> Any:
    """Create the status command."""

    @click.command()
    @click.option(
        "--format",
        "-f",
        "output_format",
        type=click.Choice(["text", "json"]),
        default="text",
        help="Output format",
    )
    def status(output_format: str) -> None:
        """Show worker and task queue status.

        Examples:
          paise2 worker status            # Show status in readable format
          paise2 worker status --format json  # Show status as JSON
        """
        _execute_status_command(output_format)

    return status


def _execute_start_command(concurrency: int | None, daemonize: bool) -> None:
    """Execute the start command logic."""
    import logging

    logger = logging.getLogger(__name__)

    if daemonize:
        click.echo(
            "Warning: Daemonize option is not yet implemented. "
            "Workers will run in foreground."
        )

    from paise2.cli import get_plugin_manager
    from paise2.main import Application

    # Check profile compatibility
    profile = os.getenv("PAISE2_PROFILE", "development")
    if profile == "test":
        click.echo(
            "Test profile uses immediate task execution.\n"
            "Background workers are not needed in test mode.\n"
            "Tasks are executed synchronously for faster testing.",
            err=True,
        )
        sys.exit(1)

    click.echo(f"Starting PAISE2 workers (profile: {profile})...")

    try:
        # Create application with plugin manager
        app = Application(plugin_manager=get_plugin_manager())
        app.start_for_worker()

        singletons = app.get_singletons()

        # Get the Huey instance from task queue
        if not hasattr(singletons, "task_queue") or singletons.task_queue is None:
            click.echo("Error: Task queue not available", err=True)
            sys.exit(1)

        huey = singletons.task_queue.huey

        # Get concurrency from configuration if not specified
        if concurrency is None:
            config_value = singletons.configuration.get("worker.concurrency", 4)
            if isinstance(config_value, (int, str)):
                concurrency = int(config_value)
            else:
                concurrency = 4

        click.echo(f"Starting {concurrency} worker(s)...")

        # Set profile environment variable for worker processes
        os.environ["PAISE2_PROFILE"] = profile

        # Create and configure consumer
        consumer: Any = huey.create_consumer(workers=concurrency)

        # Set up signal handlers for graceful shutdown
        def signal_handler(signum: int, frame: Any) -> NoReturn:  # noqa: ARG001
            logger.info("Received signal %d, shutting down workers...", signum)
            click.echo("\nShutting down workers gracefully...")
            try:
                if hasattr(consumer, "shutdown"):
                    consumer.shutdown()
                else:
                    # Fallback for consumers without shutdown method
                    consumer.stop()
                click.echo("Workers stopped.")
            except Exception:
                logger.exception("Error during worker shutdown")
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        click.echo("Workers started successfully. Press Ctrl+C to stop.")

        # Run the consumer (this blocks until interrupted)
        consumer.run()

    except Exception as e:
        logger.exception("Error starting workers")
        click.echo(f"Error starting workers: {e}", err=True)
        sys.exit(1)


def _execute_status_command(output_format: str) -> None:
    """Execute the status command logic."""
    import logging

    logger = logging.getLogger(__name__)

    from paise2.cli import get_plugin_manager
    from paise2.main import Application

    try:
        # Create application with plugin manager
        app = Application(plugin_manager=get_plugin_manager())
        app.start_for_worker()

        singletons = app.get_singletons()

        # Get worker status information
        worker_status = _get_worker_status(singletons)

        if output_format == "json":
            import json

            click.echo(json.dumps(worker_status, indent=2))
        else:
            _display_worker_status_rich(worker_status)

    except Exception as e:
        logger.exception("Error getting worker status")
        click.echo(f"Error getting worker status: {e}", err=True)
        sys.exit(1)


def _get_worker_status(singletons: Singletons) -> dict[str, Any]:
    """Get comprehensive worker and task queue status information."""
    import logging

    logger = logging.getLogger(__name__)
    profile = os.getenv("PAISE2_PROFILE", "development")

    status: dict[str, Any] = {
        "profile": profile,
        "timestamp": time.time(),
        "task_queue": {
            "available": False,
            "type": "unknown",
            "immediate_execution": True,
        },
        "workers": {
            "running": False,
            "count": 0,
            "status": "Not running",
        },
        "tasks": {
            "queue_depth": 0,
            "processing_rate": "N/A",
        },
    }

    # Check task queue availability
    if singletons.task_queue is not None:
        status["task_queue"]["available"] = True

        # Determine task queue type and behavior
        huey = singletons.task_queue.huey
        huey_type = type(huey).__name__
        status["task_queue"]["type"] = huey_type

        # Check if using immediate execution
        if hasattr(huey, "immediate") and huey.immediate:
            status["task_queue"]["immediate_execution"] = True
            status["workers"]["status"] = "Immediate execution (no workers needed)"
        else:
            status["task_queue"]["immediate_execution"] = False
            status["workers"]["status"] = "Background processing available"

            # For SQLite/Redis Huey, we could check queue depth
            # This is a placeholder for future enhancement
            try:
                # Basic queue length check (if available)
                if hasattr(huey, "pending_count"):
                    status["tasks"]["queue_depth"] = huey.pending_count()
                elif hasattr(huey, "pending"):
                    # Some Huey instances have a pending() method
                    pending_tasks = list(huey.pending())
                    status["tasks"]["queue_depth"] = len(pending_tasks)
            except Exception:
                # Queue depth unavailable - log but continue
                logger.debug("Could not determine queue depth")

    return status


def _display_worker_status_rich(status: dict[str, Any]) -> None:
    """Display worker status using Rich formatting."""
    console = Console()

    # Main header
    profile = status["profile"]
    title = Text(f"PAISE2 Worker Status (Profile: {profile})", style="bold blue")

    timestamp_str = time.strftime(
        "%Y-%m-%d %H:%M:%S", time.localtime(status["timestamp"])
    )
    header_text = f"{title}\nTimestamp: {timestamp_str}"
    console.print(Panel(header_text, style="blue"))

    # Task Queue Status
    task_queue_table = Table(title="Task Queue Status", show_header=True)
    task_queue_table.add_column("Property", style="cyan")
    task_queue_table.add_column("Value", style="white")

    tq = status["task_queue"]
    task_queue_table.add_row("Available", "✓" if tq["available"] else "✗")
    task_queue_table.add_row("Type", tq["type"])
    task_queue_table.add_row(
        "Immediate Execution", "✓" if tq["immediate_execution"] else "✗"
    )

    console.print(task_queue_table)

    # Worker Status
    worker_table = Table(title="Worker Status", show_header=True)
    worker_table.add_column("Property", style="cyan")
    worker_table.add_column("Value", style="white")

    workers = status["workers"]
    worker_table.add_row("Running", "✓" if workers["running"] else "✗")
    worker_table.add_row("Count", str(workers["count"]))
    worker_table.add_row("Status", workers["status"])

    console.print(worker_table)

    # Task Statistics
    tasks_table = Table(title="Task Statistics", show_header=True)
    tasks_table.add_column("Metric", style="cyan")
    tasks_table.add_column("Value", style="white")

    tasks = status["tasks"]
    tasks_table.add_row("Queue Depth", str(tasks["queue_depth"]))
    tasks_table.add_row("Processing Rate", str(tasks["processing_rate"]))

    console.print(tasks_table)

    # Profile-specific guidance
    _display_profile_guidance(console, profile)


def _display_profile_guidance(console: Console, profile: str) -> None:
    """Display profile-specific guidance."""
    if profile == "test":
        console.print(
            Panel(
                "Test profile uses immediate task execution.\n"
                "Background workers are not used in test mode.",
                title="Profile Information",
                style="yellow",
            )
        )
    elif profile == "development":
        console.print(
            Panel(
                "Development profile supports both immediate and background "
                "execution.\n"
                "Use 'paise2 worker start' to enable background processing.",
                title="Profile Information",
                style="green",
            )
        )
    elif profile == "production":
        console.print(
            Panel(
                "Production profile uses background workers for optimal performance.\n"
                "Workers should be running for proper task processing.",
                title="Profile Information",
                style="blue",
            )
        )


@hookimpl
def register_commands(cli: click.Group) -> None:
    """Register worker management commands with the main CLI group."""
    cli.add_command(_create_worker_command_group())
