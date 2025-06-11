# Technical Context

## Purpose of this file
- Technologies used
- Development setup
- Technical constraints
- Dependencies
- Tool usage patterns

## Technology Stack

### Core Dependencies
- **Python 3.13+**: Minimum version for typing.Protocol support
- **uv**: Package manager for dependency management
- **pluggy**: Plugin system infrastructure and hook management
- **asyncio**: Asynchronous programming support for job processing
- **typing.Protocol**: Structural typing for extension point interfaces
- **dataclasses**: Immutable data structure definitions
- **PyYAML**: YAML configuration file processing

### Optional Dependencies
- **SQLite**: Persistent job queue and state storage (via built-in sqlite3)
- **pathlib**: Modern path handling (built-in)
- **logging**: Structured logging system (built-in)
- **uuid**: Unique identifier generation (built-in)

## Development Environment

### Package Management
- **uv** for dependency resolution and virtual environment management
- **pyproject.toml** for project configuration
- **uv.lock** for reproducible builds

### Code Quality Tools
- **mypy**: Static type checking - configured and passing in strict mode
- **pytest**: Testing framework - 147 tests passing
- **ruff**: Linting and formatting - configured with per-file ignores

### Development Setup
```bash
# Initialize project
cd paise2
uv venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
uv pip install -e .

# Run tests
uv run pytest

# Type checking
uv run mypy src/

# Linting
uv run ruff check

# All quality checks
uv run pytest && uv run mypy src/ && uv run ruff check
```

## Project Structure

### Directory Layout
```
paise2/
├── src/                         # Main package
│   ├── plugins/                    # Plugin system
│   │   ├── core/                   # Core plugin infrastructure
│   │   │   ├── interfaces.py       # Protocol definitions
│   │   │   ├── registry.py         # Plugin registration
│   │   │   ├── manager.py          # Plugin management
│   │   │   ├── hosts.py            # Host implementations
│   │   │   ├── startup.py          # Phased startup sequence
│   │   │   └── jobs.py             # Job processing infrastructure
│   │   ├── providers/              # Infrastructure providers
│   │   │   ├── config.py           # Configuration providers
│   │   │   ├── storage.py          # Storage providers
│   │   │   ├── jobs.py             # Job queue providers
│   │   │   ├── state.py            # State storage providers
│   │   │   └── cache.py            # Cache providers
│   ├── config/                     # Configuration management
│   │   ├── manager.py              # Configuration merging and loading
│   │   └── models.py               # Configuration data models
│   ├── storage/                    # Storage abstractions
│   │   └── models.py               # Storage data models
│   ├── state/                      # State management
│   │   └── models.py               # State management models
│   └── utils/                      # Common utilities
│       └── logging.py              # Logging utilities
├── tests/                          # Test suite
│   ├── unit/                       # Unit tests
│   └── integration/                # Integration tests
├── docs/                           # Documentation
│   ├── plugins/                    # Plugin system documentation
│   └── memory-bank/                # Memory bank files
└── pyproject.toml                  # Project configuration
```

### Module Organization
- **plugins/core**: Core plugin system infrastructure (interfaces, registration, management)
- **plugins/providers**: Default implementations of infrastructure providers
- **profiles**: Profile-based plugin loading system (production, development, test)
- **config**: Configuration loading and merging system
- **storage**: Data storage abstractions and models
- **state**: Plugin state management system
- **utils**: Common utilities and helper functions

### Test Structure
- **tests/fixtures**: Mock plugins and test data for development and testing
- **tests/unit**: Unit tests for all components

## Technical Constraints

### Performance Constraints
- **Single Desktop Device**: Designed for single-machine operation
- **Memory Efficient**: Avoid duplicating file content in database
- **Space Efficient**: Cache management with automatic cleanup
- **Resumable**: Can stop and restart without losing significant progress

### Scalability Constraints
- **Plugin Count**: System should handle dozens of plugins efficiently
- **Content Volume**: Handle thousands of documents without performance degradation
- **Job Processing**: Efficient job queue processing with minimal overhead

### Compatibility Constraints
- **Python Version**: Must support Python 3.8+ (no newer language features)
- **Platform**: Cross-platform support (Windows, macOS, Linux)
- **Dependencies**: Minimize external dependencies to reduce complexity

## Architecture Decisions

### Plugin System Design
- **pluggy Integration**: Use pluggy's hook system for plugin management
- **Protocol-Based**: Structural typing via typing.Protocol
- **Phased Loading**: 5-phase startup sequence for dependency management
- **Type Safety**: Static type checking and runtime validation

### Data Management
- **Immutable Data**: frozen dataclasses with copy/merge methods
- **Job Queue**: Asynchronous processing via job queue abstraction
- **State Partitioning**: Automatic plugin state isolation
- **Configuration Merging**: Plugin defaults + user overrides with list concatenation

### Error Handling
- **Fail Fast**: Initial implementation halts on plugin errors
- **Future Isolation**: Planned error isolation and recovery mechanisms
- **Retry Logic**: Job queue supports retry mechanisms for transient failures

## Integration Patterns

