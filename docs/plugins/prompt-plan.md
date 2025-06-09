# PAISE2 Plugin System - Implementation Plan

## Overview

This document provides a detailed, step-by-step implementation plan for building the PAISE2 plugin system. Each prompt is designed to be implemented in a test-driven manner, building incrementally on previous work with no orphaned code.

The plan prioritizes:
- **Clean architecture** with protocol-based interfaces
- **Incremental progress** with small, safe steps
- **Early testing** at every stage
- **Refactoring** to reduce repetition and improve design
- **Integration** ensuring no hanging code

## Implementation Blueprint

### Phase 1: Foundation (Prompts 1-4)
Set up project structure, core data types, and basic plugin discovery

### Phase 2: Configuration System (Prompts 5-7)
Build configuration management with provider pattern

### Phase 3: Core Infrastructure (Prompts 8-12)
State storage, job queues, caching, and data storage providers

### Phase 4: Plugin System Core (Prompts 13-16)
Plugin discovery, registration, and host interfaces

### Phase 5: Content Processing Pipeline (Prompts 17-20)
Content sources, fetchers, and extractors with job-based processing

### Phase 6: Integration & Polish (Prompts 21-22)
End-to-end integration, resumability, and cleanup

---

## PROMPT 1: Project Foundation and Data Models

### Context
Start a greenfield Python project for the PAISE2 plugin system. This is a desktop search engine indexer that uses a plugin architecture. Focus on establishing the basic project structure and core data types.

### Task
```
Create the initial Python project structure using modern Python practices with uv for dependency management. Implement the core immutable data models that will be used throughout the system.

Requirements:
1. Set up project structure with uv (pyproject.toml, src layout)
2. Add core dependencies: pluggy, pytest, typing-extensions (for Python 3.8 compatibility)
3. Create immutable data models using dataclasses:
   - Metadata (with copy/merge methods)
   - Content type alias
   - ItemId, JobId, CacheId type aliases
4. Add comprehensive unit tests for data models, especially immutable operations
5. Set up basic logging utilities
6. Configure pytest with proper test discovery

Focus on:
- Modern Python project structure
- Type safety with proper annotations
- Immutable data patterns
- Comprehensive test coverage
- Clean separation of concerns

The Metadata class should support:
- Immutable updates via copy() method
- Merging with other Metadata instances
- Proper handling of lists (concatenation) and dicts (recursive merge)
- All fields from the specification including processing_state for resumability
```

### Task List
- [x] Create pyproject.toml with proper metadata and dependencies
- [x] Set up src/paise2 directory structure
- [x] Implement Metadata dataclass with immutable operations
- [x] Create type aliases for ItemId, JobId, CacheId
- [x] Add Content type alias and related types
- [x] Implement comprehensive tests for Metadata copy/merge operations
- [x] Set up basic logging utilities in utils/logging.py
- [x] Configure pytest.ini or pyproject.toml test settings
- [x] Add __init__.py files for proper package structure
- [x] Verify all tests pass and type checking works
- [x] Create comprehensive README.md with project overview
- [x] Modernize type annotations (Union → |, Optional → |, List/Dict → list/dict)
- [x] Move runtime imports to TYPE_CHECKING blocks for type-only usage
- [x] Fix all ruff linting issues and mypy type checking
- [x] **PROMPT 1 COMPLETE** ✅

**Final Status (June 9, 2025):**
- ✅ All 9 unit tests passing
- ✅ Ruff linting: All checks pass
- ✅ MyPy type checking: Success with no issues
- ✅ Modern Python 3.9+ type annotations throughout
- ✅ Clean, maintainable codebase ready for PROMPT 2

---

## PROMPT 2: Protocol Interfaces Foundation

### Context
Building on the core data models, now implement the Protocol interfaces that define the contract for all extension points. These protocols use structural typing and will be implemented by plugins.

### Task
```
Create comprehensive Protocol interfaces for all extension points in the PAISE2 system. Focus on clean interface design and proper typing.

Requirements:
1. Create src/paise2/plugins/core/interfaces.py with all Protocol definitions:
   - ConfigurationProvider, DataStorageProvider, JobQueueProvider
   - StateStorageProvider, CacheProvider (Phase 2 extension points)
   - ContentExtractor, ContentSource, ContentFetcher (Phase 4 extension points)
   - LifecycleAction
2. Define supporting protocols for host interfaces:
   - BaseHost, ContentExtractorHost, ContentSourceHost, etc.
3. Create state management interfaces:
   - StateStorage, StateManager protocols
4. Add job processing protocols:
   - JobQueue, Job dataclass with proper typing
5. Implement comprehensive unit tests verifying protocol compliance
6. Use typing.Protocol for structural typing
7. Add proper async/await annotations where needed
8. Include detailed docstrings for all protocols

Focus on:
- Clear protocol contracts
- Proper async/await usage
- Type safety throughout
- Comprehensive documentation
- Test-driven validation of interface contracts
```

