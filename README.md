# PAISE2

Desktop search engine indexer with extensible plugin system.

## Overview

PAISE2 is a plugin-based desktop search engine indexer that allows for extensible content processing through a well-defined plugin architecture. It uses a phased startup system to handle complex plugin dependencies and provides a job queue system for asynchronous processing.

## Features

- **Plugin Architecture**: Extensible system using pluggy with Protocol-based interfaces
- **Immutable Data Models**: Clean data structures with copy/merge operations
- **Job Queue System**: Support for both synchronous and asynchronous processing
- **State Management**: Automatic state partitioning by plugin module
- **Configuration System**: Plugin defaults with user override support

## Development

This project uses `uv` for dependency management and modern Python practices.

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest

# Run linting
uv run ruff check

# Run type checking
uv run mypy src/
```

## Architecture

The system is built around several key concepts:

- **Extension Points**: Well-defined interfaces for plugin functionality
- **Phased Startup**: 5-phase startup sequence to handle singleton dependencies
- **Host Interfaces**: Provide plugins with access to system services
- **Job Queue**: Abstraction layer for processing tasks

## Status

This project is currently under active development. See `docs/plugins/prompt-plan.md` for the detailed implementation roadmap.