### Plugin Discovery
```python
# Internal plugin discovery via AST scanning
def discover_internal_plugins():
    for module in scan_paise2_modules():
        for func in get_hookimpl_functions(module):
            register_plugin_function(func)

# External plugin discovery via pluggy
def discover_external_plugins():
    pm = pluggy.PluginManager("paise2")
    pm.add_hookspecs(PluginHooks)
    pm.load_setuptools_entrypoints()
```

### Host Interface Integration
```python
# Base host provides common services
class BaseHost:
    def __init__(self, singletons: Singletons, plugin_module: str):
        self.logger = singletons.logger
        self.configuration = singletons.configuration
        self.state = StateManager(singletons.state_storage, plugin_module)

# Specialized hosts extend base functionality
class ContentExtractorHost(BaseHost):
    def __init__(self, singletons: Singletons, plugin_module: str):
        super().__init__(singletons, plugin_module)
        self.storage = singletons.storage
        self.cache = singletons.cache
```

### Job Queue Integration
```python
# Providers create job queue implementations
class JobQueueProvider(Protocol):
    def create_job_queue(self, configuration: Configuration) -> JobQueue

# Job queue handles async processing
async def process_jobs():
    while True:
        job = await job_queue.dequeue(worker_id)
        if job:
            await process_job(job)
            await job_queue.complete(job.job_id)
```

### State Storage Integration
```python
# State storage with automatic partitioning
class StateStorage(Protocol):
    def store(self, partition_key: str, key: str, value: Any, version: int) -> None
    def get(self, partition_key: str, key: str, default: Any = None) -> Any

# Automatic partitioning by plugin module name
class StateManager:
    def __init__(self, storage: StateStorage, plugin_module: str):
        self.storage = storage
        self.plugin_module = plugin_module

    def store(self, key: str, value: Any, version: int = 1) -> None:
        self.storage.store(self.plugin_module, key, value, version)
```

## Development Workflow

### Adding New Extension Point
1. Define Protocol in `plugins/core/interfaces.py`
2. Add registration hook in `plugins/core/registry.py`
3. Update plugin manager in `plugins/core/manager.py`
4. Create host interface if needed in `plugins/core/hosts.py`
5. Add to appropriate startup phase in `plugins/core/startup.py`
6. Write unit tests and integration tests

### Adding New Plugin
1. Implement Protocol interface
2. Create registration function with `@hookimpl`
3. Add default configuration if needed
4. Write unit tests for plugin functionality
5. Add integration tests for plugin interaction
6. Document plugin capabilities and usage

### Testing Strategy
- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test component interactions and full flows
- **Plugin Tests**: Test plugin implementations and registration
- **Host Tests**: Test host interface implementations
- **Configuration Tests**: Test configuration merging and access

## Current Implementation Status

### Completed Components (as of December 19, 2024)
- ✅ **Core Data Models**: Immutable Metadata dataclass with copy/merge methods in `src/paise2/models.py`
- ✅ **Type System**: ItemId, JobId, CacheId, Content, Logger, Configuration type aliases
- ✅ **Protocol Interfaces**: Complete protocol system in `src/paise2/plugins/core/interfaces.py`
  - Phase 2 singleton-contributing protocols: ConfigurationProvider, DataStorageProvider, JobQueueProvider, StateStorageProvider, CacheProvider
  - Phase 4 singleton-using protocols: ContentExtractor, ContentSource, ContentFetcher, LifecycleAction
  - Complete host interface hierarchy: BaseHost → ContentExtractorHost, ContentSourceHost, ContentFetcherHost, LifecycleActionHost
  - Supporting protocols: StateStorage, StateManager, JobQueue, Job dataclass
- ✅ **Plugin Registration System**: PluginManager with plugin system integration, plugin discovery, and validation
- ✅ **Host Infrastructure**: BaseHost and ConcreteStateManager with automatic state partitioning
- ✅ **Configuration Management System**: Complete configuration package with FileConfigurationProvider, ConfigurationManager, and YAML support
- ✅ **Configuration Integration System**: ConfigurationFactory for singleton creation, plugin registration enhancements, and comprehensive integration testing
- ✅ **Configuration Diffing System**: ConfigurationDiffer and EnhancedMergedConfiguration with startup diffing design
- ✅ **Testing Infrastructure**: 129 comprehensive tests covering all components including configuration integration and diffing
- ✅ **Code Quality**: Modern Python typing, pathlib.Path usage, code style compliance, comprehensive documentation
- ✅ **Bootstrap Logging**: SimpleInMemoryLogger for early development phases

### Ready for Implementation (PROMPT 8)
- ⏳ **State Storage Provider System**: SQLite-based state storage with partitioning and versioning
- ⏳ **State Persistence**: Enable state storage for plugins and system configuration
- ⏳ **Startup Configuration Diffing**: Implement configuration state persistence and cross-session change detection
- ⏳ **State Management Integration**: Integrate state storage with plugin system and hosts

### Development Workflow Status
- **Quality Assurance**: All 129 tests passing, ruff linting clean (mypy has test annotation issues but core code is clean)
- **Code Standards**: Modern Python 3.9+ typing with pathlib.Path usage throughout
- **Documentation**: Comprehensive docstrings for all protocols and public interfaces
- **Test Coverage**: Protocol compliance validation and comprehensive functionality testing including configuration integration and diffing
- **Integration Testing**: Configuration integration patterns fully tested with singleton creation, plugin interaction, and configuration diffing