### Task List
- [ ] Create src/paise2/plugins/core/ directory structure
- [ ] Implement Phase 2 singleton-contributing protocols (Configuration, Storage, etc.)
- [ ] Implement Phase 4 singleton-using protocols (ContentExtractor, ContentSource, etc.)
- [ ] Create host interface protocols with proper inheritance
- [ ] Define StateStorage and StateManager protocols
- [ ] Implement Job dataclass and JobQueue protocol
- [ ] Add comprehensive protocol compliance tests
- [ ] Include proper async typing throughout
- [ ] Add detailed docstrings explaining each protocol's purpose
- [ ] Verify all protocols are properly typed and testable
- [ ] PROMPT 2 COMPLETE

---

## PROMPT 3: Plugin Registration System

### Context
With protocols defined, implement the plugin registration system using pluggy's native approach. This will handle the discovery and registration of plugin extensions.

### Task
```
Build the plugin registration system that allows plugins to register implementations of the various extension points using pluggy's hookimpl pattern.

Requirements:
1. Create src/paise2/plugins/core/registry.py with:
   - PluginManager class wrapping pluggy.PluginManager
   - Registration hooks for each extension point type
   - Plugin discovery for internal plugins (scan paise2 codebase)
   - External plugin discovery support
2. Define hookspec functions for each extension point registration
3. Implement plugin scanning that finds @hookimpl decorated functions
4. Create plugin loading with proper error handling
5. Add validation that registered extensions implement required protocols
6. Implement comprehensive tests including:
   - Plugin discovery
   - Registration validation
   - Error handling for invalid plugins
7. Create test plugins as examples/testing aids
8. Support simple load ordering (discovery order)

Focus on:
- Clean separation between registration and plugin logic
- Proper error handling and validation
- Type safety in registration process
- Comprehensive test coverage
- Clear plugin authoring patterns
```

### Task List
- [ ] Create PluginManager class with pluggy integration
- [ ] Define hookspec functions for all extension point registrations
- [ ] Implement internal plugin discovery (scan paise2 codebase for @hookimpl)
- [ ] Add external plugin discovery support
- [ ] Create plugin validation ensuring protocol compliance
- [ ] Implement proper error handling for plugin loading
- [ ] Add comprehensive tests for plugin discovery and registration
- [ ] Create test plugins for testing registration system
- [ ] Verify load ordering works correctly
- [ ] Add logging for plugin discovery and registration
- [ ] PROMPT 3 COMPLETE

---

## PROMPT 4: Basic Host Infrastructure

### Context
Now implement the host infrastructure that plugins use to interact with the system. Start with the base host class and basic functionality before adding specialized hosts.

### Task
```
Create the host infrastructure that plugins interact with. Implement the base host class and the state management system with automatic partitioning.

Requirements:
1. Create src/paise2/plugins/core/hosts.py with:
   - BaseHost class with shared functionality
   - StateManager class with automatic plugin partitioning
   - Host factory functions
2. Implement state partitioning by plugin module name
3. Add placeholder properties for logger, configuration, etc. (will be injected later)
4. Create comprehensive state management tests:
   - Automatic partitioning verification
   - State isolation between plugins
   - Versioning support for re-indexing
5. Add mock implementations for testing
6. Ensure state operations are thread-safe if needed
7. Include proper error handling and validation

Focus on:
- Automatic state partitioning by plugin module name
- Clean host interface design
- Comprehensive testing of state isolation
- Future-proofing for dependency injection
- Type safety throughout
```

### Task List
- [ ] Create BaseHost class with common functionality
- [ ] Implement StateManager with automatic partitioning by module name
- [ ] Add state storage operations (store, get, get_versioned_state, etc.)
- [ ] Create host factory functions for different host types
- [ ] Implement comprehensive state partitioning tests
- [ ] Verify state isolation between different plugin modules
- [ ] Add versioning support for state management
- [ ] Create mock implementations for testing
- [ ] Add proper error handling and validation
- [ ] Include thread safety considerations if needed
- [ ] PROMPT 4 COMPLETE

---

## PROMPT 5: Configuration Provider System

### Context
Begin implementing the singleton-contributing extension points, starting with configuration management. This system allows plugins to contribute default configurations.

### Task
```
Implement the configuration provider system that allows plugins to contribute default configurations. This includes both the provider interfaces and the configuration merging logic.

Requirements:
1. Create src/paise2/config/ directory with:
   - Configuration data models and manager
   - YAML loading and merging logic
   - User vs plugin configuration handling
2. Implement FileConfigurationProvider as a default implementation
3. Create configuration merging with these rules:
   - Plugin-to-plugin: later plugins override earlier for scalars
   - Lists are concatenated from all sources
   - User config completely overrides plugin defaults for same keys
   - Dictionary merging is recursive
4. Add comprehensive tests for:
   - Configuration loading from YAML
   - Merging behavior (scalars, lists, dicts)
   - User override behavior
   - File path resolution relative to plugin modules
5. Support $PAISE_CONFIG_DIR environment variable
6. Add proper error handling for invalid YAML/missing files

Focus on:
- Correct merging semantics
- Clear configuration access patterns
- Comprehensive test coverage
- User configuration override behavior
- Clean separation of plugin vs user config
```

