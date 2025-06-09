# Product Context

## Purpose of this file
- Why this project exists
- Problems it solves
- How it should work
- User experience goals

## Problem Statement

Current search indexing solutions are either too complex for desktop use or too simple for comprehensive content processing. Users need a way to index diverse content types (documents, web pages, code, media) from multiple sources (local files, bookmarks, APIs) without being locked into specific vendors or formats.

## Solution Vision

PAISE2 provides a plugin-based search indexer that can adapt to any content type or source through its extension system. Users can configure what to index through simple YAML files, while developers can extend functionality through well-defined plugin interfaces.

## Target Users

### Primary Users
- **Knowledge Workers**: People who work with diverse document types and need unified search
- **Researchers**: Users dealing with multiple information sources and formats
- **Developers**: Users with code repositories, documentation, and technical content

### Secondary Users
- **Plugin Developers**: Developers extending PAISE2 with new content types or sources
- **System Integrators**: Users connecting PAISE2 to existing workflows and tools

## User Experience Goals

### For End Users
- **Simple Configuration**: Define what to index through YAML files
- **Automatic Processing**: System handles content discovery, fetching, and extraction automatically
- **Resumable Operations**: Can stop and restart without losing progress
- **Space Efficient**: No unnecessary file duplication

### For Plugin Developers
- **Type-Safe APIs**: Protocol-based interfaces with static type checking
- **Minimal Boilerplate**: Just implement Protocol and register with @hookimpl
- **Rich Host Services**: Access to configuration, state, caching, and job queues
- **Testing Support**: Test infrastructure for plugin development

## How It Should Work

### Content Processing Flow
1. **Configuration**: User defines sources in YAML (directories, bookmarks, APIs)
2. **Discovery**: ContentSources scan configuration and schedule content for fetching
3. **Fetching**: ContentFetchers retrieve content from various sources
4. **Extraction**: ContentExtractors process content and extract searchable text
5. **Storage**: Processed content stored with metadata for search indexing
6. **Resumability**: System tracks progress and can resume after interruption

### Plugin Development Flow
1. **Interface Definition**: Implement typing.Protocol for extension point
2. **Registration**: Use @hookimpl decorator to register plugin
3. **Host Interaction**: Use host interface for system services
4. **Configuration**: Define default configuration if needed
5. **Testing**: Write unit tests using provided test infrastructure

## Value Proposition

### For Users
- **Unified Search**: One system for all content types and sources
- **Extensible**: Add new content types without changing core system
- **Efficient**: Avoid duplicate storage and unnecessary processing
- **Reliable**: Resumable operations with job queue persistence

### For Developers
- **Clean Architecture**: Well-defined extension points with type safety
- **Rich Infrastructure**: Built-in services for common plugin needs
- **Easy Testing**: Comprehensive test support for plugin development
- **Future-Proof**: Architecture supports advanced features as needed

## Success Metrics

- **Plugin Ecosystem**: Number of available plugins and content types supported
- **User Adoption**: Users successfully configuring and using the system
- **Developer Experience**: Time from plugin idea to working implementation
- **System Reliability**: Successful resume rate after interruptions
- **Performance**: Processing throughput and resource efficiency
