# ABOUTME: Command-line interface for PAISE2 system operations and management
# ABOUTME: Provides CLI commands for starting, stopping, monitoring, and managing

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from paise2.plugins.core.registry import PluginManager

__all__ = ["get_plugin_manager", "main"]

logger = logging.getLogger(__name__)

# Global plugin manager instance available to all CLI commands
_plugin_manager: PluginManager | None = None


def _set_plugin_manager(manager: PluginManager) -> None:
    """Set the global plugin manager instance."""
    global _plugin_manager  # noqa: PLW0603
    _plugin_manager = manager


def get_plugin_manager() -> PluginManager:
    """Get the global plugin manager instance."""
    if _plugin_manager is None:
        msg = (
            "Plugin manager not initialized. "
            "This should not happen in normal CLI usage."
        )
        raise RuntimeError(msg)
    return _plugin_manager


def setup_logging(log_level: str) -> None:
    """Set up logging configuration."""
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


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


def main() -> None:
    """Main CLI entry point."""
    # Initialize plugin manager from environment variable
    try:
        from paise2.profiles.factory import create_plugin_manager_from_env

        # Create plugin manager based on PAISE2_PROFILE environment variable
        # Factory handles discovery of both base and profile-specific plugins
        plugin_manager = create_plugin_manager_from_env()
        # This loads plugins which are specific to the "app", but not the worker.
        plugin_manager.discover_internal_profile_plugins("app")
        plugin_manager.discover_plugins()

        # Set global plugin manager for CLI commands to use
        _set_plugin_manager(plugin_manager)

        # Load discovered plugins and register CLI commands
        plugin_manager.load_plugins()
        plugin_manager.load_cli_commands(cli)
    except Exception as e:
        # Log plugin loading errors but don't fail CLI startup
        logger.debug("Failed to load plugin system: %s", e)

    cli()


if __name__ == "__main__":
    main()