### Task List
- [ ] Create configuration data models in src/paise2/config/models.py
- [ ] Implement Configuration manager class with YAML support
- [ ] Create FileConfigurationProvider implementation
- [ ] Implement configuration merging logic with proper rules
- [ ] Add support for $PAISE_CONFIG_DIR environment variable
- [ ] Handle relative paths relative to plugin modules
- [ ] Create comprehensive tests for all merging scenarios
- [ ] Test user configuration override behavior
- [ ] Add error handling for invalid YAML and missing files
- [ ] Verify configuration access patterns work correctly
- [ ] PROMPT 5 COMPLETE

---

## PROMPT 6: Configuration Integration with Plugin System

### Context
Integrate the configuration system with the plugin system, ensuring configurations can be loaded during the phased startup and accessed by all plugins.

### Task
```
Integrate configuration management into the plugin system with proper singleton creation and access patterns.

Requirements:
1. Update the plugin registration system to handle ConfigurationProvider plugins
2. Create configuration singleton creation logic in the startup sequence
3. Integrate configuration access into BaseHost
4. Add configuration reloading capability with diff detection
5. Create test configuration providers for testing
6. Update host interfaces to provide configuration access
7. Add comprehensive integration tests:
   - Configuration loading during startup
   - Plugin access to merged configuration
   - Configuration reloading behavior
   - Multiple configuration providers working together
8. Add proper error handling for configuration failures during startup

Focus on:
- Seamless integration with plugin system
- Proper singleton lifecycle management
- Configuration access patterns for plugins
- Comprehensive testing of integration points
- Clean error handling and recovery
```

### Task List
- [ ] Update plugin registration to handle ConfigurationProvider
- [ ] Create configuration singleton creation in startup sequence
- [ ] Integrate configuration access into BaseHost class
- [ ] Add configuration reloading with diff detection
- [ ] Create test configuration providers for comprehensive testing
- [ ] Update all host interfaces to provide configuration access
- [ ] Add integration tests for configuration loading during startup
- [ ] Test plugin access to merged configuration data
- [ ] Verify configuration reloading behavior works correctly
- [ ] Add proper error handling for configuration startup failures
- [ ] PROMPT 6 COMPLETE

---

## PROMPT 7: Configuration System Refinement

### Context
Refine the configuration system based on integration experience. Focus on improving usability, error handling, and performance.

### Task
```
Refine and polish the configuration system to improve usability and robustness.

Requirements:
1. Improve configuration validation and error reporting
2. Add configuration schema validation if needed
3. Optimize configuration loading and merging performance
4. Add configuration debugging/introspection tools
5. Improve error messages for configuration problems
6. Add configuration documentation generation
7. Create helper utilities for common configuration patterns
8. Refactor any duplicate code in configuration handling
9. Add configuration change notifications if needed
10. Comprehensive testing of edge cases and error conditions

Focus on:
- Improved developer experience
- Better error messages and debugging
- Performance optimization
- Code quality and maintainability
- Comprehensive edge case testing
```

### Task List
- [ ] Add configuration validation with clear error messages
- [ ] Implement configuration schema validation if beneficial
- [ ] Optimize configuration loading and merging performance
- [ ] Create configuration debugging and introspection utilities
- [ ] Improve error messages for common configuration problems
- [ ] Add configuration documentation generation capabilities
- [ ] Create helper utilities for common configuration access patterns
- [ ] Refactor duplicate code in configuration handling
- [ ] Add configuration change notification system if needed
- [ ] Test edge cases and error conditions comprehensively
- [ ] PROMPT 7 COMPLETE

---

## PROMPT 8: State Storage Provider System

### Context
Implement the state storage provider system that allows plugins to persist state between runs, with automatic partitioning and versioning support.

### Task
```
Build the state storage provider system that handles plugin state persistence with automatic partitioning and versioning.

Requirements:
1. Create src/paise2/state/ with state storage implementations:
   - StateStorage protocol implementation
   - File-based and memory-based providers
   - Versioning support for plugin updates
2. Implement automatic state partitioning by plugin module name
3. Add state storage operations:
   - store, get, get_versioned_state, get_all_keys_with_value
4. Create comprehensive tests for:
   - State isolation between plugins
   - Versioning behavior
   - State persistence and retrieval
   - State querying operations
5. Add state migration utilities for plugin updates
6. Include proper error handling and data validation
7. Support both synchronous and asynchronous operations

Focus on:
- Automatic partitioning without explicit naming
- Robust versioning for plugin evolution
- Clean state access patterns
- Data integrity and error handling
- Comprehensive testing of isolation and persistence
```

### Task List
- [ ] Create state storage data models and interfaces
- [ ] Implement file-based state storage provider
- [ ] Create memory-based state storage for testing
- [ ] Add automatic partitioning by plugin module name
- [ ] Implement versioning support with proper state migration
- [ ] Create state querying operations (get_all_keys_with_value, etc.)
- [ ] Add comprehensive tests for state isolation between plugins
- [ ] Test state persistence and retrieval operations
- [ ] Verify versioning behavior works correctly for plugin updates
- [ ] Add proper error handling and data validation
- [ ] PROMPT 8 COMPLETE

