# PAISE2 Project Brief

## Purpose of this file
- Foundation document that shapes all other files
- Created at project start if it doesn't exist
- Defines core requirements and goals
- Source of truth for project scope

## Project Overview

PAISE2 is a desktop-class search engine indexer with an extensible plugin system. The project focuses on building a comprehensive plugin architecture that can handle content extraction, fetching, and indexing from various sources.

## Core Goals

1. **Plugin-First Architecture**: Build a robust plugin system that enables easy extension and customization
2. **Type Safety**: Use Protocol-based interfaces for all extension points with static type checking
3. **Asynchronous Processing**: Handle content processing through job queues for scalability
4. **Resumable Operations**: Support system restart with minimal duplicate work
5. **Space Efficiency**: Avoid copying file content when indexing local files

## Key Requirements

### Functional Requirements
- **Content Processing Pipeline**: Source → Fetch → Extract → Store → Index
- **Plugin Discovery**: Automatic scanning of internal plugins with @hookimpl decorators
- **Configuration Management**: YAML-based configuration with plugin defaults merging
- **State Persistence**: Plugin state management with automatic partitioning
- **Caching**: Efficient content caching with automatic cleanup
- **Job Queue System**: Asynchronous processing with multiple provider options

### Technical Requirements
- **Python 3.8+** with uv package management
- **pluggy** for plugin system infrastructure
- **asyncio** for asynchronous operations
- **typing.Protocol** for interface definitions
- **dataclasses** for immutable data structures
- **YAML** for configuration files

## Project Scope

### Phase 1: Plugin Infrastructure
- Core plugin system with pluggy integration
- Essential extension points (Config, Storage, Jobs, State, Cache)
- Host interfaces with base class pattern
- Test plugin simulacra for development
- Phased startup sequence
- Basic job queue processing

### Phase 2: Real Functionality
- Replace test plugins with actual implementations
- Add content extractors (HTML, PDF, text, etc.)
- Add content sources (directories, bookmarks, etc.)
- Add content fetchers (file, HTTP, API)
- Error isolation and handling

### Phase 3: Advanced Features
- Dynamic plugin loading/unloading
- Plugin sandboxing and security
- Web-based configuration UI
- Performance monitoring
- Distributed processing support

## Success Criteria

- Complete phased startup sequence works
- End-to-end content processing flow operational
- Plugin state isolation and configuration merging functional
- System can restart and resume operations
- Test plugins demonstrate all extension points
- Type safety maintained throughout system

## Non-Goals

- Real-time search interface (separate concern)
- Complex search ranking algorithms (future enhancement)
- Multi-user support (single desktop focus)
- Network-based plugin distribution (future enhancement)
