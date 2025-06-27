from __future__ import annotations

import signal
import sys
import time
from typing import Any, NoReturn

import click

from paise2.plugins.core.registry import hookimpl


def _create_run_command() -> Any:
    """Create the run command."""
    import logging

    logger = logging.getLogger(__name__)

    @click.command()
    def run() -> None:
        """Start the PAISE2 content indexing system.

        Examples:
          PAISE2_PROFILE=development paise2 run
                                                # Start with development profile
          PAISE_CONFIG_DIR=~/.config/paise2/ paise2 run
                                                # Start with custom configuration
        """
        from paise2.cli import get_plugin_manager
        from paise2.main import Application

        # Create and start application with the plugin manager
        plugin_manager = get_plugin_manager()

        app = Application(plugin_manager=plugin_manager)

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

    return run


@hookimpl
def register_commands(cli: click.Group) -> None:
    """Register core CLI commands with the main CLI group."""

    # Add all core commands to the CLI group
    cli.add_command(_create_run_command())