---

## PROMPT 9: Job Queue Provider System

### Context
Implement the job queue provider system that handles asynchronous job processing. Start with both synchronous (for development) and persistent (for production) implementations.

### Task
```
Build the job queue provider system with both synchronous and persistent implementations for flexible deployment.

Requirements:
1. Create src/paise2/plugins/core/jobs.py with:
   - Job dataclass with proper typing and metadata
   - JobQueue protocol implementation
   - Strongly typed job types (JOB_TYPES constant)
2. Implement two providers:
   - NoJobQueueProvider (synchronous execution for development)
   - SQLiteJobQueueProvider (persistent queue for production)
3. Add job queue operations:
   - enqueue, dequeue, complete, fail, get_incomplete_jobs
4. Include job retry logic and priority handling
5. Add comprehensive tests for:
   - Both queue implementations
   - Job lifecycle (enqueue -> dequeue -> complete/fail)
   - Retry behavior and priorities
   - Resume incomplete jobs on startup
6. Add proper error handling and job validation

Focus on:
- Clean job processing patterns
- Support for both sync and async workflows
- Robust job lifecycle management
- Resumability for system restarts
- Comprehensive testing of job processing
```

### Task List
- [ ] Create Job dataclass with proper typing and metadata
- [ ] Define JOB_TYPES constant with strongly typed job types
- [ ] Implement JobQueue protocol with all required operations
- [ ] Create NoJobQueueProvider for synchronous development workflow
- [ ] Implement SQLiteJobQueueProvider for persistent production usage
- [ ] Add job retry logic and priority handling
- [ ] Create comprehensive tests for job lifecycle management
- [ ] Test both synchronous and asynchronous job processing
- [ ] Verify job resumption works correctly after system restart
- [ ] Add proper error handling and job validation
- [ ] PROMPT 9 COMPLETE

---

## PROMPT 10: Cache Provider System

### Context
Implement the cache provider system that handles content caching with automatic partitioning and cleanup support.

### Task
```
Build the cache provider system for storing and managing cached content with proper partitioning and lifecycle management.

Requirements:
1. Create src/paise2/plugins/providers/cache.py with:
   - CacheManager protocol implementation
   - File-based cache provider as default
   - Memory-based cache for testing
2. Implement cache operations:
   - save, get, remove, remove_all, get_all
3. Add automatic partitioning by plugin module name
4. Include cache cleanup integration with storage system
5. Add cache size management and eviction policies
6. Create comprehensive tests for:
   - Cache operations and partitioning
   - Cache cleanup when items are removed from storage
   - Cache size limits and eviction
   - Performance characteristics
7. Add proper error handling and cache validation

Focus on:
- Efficient cache storage and retrieval
- Automatic cleanup integration
- Cache size management
- Clean partitioning by plugin
- Comprehensive testing of cache lifecycle
```

### Task List
- [ ] Create CacheManager protocol with all required operations
- [ ] Implement file-based cache provider as default implementation
- [ ] Create memory-based cache provider for testing
- [ ] Add automatic cache partitioning by plugin module name
- [ ] Implement cache cleanup integration with storage removal
- [ ] Add cache size management and eviction policies
- [ ] Create comprehensive tests for cache operations and partitioning
- [ ] Test cache cleanup when storage items are removed
- [ ] Verify cache size limits and eviction policies work correctly
- [ ] Add proper error handling and cache validation
- [ ] PROMPT 10 COMPLETE

---

## PROMPT 11: Data Storage Provider System

### Context
Implement the data storage provider system that handles the core content storage with metadata management and deduplication support.

### Task
```
Build the data storage provider system that manages indexed content with proper metadata handling and integration with caching.

Requirements:
1. Create src/paise2/storage/ with data storage implementations:
   - DataStorage protocol implementation
   - SQLite-based storage provider as default
   - Memory-based storage for testing
2. Implement storage operations:
   - add_item, update_item, update_metadata, find_item_id
   - find_item, remove_item, remove_items_by_metadata, remove_items_by_url
3. Add content deduplication at storage level
4. Include cache ID management and cleanup coordination
5. Add storage indexing for efficient querying
6. Create comprehensive tests for:
   - All CRUD operations
   - Deduplication behavior
   - Cache coordination
   - Query performance
   - Data integrity
7. Add proper error handling and data validation

Focus on:
- Efficient storage and retrieval patterns
- Proper cache integration and cleanup
- Content deduplication strategies
- Data integrity and consistency
- Comprehensive testing of storage operations
```

