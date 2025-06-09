# Active Context

## Purpose of this file
- Current work focus
- Recent changes
- Next steps
- Active decisions and considerations
- Important patterns and preferences
- Learnings and project insights

## Current Work Focus

### Phase 1: Plugin Infrastructure Foundation
The project is in the initial implementation phase, focusing on building the core plugin system infrastructure with test plugins as simulacra. This establishes the foundation that all future functionality will build upon.

### Immediate Priority: Core Plugin System
1. **Plugin Discovery and Registration**: Implement pluggy integration with internal plugin scanning
2. **Extension Point Infrastructure**: Create Protocol definitions and registration hooks
3. **Phased Startup Sequence**: Implement 5-phase startup to handle singleton dependencies
4. **Host Interface System**: Build base host with specialized extensions
5. **Test Plugin Simulacra**: Create simple test plugins for each extension point

## Recent Changes

### Project Setup
- Created comprehensive plugin specification in `docs/plugins/spec.md`
- Established memory bank structure for project documentation
- Defined technical requirements and dependencies

### Architecture Decisions Made
- **pluggy Integration**: Use pluggy's hook system for plugin management
- **Protocol-Based Interfaces**: Use `typing.Protocol` for structural typing
- **Phased Startup**: 5-phase sequence to handle singleton dependency ordering
- **Job Queue Processing**: Route most operations through job queue system
- **Automatic State Partitioning**: Partition plugin state by module name

## Next Steps

### Immediate (Current Sprint)
1. **Create Core Plugin Infrastructure**
   - `paise2/plugins/core/interfaces.py` - Protocol definitions
   - `paise2/plugins/core/registry.py` - Plugin registration system
   - `paise2/plugins/core/manager.py` - Plugin management and discovery
   - `paise2/plugins/core/startup.py` - Phased startup sequence

2. **Implement Essential Extension Points**
   - ConfigurationProvider (Phase 2)
   - DataStorageProvider (Phase 2)
   - JobQueueProvider (Phase 2)
   - StateStorageProvider (Phase 2)
   - CacheProvider (Phase 2)

3. **Build Host Interface System**
   - `paise2/plugins/core/hosts.py` - BaseHost and specialized hosts
   - State management with automatic partitioning
   - Configuration access integration

### Short Term (Next 2-3 Sprints)
1. **Complete Phase 4 Extension Points**
   - ContentExtractor
   - ContentSource
   - ContentFetcher
   - LifecycleAction

2. **Default Provider Implementations**
   - NoJobQueueProvider (synchronous for development)
   - SQLiteJobQueueProvider (persistent for production)
   - FileConfigurationProvider
   - Basic storage, state, and cache providers

3. **Test Plugin Simulacra**
   - TestContentExtractor (simple text extraction)
   - TestContentSource (generates test URLs)
   - TestContentFetcher (simulates fetching)
   - TestConfigurationProvider and infrastructure providers

4. **Supporting Systems**
   - Configuration merging logic
   - Job queue processing infrastructure
   - Cache management with automatic cleanup

## Active Decisions and Considerations

### Architecture Decisions in Progress
- **Error Handling Strategy**: Start with "fail fast" approach, plan for isolation later
- **Job Queue Implementation**: Begin with synchronous mode, add persistence
- **Plugin State Persistence**: SQLite-based with automatic partitioning
- **Configuration File Location**: Need to determine user config location strategy

### Key Design Considerations
- **Type Safety vs Flexibility**: Balance Protocol strictness with plugin flexibility
- **Performance vs Simplicity**: Start simple, optimize based on real usage
- **Plugin Discovery**: Internal scanning vs explicit registration trade-offs
- **Resource Management**: Plugin resource limits and cleanup strategies

### Open Questions
- **Plugin Sandboxing**: When to add security isolation for plugins?
- **Dynamic Loading**: Support for runtime plugin loading/unloading?
- **Plugin Dependencies**: How to handle plugins that depend on other plugins?
- **Configuration Validation**: How strictly to validate plugin configurations?

## Important Patterns and Preferences

### Code Organization Patterns
- **Protocol-First Design**: Define interfaces before implementations
- **Immutable Data Structures**: Use frozen dataclasses with copy/merge methods
- **Dependency Injection**: Singletons created by plugin system and injected
- **Separation of Concerns**: Clear boundaries between plugin system and business logic

### Implementation Preferences
- **Type Safety**: Use mypy-compatible type hints throughout
- **Async/Await**: Use async patterns for I/O operations and job processing
- **Minimal Dependencies**: Prefer built-in libraries when possible
- **Testable Design**: Structure code for easy unit and integration testing

### Documentation Standards
- **Protocol Documentation**: Clear docstrings for all Protocol methods
- **Plugin Examples**: Comprehensive examples for each extension point
- **API Stability**: Mark APIs as stable vs experimental
- **Migration Guides**: Document changes that affect plugin developers

## Learnings and Project Insights

### Plugin System Design Insights
- **Phased Startup Critical**: Singleton dependency ordering requires careful phase management
- **Host Interface Pattern**: Base host with extensions provides clean separation
- **State Partitioning**: Automatic partitioning by module name eliminates namespace conflicts
- **Job Queue Abstraction**: Enables both synchronous (dev) and asynchronous (prod) processing

### Development Process Insights
- **Specification First**: Comprehensive spec document essential for complex systems
- **Test Plugins Important**: Simulacra provide concrete examples and testing foundation
- **Memory Bank Value**: Documentation structure enables better context management
- **Type Safety Investment**: Protocol-based interfaces pay dividends in maintainability

### Technical Implementation Insights
- **pluggy Power**: Excellent foundation for plugin systems with minimal boilerplate
- **Protocol Benefits**: Structural typing more flexible than inheritance-based systems
- **Configuration Merging Complexity**: Need careful rules for plugin defaults vs user overrides
- **Resumable Operations**: Job queue persistence enables robust restart behavior

## Context for Collaboration

### For New Team Members
- Read the complete plugin specification first: `docs/plugins/spec.md`
- Understand the 5-phase startup sequence - it's critical to the architecture
- Study the Protocol definitions - they define the contract for all plugins
- Look at test plugin simulacra for concrete examples of each extension point

### For Plugin Developers
- Start with Protocol definitions in `interfaces.py`
- Use `@hookimpl` decorator for registration functions
- Access system services through host interfaces
- Implement test plugins first to understand patterns

### For System Integration
- Plugin discovery happens automatically by scanning for `@hookimpl` decorators
- Configuration merging follows specific rules (plugin defaults + user overrides)
- State is automatically partitioned by plugin module name
- Job queue enables both sync and async processing modes
