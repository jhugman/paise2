# PAISE2 Command Line Reference

This document provides a comprehensive reference for all PAISE2 command line interface commands.

## Overview

PAISE2 provides a command-line interface for system operations and management. The CLI is extensible through the plugin system, allowing plugins to contribute additional commands and functionality.

## Global Options

All commands support these global options:

```bash
--log-level [DEBUG|INFO|WARNING|ERROR]  Set logging level (default: INFO)
--version                               Show version and exit
--help                                  Show help message and exit
```

## Environment Variables

- `PAISE2_PROFILE`: Set the active profile (development, test, production)
- `PAISE2_CONFIG_DIR`: Set the configuration directory (default: `~/.config/paise2`)

## Configuration Management Commands

The `config` command group provides comprehensive configuration management functionality.

### `paise2 config edit <CONFIG_ID>`

Edit configuration files with automatic default provisioning.

**Usage:**
```bash
paise2 config edit <CONFIG_ID>
```

**Description:**
Opens an editor to modify the user override file for the specified configuration ID. If no override file exists, the system will:

1. Copy the default configuration from the corresponding ConfigurationProvider
2. Save it as `$PAISE2_CONFIG_DIR/<CONFIG_ID>.yaml`
3. Open the file in the system editor

**Examples:**
```bash
# Edit the content fetcher configuration
paise2 config edit content_fetcher

# Edit worker configuration
paise2 config edit workers
```

**Error Handling:**
- If no ConfigurationProvider exists for the given ID, shows an error message including the path where the override file would be created
- If the editor fails to launch, shows an appropriate error message

### `paise2 config list [--json]`

List all available configuration providers in the system.

**Usage:**
```bash
paise2 config list [--json]
```

**Options:**
- `--json`: Output detailed information in JSON format

**Description:**
Without `--json`: Lists all configuration provider IDs, one per line.

With `--json`: Provides detailed information including:
- Configuration ID
- Whether the configuration has a user override file
- Associated plugin information (when available)

**Examples:**
```bash
# Simple list
paise2 config list
content_fetcher
workers
database

# Detailed JSON output
paise2 config list --json
[
  {
    "id": "content_fetcher",
    "has_override": true,
    "plugin": "paise2.plugins.core.fetchers"
  },
  {
    "id": "workers",
    "has_override": false,
    "plugin": "paise2.plugins.core.workers"
  }
]
```

**Behavior:**
- If no configuration providers are available, produces no output (or empty array for JSON)
- Output is sorted alphabetically by configuration ID

### `paise2 config reset --all|<CONFIG_ID>`

Remove user configuration override files.

**Usage:**
```bash
paise2 config reset <CONFIG_ID>
paise2 config reset --all
```

**Options:**
- `--all`: Reset all configuration overrides

**Description:**
Deletes user override files, reverting configurations to their plugin defaults.

**Examples:**
```bash
# Reset specific configuration
paise2 config reset content_fetcher

# Reset all configurations
paise2 config reset --all
```

**Error Handling:**
- If the configuration ID doesn't exist, shows an appropriate error message
- If the configuration ID exists but has no override file, succeeds silently
- Cannot specify both `--all` and a specific `CONFIG_ID`

### `paise2 config show [<CONFIG_ID>*]`

Display current merged configuration state.

**Usage:**
```bash
paise2 config show [<CONFIG_ID> ...]
```

**Description:**
Shows the final merged configuration after combining plugin defaults with user overrides.

**Examples:**
```bash
# Show complete system configuration
paise2 config show

# Show specific configurations
paise2 config show content_fetcher workers

# Show single configuration
paise2 config show database
```

**Output Format:**
- YAML format with syntax highlighting when possible
- Shows the actual configuration values that plugins will receive
- Includes comments from default configurations where preserved

**Error Handling:**
- If a specified CONFIG_ID doesn't exist, shows an error for that ID and continues with others
- If no CONFIG_IDs are specified, shows the complete merged configuration

## Core System Commands

### `paise2 run`

Start the PAISE2 content indexing system.

**Usage:**
```bash
paise2 run
```

**Description:**
Initializes and starts the complete PAISE2 system including:
- Plugin loading and initialization
- Configuration merging
- Task queue setup
- Content source activation

**Examples:**
```bash
# Start with development profile
PAISE2_PROFILE=development paise2 run

# Start with custom configuration directory
PAISE2_CONFIG_DIR=~/.config/paise2/ paise2 run
```

### `paise2 status`

Check system health and status.

**Usage:**
```bash
paise2 status [--json]
```

**Description:**
Provides detailed information about system components and their current state.

### `paise2 validate`

Validate configuration and plugin integrity.

**Usage:**
```bash
paise2 validate
```

**Description:**
Performs comprehensive validation of the system configuration and loaded plugins.

### `paise2 reset [--hard]`

Reset system components using registered ResetAction plugins.

**Usage:**
```bash
paise2 reset
paise2 reset --hard
```

**Description:**
Calls all registered ResetAction plugins to reset various system components. The level of reset depends on the flag used:

- **Soft reset** (default): Performs a partial reset, clearing temporary data while preserving important persistent information
- **Hard reset** (`--hard`): Performs a complete reset, clearing all data and returning components to their initial state

**Options:**
- `--hard`: Perform a hard reset instead of the default soft reset

**Examples:**
```bash
# Perform soft reset (default)
paise2 reset

# Perform hard reset (complete data clearing)
paise2 reset --hard
```

**Behavior:**
- Executes all registered ResetAction plugins in sequence
- Continues execution even if individual reset actions fail
- Provides feedback on success/failure of each reset action
- Shows warning if no reset actions are registered

**Error Handling:**
- Individual reset action failures are logged but don't stop the overall reset process
- System errors during reset initialization will abort the command

### `paise2 version`

Display version information.

**Usage:**
```bash
paise2 version
```

**Description:**
Shows detailed version information including system status and capabilities.

## Plugin-Contributed Commands

Additional commands may be available depending on the loaded plugins. Use `paise2 --help` to see all available commands in your current configuration.

## Configuration File Format

All configuration files use YAML format with the following structure:

```yaml
# Plugin-specific configuration sections
plugin_name:
  setting1: value1
  setting2: value2

# Global configuration
global:
  log_level: INFO
  debug_mode: false
```

## Examples

### Basic Configuration Workflow

```bash
# See what configurations are available
paise2 config list

# Edit a specific configuration
paise2 config edit content_fetcher

# View the merged result
paise2 config show content_fetcher

# Reset if needed
paise2 config reset content_fetcher
```

### JSON Integration

```bash
# Get configuration info as JSON for scripting
paise2 config list --json | jq '.[] | select(.has_override == true)'

# Check system status programmatically
paise2 status --json | jq '.components.database.status'
```