### Task List
- [ ] Create DataStorage protocol with all required operations
- [ ] Implement SQLite-based storage provider as default
- [ ] Create memory-based storage provider for testing
- [ ] Add content deduplication logic at storage level
- [ ] Implement cache ID management and cleanup coordination
- [ ] Add proper indexing for efficient metadata querying
- [ ] Create comprehensive tests for all CRUD operations
- [ ] Test content deduplication behavior
- [ ] Verify cache coordination and cleanup works correctly
- [ ] Add proper error handling and data validation
- [ ] PROMPT 11 COMPLETE

---

## PROMPT 12: Infrastructure Provider Integration

### Context
Integrate all the provider systems (state, jobs, cache, storage) with the plugin system and create the singleton creation logic for the phased startup.

### Task
```
Integrate all infrastructure providers into a cohesive system with proper singleton management and phased startup support.

Requirements:
1. Create src/paise2/plugins/core/startup.py with phased startup logic:
   - Phase 2: Load singleton-contributing extensions
   - Phase 3: Create singletons from providers
   - Phase 4: Load singleton-using extensions
2. Implement singleton container/dependency injection
3. Update plugin registration to handle all provider types
4. Create provider selection logic when multiple providers available
5. Add comprehensive integration tests:
   - Full phased startup sequence
   - Singleton creation and injection
   - Provider interoperability
   - Error handling during startup
6. Add startup logging and debugging support
7. Create clean shutdown procedures

Focus on:
- Proper dependency injection patterns
- Clean phased startup implementation
- Robust error handling during startup
- Provider interoperability testing
- Clean shutdown and resource cleanup
```

### Task List
- [ ] Create phased startup logic with proper phase separation
- [ ] Implement singleton container and dependency injection system
- [ ] Update plugin registration to handle all provider extension types
- [ ] Add provider selection logic for multiple provider scenarios
- [ ] Create comprehensive integration tests for full startup sequence
- [ ] Test singleton creation and injection throughout the system
- [ ] Verify provider interoperability works correctly
- [ ] Add proper error handling and recovery during startup phases
- [ ] Implement startup logging and debugging support
- [ ] Create clean shutdown procedures and resource cleanup
- [ ] PROMPT 12 COMPLETE

---

## PROMPT 13: Specialized Host Implementations

### Context
Now implement the specialized host classes that plugins interact with, building on the base host infrastructure and integrating with the singleton providers.

### Task
```
Create specialized host implementations for each extension point type, with proper dependency injection and plugin-specific functionality.

Requirements:
1. Update src/paise2/plugins/core/hosts.py with specialized hosts:
   - ContentExtractorHost, ContentSourceHost, ContentFetcherHost
   - DataStorageHost, LifecycleHost
2. Integrate singleton dependency injection into all hosts
3. Add host-specific methods (extract_file, schedule_fetch, etc.)
4. Implement job scheduling integration in hosts
5. Add proper state management integration with automatic partitioning
6. Create comprehensive tests for:
   - Host-specific functionality
   - Dependency injection
   - Job scheduling integration
   - State partitioning by plugin
7. Add host factory functions with proper plugin module detection
8. Include proper error handling and validation

Focus on:
- Clean separation of host responsibilities
- Proper dependency injection throughout
- Integration with job processing system
- Automatic state partitioning
- Comprehensive testing of host functionality
```

### Task List
- [ ] Create ContentExtractorHost with storage and cache integration
- [ ] Implement ContentSourceHost with scheduling functionality
- [ ] Create ContentFetcherHost with extraction capabilities
- [ ] Add DataStorageHost and LifecycleHost implementations
- [ ] Integrate singleton dependency injection into all host classes
- [ ] Add host-specific methods (extract_file, schedule_fetch, etc.)
- [ ] Implement job scheduling integration within host methods
- [ ] Add comprehensive tests for all host-specific functionality
- [ ] Test dependency injection and singleton access
- [ ] Verify automatic state partitioning works for all host types
- [ ] PROMPT 13 COMPLETE

---

## PROMPT 14: Plugin System Manager

### Context
Create the main plugin system manager that orchestrates the entire plugin lifecycle, from discovery through shutdown.

### Task
```
Implement the main PluginSystem class that manages the complete plugin lifecycle and coordinates all the subsystems.

Requirements:
1. Create src/paise2/plugins/core/manager.py with:
   - PluginSystem class managing complete lifecycle
   - Integration with all provider systems
   - Host creation and management
   - Plugin lifecycle coordination
2. Implement full startup sequence:
   - Bootstrap logging
   - Phase 2: Load singleton-contributing extensions
   - Phase 3: Create singletons
   - Phase 4: Load singleton-using extensions
   - Phase 5: Start the system
3. Add plugin management capabilities:
   - Plugin discovery and loading
   - Error handling and recovery
   - Graceful shutdown
4. Create comprehensive integration tests:
   - Complete startup/shutdown cycle
   - Error handling during each phase
   - Plugin isolation and interaction
5. Add system monitoring and health checks
6. Include proper logging throughout

Focus on:
- Orchestrating the complete plugin system
- Robust error handling at each phase
- Clean startup and shutdown procedures
- System monitoring and observability
- Comprehensive integration testing
```

