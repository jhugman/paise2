# ABOUTME: Configuration management CLI commands for PAISE2
# ABOUTME: Implements config edit, list, reset, and show commands with error handling

from __future__ import annotations

import json

import click
import editor
import yaml
from rich.console import Console
from rich.syntax import Syntax

from paise2.cli import get_plugin_manager
from paise2.config.factory import ConfigurationFactory
from paise2.plugins.core.registry import PluginManager, hookimpl

console = Console()


class ConfigCliPlugin:
    """CLI plugin for configuration management commands."""

    def __init__(self, plugin_manager: PluginManager | None = None) -> None:
        """Initialize the plugin with a plugin manager.

        Args:
            plugin_manager: The plugin manager instance to use for configuration
            operations.
        """
        self._plugin_manager = plugin_manager
        self._config_factory = ConfigurationFactory()

    def _get_plugin_manager(self) -> PluginManager:
        """Get the plugin manager, lazy-loading it if necessary."""
        if self._plugin_manager is None:
            self._plugin_manager = get_plugin_manager()
        return self._plugin_manager

    @hookimpl
    def register_commands(self, cli: click.Group) -> None:
        """Register configuration management commands with the main CLI."""
        # Create the config group with commands bound to this instance
        config_group = self._create_config_group()
        cli.add_command(config_group)

    def _create_config_group(self) -> click.Group:
        """Create the config command group with all subcommands."""

        @click.group()
        def config() -> None:
            """Manage PAISE2 configuration files and settings.

            Commands for viewing, editing, and managing configuration that combines
            plugin defaults with user overrides from $PAISE_CONFIG_DIR.
            """

        # Add subcommands to the group
        config.add_command(self._create_list_command())
        config.add_command(self._create_show_command())
        config.add_command(self._create_edit_command())
        config.add_command(self._create_reset_command())

        return config

    def _create_list_command(self) -> click.Command:
        """Create the list subcommand."""

        @click.command("list")
        @click.option(
            "--json",
            "output_json",
            is_flag=True,
            help="Output detailed information in JSON format",
        )
        def list_configs(output_json: bool) -> None:
            """List all available configuration provider IDs.

            Shows configuration IDs that can be edited, along with override status
            when using --json format.
            """
            self._list_configs_impl(output_json)

        return list_configs

    def _create_show_command(self) -> click.Command:
        """Create the show subcommand."""

        @click.command()
        @click.argument("config_ids", nargs=-1)
        def show(config_ids: tuple[str, ...]) -> None:
            """Show current merged configuration state.

            CONFIG_IDS: Optional list of configuration IDs to show.
            If none specified, shows all merged configuration.
            """
            self._show_configs_impl(config_ids)

        return show

    def _create_edit_command(self) -> click.Command:
        """Create the edit subcommand."""

        @click.command()
        @click.argument("config_id")
        def edit(config_id: str) -> None:
            """Open configuration file for editing.

            CONFIG_ID: The configuration ID to edit.

            If the override file exists, opens it directly.
            If not, copies the default configuration to the override file first.
            """
            self._edit_config_impl(config_id)

        return edit

    def _create_reset_command(self) -> click.Command:
        """Create the reset subcommand."""

        @click.command()
        @click.argument("config_id", required=False)
        @click.option(
            "--all",
            "reset_all",
            is_flag=True,
            help="Reset all configuration override files",
        )
        def reset(config_id: str | None, reset_all: bool) -> None:
            """Delete user configuration override files.

            CONFIG_ID: The configuration ID to reset.
            Use --all to reset all override files.
            """
            self._reset_config_impl(config_id, reset_all)

        return reset

    def _list_configs_impl(self, output_json: bool) -> None:
        """Implementation of config list command."""
        try:
            configs = self._config_factory.list_configurations(
                self._get_plugin_manager(), include_details=output_json
            )

            if not configs:
                if output_json:
                    click.echo(json.dumps({"configurations": []}, indent=2))
                return

            if output_json:
                click.echo(json.dumps({"configurations": configs}, indent=2))
            else:
                for config_id in configs:
                    click.echo(config_id)

        except Exception as e:
            click.echo(f"Error listing configurations: {e}", err=True)
            raise click.Abort from e

    def _show_configs_impl(self, config_ids: tuple[str, ...]) -> None:
        """Implementation of config show command."""
        try:
            config_data = self._config_factory.show_configurations(
                self._get_plugin_manager(), list(config_ids) if config_ids else None
            )

            if config_data:
                self._print_yaml_with_syntax(config_data)
            else:
                click.echo("No configuration data found.")

        except ValueError as e:
            click.echo(f"Error: {e}", err=True)
            raise click.Abort from e
        except Exception as e:
            click.echo(f"Error showing configuration: {e}", err=True)
            raise click.Abort from e

    def _edit_config_impl(self, config_id: str) -> None:
        """Implementation of config edit command."""
        try:
            override_file, was_created = (
                self._config_factory.prepare_config_for_editing(
                    self._get_plugin_manager(), config_id
                )
            )

            if was_created:
                click.echo(f"Created new configuration file: {override_file}")

            # Open editor
            editor.editor(filename=str(override_file))

        except ValueError as e:
            click.echo(f"Error: {e}", err=True)
            raise click.Abort from e
        except Exception as e:
            click.echo(f"Error editing configuration: {e}", err=True)
            raise click.Abort from e

    def _reset_config_impl(self, config_id: str | None, reset_all: bool) -> None:
        """Implementation of config reset command."""
        try:
            deleted_files = self._config_factory.reset_configurations(
                self._get_plugin_manager(), config_id, reset_all
            )

            if not deleted_files:
                if reset_all:
                    click.echo("No configuration override files found.")
                else:
                    click.echo(
                        f"No override file found for '{config_id}' (already at default)"
                    )
                return

            if reset_all:
                for filename in deleted_files:
                    click.echo(f"Deleted: {filename}")
                click.echo(
                    f"Reset all configuration overrides ({len(deleted_files)} files)"
                )
            else:
                click.echo(f"Reset configuration for '{config_id}'")

        except ValueError as e:
            click.echo(f"Error: {e}", err=True)
            raise click.Abort from e
        except Exception as e:
            click.echo(f"Error resetting configuration: {e}", err=True)
            raise click.Abort from e

    def _print_yaml_with_syntax(self, config_data: dict) -> None:
        """Print YAML data with syntax highlighting if possible."""
        yaml_output = yaml.dump(config_data, default_flow_style=False, sort_keys=True)

        # Try to apply syntax highlighting if rich supports it
        try:
            syntax = Syntax(yaml_output, "yaml", theme="monokai", line_numbers=False)
            console.print(syntax)
        except Exception:
            # Fall back to plain output if syntax highlighting fails
            click.echo(yaml_output)