### Task List
- [ ] Create PluginSystem class managing complete plugin lifecycle
- [ ] Implement bootstrap logging for plugin system startup
- [ ] Add Phase 2 logic for loading singleton-contributing extensions
- [ ] Create Phase 3 singleton creation from loaded providers
- [ ] Implement Phase 4 logic for loading singleton-using extensions
- [ ] Add Phase 5 system startup and host activation
- [ ] Create plugin discovery and loading coordination
- [ ] Add comprehensive error handling and recovery for each phase
- [ ] Implement graceful shutdown with proper resource cleanup
- [ ] Create integration tests for complete startup/shutdown cycles
- [ ] PROMPT 14 COMPLETE

---

## PROMPT 15: Test Plugin Implementations

### Context
Create comprehensive test plugin implementations that can be used to validate the entire plugin system and serve as examples for plugin authors.

### Task
```
Implement a complete set of test plugins that exercise all extension points and demonstrate proper plugin authoring patterns.

Requirements:
1. Create src/paise2/plugins/test_plugins/ with test implementations for:
   - TestConfigurationProvider
   - TestDataStorageProvider, TestJobQueueProvider, TestStateStorageProvider, TestCacheProvider
   - TestContentExtractor, TestContentSource, TestContentFetcher
   - TestLifecycleAction
2. Each test plugin should:
   - Implement the required protocol correctly
   - Include proper registration with @hookimpl
   - Demonstrate best practices
   - Include realistic but simple functionality
3. Add comprehensive tests for each test plugin
4. Create integration tests using test plugins end-to-end
5. Include plugin authoring documentation and examples
6. Add validation that test plugins work with the full system

Focus on:
- Complete protocol implementations
- Proper plugin registration patterns
- Realistic but simple functionality
- Plugin authoring best practices
- Comprehensive testing and validation
```

### Task List
- [ ] Create TestConfigurationProvider with sample YAML configuration
- [ ] Implement TestDataStorageProvider with in-memory storage
- [ ] Create TestJobQueueProvider, TestStateStorageProvider, TestCacheProvider
- [ ] Implement TestContentExtractor with simple text processing
- [ ] Create TestContentSource that generates test URLs for processing
- [ ] Implement TestContentFetcher with simulated fetch operations
- [ ] Add TestLifecycleAction with startup/shutdown logging
- [ ] Create proper @hookimpl registration for all test plugins
- [ ] Add comprehensive unit tests for each test plugin
- [ ] Create integration tests using test plugins end-to-end
- [ ] PROMPT 15 COMPLETE

---

## PROMPT 16: Plugin System Testing and Validation

### Context
Create comprehensive tests that validate the entire plugin system works correctly, with proper isolation, error handling, and integration.

### Task
```
Build comprehensive test suite that validates the complete plugin system functionality and robustness.

Requirements:
1. Create tests/integration/ with comprehensive integration tests:
   - Complete startup sequence testing
   - Plugin isolation and state partitioning
   - Error handling and recovery
   - Job processing integration
   - Configuration system integration
2. Add performance and stress testing:
   - Plugin loading performance
   - Job queue performance
   - State storage performance
   - Memory usage validation
3. Create plugin system validation tools:
   - Plugin compatibility checker
   - System health diagnostics
   - Performance monitoring
4. Add error injection testing to validate robustness
5. Include plugin development testing utilities
6. Add comprehensive documentation for test suite

Focus on:
- Complete system validation
- Plugin isolation verification
- Performance and scalability testing
- Error handling robustness
- Developer testing utilities
```

### Task List
- [ ] Create comprehensive integration tests for complete startup sequence
- [ ] Test plugin isolation and state partitioning works correctly
- [ ] Add error handling and recovery testing for all phases
- [ ] Test job processing integration with plugin system
- [ ] Verify configuration system integration works end-to-end
- [ ] Add performance testing for plugin loading and execution
- [ ] Create stress tests for job queue and state storage performance
- [ ] Add memory usage validation and leak detection
- [ ] Create plugin compatibility checker and validation tools
- [ ] Add error injection testing to validate system robustness
- [ ] PROMPT 16 COMPLETE

---

## PROMPT 17: Content Processing Pipeline Foundation

### Context
Begin implementing the content processing pipeline, starting with the ContentSource extension point that identifies resources to be processed.

### Task
```
Implement the ContentSource extension point and supporting infrastructure for identifying and scheduling content to be processed.

Requirements:
1. Create comprehensive ContentSource support:
   - Host implementation with scheduling capabilities
   - Integration with job queue for fetch scheduling
   - Configuration-driven resource discovery
2. Implement ContentSourceHost functionality:
   - schedule_fetch() method with job queue integration
   - schedule_next_run() for recurring sources
   - Configuration access for source parameters
3. Add source lifecycle management:
   - Start and stop source operations
   - Error handling and recovery
   - Resource cleanup
4. Create comprehensive tests:
   - Source scheduling and job creation
   - Lifecycle management
   - Configuration integration
   - Error handling
5. Add example ContentSource implementations
6. Include proper logging and monitoring

Focus on:
- Clean ContentSource interface implementation
- Robust job scheduling integration
- Proper lifecycle management
- Configuration-driven operation
- Comprehensive testing and validation
```

### Task List
- [ ] Implement ContentSourceHost with scheduling capabilities
- [ ] Add schedule_fetch() method with job queue integration
- [ ] Create schedule_next_run() for recurring source operations
- [ ] Implement source lifecycle management (start/stop operations)
- [ ] Add comprehensive error handling and recovery for sources
- [ ] Create example ContentSource implementations for testing
- [ ] Add comprehensive tests for source scheduling and job creation
- [ ] Test source lifecycle management and cleanup
- [ ] Verify configuration integration works for source parameters
- [ ] Add proper logging and monitoring for source operations
- [ ] PROMPT 17 COMPLETE

---

## PROMPT 18: Content Fetching Pipeline

### Context
Implement the ContentFetcher extension point that transforms URLs and paths into content for extraction.

### Task
```
Build the ContentFetcher extension point with proper URL/path handling and content retrieval capabilities.

Requirements:
1. Implement ContentFetcher support:
   - Host implementation with extraction integration
   - URL/path pattern matching and priority
   - Content retrieval with proper error handling
2. Create ContentFetcherHost functionality:
   - extract_file() method for content processing
   - Cache integration for fetched content
   - Metadata enrichment during fetch
3. Add fetcher selection logic:
   - can_fetch() evaluation and prioritization
   - First-match-wins with proper ordering
   - Fallback to general fetchers
4. Create comprehensive tests:
   - Fetcher selection and prioritization
   - Content retrieval and caching
   - Error handling and retry logic
   - Cache integration
5. Add example ContentFetcher implementations
6. Include job processing integration

Focus on:
- Flexible fetcher selection and prioritization
- Robust content retrieval with caching
- Proper integration with extraction pipeline
- Error handling and retry mechanisms
- Comprehensive testing of fetch scenarios
```

### Task List
- [ ] Implement ContentFetcherHost with extraction integration
- [ ] Add extract_file() method for processed content
- [ ] Create fetcher selection logic with can_fetch() evaluation
- [ ] Implement fetcher prioritization and first-match-wins behavior
- [ ] Add cache integration for fetched content storage
- [ ] Create comprehensive error handling and retry logic
- [ ] Add example ContentFetcher implementations (file, HTTP, etc.)
- [ ] Create comprehensive tests for fetcher selection and prioritization
- [ ] Test content retrieval, caching, and error handling
- [ ] Verify job processing integration works correctly
- [ ] PROMPT 18 COMPLETE

---

## PROMPT 19: Content Extraction Pipeline

### Context
Implement the ContentExtractor extension point that processes fetched content and stores it in the system.

### Task
```
Build the ContentExtractor extension point with content processing, storage integration, and recursive extraction support.

Requirements:
1. Implement ContentExtractor support:
   - Host implementation with storage and cache access
   - MIME type and extension-based selection
   - Content processing with metadata handling
2. Create ContentExtractorHost functionality:
   - Storage integration for processed content
   - Cache management for extracted content
   - Recursive extraction support (extract_file calls)
3. Add extractor selection logic:
   - can_extract() evaluation with MIME types
   - preferred_mime_types() prioritization
   - Fallback extraction strategies
4. Create comprehensive tests:
   - Extractor selection and prioritization
   - Content processing and storage
   - Recursive extraction scenarios
   - Cache and storage integration
5. Add example ContentExtractor implementations
6. Include metadata enrichment capabilities

Focus on:
- Flexible extractor selection by content type
- Robust content processing with storage
- Recursive extraction for complex content
- Proper metadata handling and enrichment
- Comprehensive testing of extraction scenarios
```

### Task List
- [ ] Implement ContentExtractorHost with storage and cache integration
- [ ] Add extractor selection logic using can_extract() and MIME types
- [ ] Create preferred_mime_types() prioritization system
- [ ] Implement recursive extraction support via extract_file() calls
- [ ] Add comprehensive storage integration for processed content
- [ ] Create cache management for extracted content
- [ ] Add example ContentExtractor implementations (text, HTML, etc.)
- [ ] Create comprehensive tests for extractor selection and processing
- [ ] Test recursive extraction scenarios (ZIP files, etc.)
- [ ] Verify storage and cache integration works correctly
- [ ] PROMPT 19 COMPLETE

---

## PROMPT 20: Job Processing Integration

### Context
Integrate the job processing system with the content pipeline to enable asynchronous processing of fetch and extract operations.

### Task
```
Create the job processing workers that handle the content pipeline jobs asynchronously and integrate with the plugin system.

Requirements:
1. Implement job processing workers:
   - fetch_content job handler
   - extract_content job handler
   - store_content job handler
   - cleanup_cache job handler
2. Create job processing coordination:
   - Worker lifecycle management
   - Job routing to appropriate plugins
   - Error handling and retry logic
3. Add job processing integration:
   - Integration with plugin hosts
   - Proper singleton access in workers
   - State management in job processing
4. Create comprehensive tests:
   - Job processing workflow
   - Error handling and retries
   - Plugin integration in workers
   - Performance and concurrency
5. Add job monitoring and observability
6. Include graceful shutdown for workers

Focus on:
- Asynchronous job processing integration
- Robust error handling and retry logic
- Proper plugin integration in workers
- Job processing performance and scalability
- Comprehensive testing of async workflows
```

### Task List
- [ ] Create job processing workers for each job type
- [ ] Implement fetch_content job handler with fetcher integration
- [ ] Add extract_content job handler with extractor integration
- [ ] Create store_content and cleanup_cache job handlers
- [ ] Add job processing coordination and routing logic
- [ ] Implement worker lifecycle management with graceful shutdown
- [ ] Add comprehensive error handling and retry logic for job processing
- [ ] Create integration between job workers and plugin hosts
- [ ] Add comprehensive tests for job processing workflows
- [ ] Test error handling, retries, and performance characteristics
- [ ] PROMPT 20 COMPLETE

---

## PROMPT 21: System Integration and End-to-End Testing

### Context
Integrate all components into a complete working system and create comprehensive end-to-end tests that validate the entire content processing pipeline.

### Task
```
Complete the system integration and create comprehensive end-to-end testing that validates the entire PAISE2 plugin system.

Requirements:
1. Create complete system integration:
   - Main application entry point
   - Complete startup and shutdown procedures
   - Integration of all subsystems
   - Configuration-driven operation
2. Add comprehensive end-to-end tests:
   - Complete content processing pipeline
   - ContentSource → Job Queue → ContentFetcher → ContentExtractor → Storage
   - Recursive extraction scenarios
   - Error recovery and resumability
3. Create system health and monitoring:
   - System status reporting
   - Performance metrics collection
   - Error reporting and alerting
4. Add deployment and packaging:
   - Proper CLI interface
   - Configuration management
   - Installation and setup procedures
5. Include comprehensive documentation:
   - System architecture overview
   - Plugin development guide
   - Configuration reference
   - Troubleshooting guide

Focus on:
- Complete system integration and validation
- End-to-end content processing pipeline
- System health and observability
- Production deployment readiness
- Comprehensive documentation
```

### Task List
- [ ] Create main application entry point with full system integration
- [ ] Implement complete startup and shutdown procedures
- [ ] Add comprehensive end-to-end tests for content processing pipeline
- [ ] Test complete flow: ContentSource → Fetcher → Extractor → Storage
- [ ] Verify recursive extraction scenarios work end-to-end
- [ ] Test error recovery and resumability across system restarts
- [ ] Add system health monitoring and status reporting
- [ ] Create performance metrics collection and monitoring
- [ ] Implement proper CLI interface with configuration management
- [ ] Add comprehensive system documentation and plugin development guide
- [ ] PROMPT 21 COMPLETE

---

## PROMPT 22: Resumability and Production Polish

### Context
Add resumability features and production-ready polish to the system, ensuring it can handle interruptions gracefully and restart cleanly.

### Task
```
Implement resumability features and add production-ready polish to create a robust, deployable system.

Requirements:
1. Complete resumability implementation:
   - Processing state tracking in metadata
   - Resume incomplete jobs on startup
   - Idempotent operations throughout
   - Cache-based deduplication
2. Add production polish:
   - Comprehensive error handling with isolation
   - Resource management and cleanup
   - Performance optimization
   - Memory usage optimization
3. Create operational tools:
   - System administration utilities
   - Backup and recovery procedures
   - Performance tuning guidance
   - Monitoring and alerting setup
4. Add comprehensive testing:
   - Resumability scenarios
   - Long-running system testing
   - Resource leak detection
   - Performance benchmarking
5. Final refactoring and cleanup:
   - Code quality improvements
   - Documentation completeness
   - Remove duplicate/unused code
   - Optimize for maintainability

Focus on:
- Complete resumability implementation
- Production-ready error handling
- System operational excellence
- Performance and resource optimization
- Final code quality and maintainability
```

### Task List
- [ ] Implement processing state tracking in metadata for resumability
- [ ] Add resume incomplete jobs logic on system startup
- [ ] Make all operations idempotent for safe resumption
- [ ] Implement cache-based deduplication to avoid duplicate work
- [ ] Add comprehensive error handling with proper isolation
- [ ] Create resource management and cleanup procedures
- [ ] Add performance optimization throughout the system
- [ ] Create system administration and operational utilities
- [ ] Add comprehensive testing for resumability scenarios
- [ ] Conduct final refactoring and cleanup for code quality
- [ ] PROMPT 22 COMPLETE

---

## Summary

This implementation plan provides 22 detailed, incremental prompts that build the PAISE2 plugin system from foundation to production-ready system. Each prompt:

- Builds incrementally on previous work
- Includes comprehensive testing requirements
- Focuses on clean architecture and best practices
- Ends with integrated, working functionality
- Includes refactoring to improve code quality

The plan ensures no orphaned code and maintains a test-driven approach throughout, resulting in a robust, extensible plugin system that meets the specification requirements.
