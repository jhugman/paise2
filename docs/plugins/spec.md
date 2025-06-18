# PAISE2 Plugin System - Comprehensive Developer Specification

## Overview

PAISE2 is a search engine indexer designed to run on a single desktop-class device. The plugin system allows users to extend the system and enables easy authorship of plugins.

The system is designed to handle a dynamically changing environment (e.g., using directory watchers), but the initial implementation focuses on getting something working first. The indexer is space-efficient: when indexing local files, file content is not copied into a database.

## Nomenclature

- **Plugins** are discrete units of code that could be from different repositories, installable via pip/uv, or built-in
- **Extension points** are interfaces that the host application defines, implemented as hookspec functions
- **Extensions** are implementations of extension point interfaces that plugins provide

Plugins can provide multiple extensions for one or more different extension points.

## System Architecture Principles

### Core Design Decisions
1. **Protocol-based interfaces**: Use `typing.Protocol` for structural typing rather than inheritance
2. **Native plugin registration**: Separate registration hooks for each extension type for type safety
3. **Base host class pattern**: Common host functionality with type-specific extensions
4. **Merged configuration**: All plugins can access entire merged configuration
5. **Automatic state partitioning**: Plugin state isolated by plugin module name without explicit name spacing
6. **Dependency injection**: Singletons created by plugin system and injected into hosts
7. **Minimal extension points**: Only Protocol + registration hook required, additional infrastructure added on-demand
8. **Simple load ordering**: Discovery order for plugins within same phase (can be enhanced later)
9. **Immutable data objects**: All data structures use immutable patterns with copy/merge methods
10. **Resumable operations**: System can restart and resume processing with minimal duplicate work
11. **Task-based processing**: Most operations are handled through a task queue system
12. **Pluggable infrastructure**: Task queues, state storage, and caches are provided by plugins

### Plugin Discovery

- **Internal plugins**: Scan entire paise2 codebase for modules containing `@hookimpl` decorated functions
- **External plugins**: Use pluggy's standard discovery mechanisms for third-party plugins
- **Load order**: Simple discovery order within each phase (first found, first loaded)

#### Profile-Based Plugin Loading

The plugin system supports profile-based loading for context-dependent plugin selection. Profiles (`production`, `development`, `test`) contain different plugin combinations to eliminate singleton provider selection complexity.

```python
from paise2.profiles.factory import create_test_plugin_manager
plugin_manager = create_test_plugin_manager()
```

### Extension Point-Based Startup Sequence

The system uses a phased startup approach segmented by extension point types to handle the delicate startup sequence when singletons are contributed to by plugins:

#### Phase 1: Bootstrap
```python
# Create minimal in-memory logger for plugin system startup
bootstrap_logger = SimpleInMemoryLogger()
plugin_system = PluginSystem(bootstrap_logger)
```

#### Phase 2: Singleton-Contributing Extension Points
Load extension points that contribute to system singletons:
```python
plugin_system.load_extension_point("ConfigurationProvider")
plugin_system.load_extension_point("DataStorageProvider")
plugin_system.load_extension_point("TaskQueueProvider")
plugin_system.load_extension_point("StateStorageProvider")
plugin_system.load_extension_point("CacheProvider")
```

#### Phase 3: Singleton Creation
Create singletons from loaded extensions:
```python
configuration = create_configuration_from_providers()
task_queue = create_task_queue_from_providers(configuration)
state_storage = create_state_storage_from_providers(configuration)
cache = create_cache_from_providers(configuration)
storage = create_storage_from_providers(configuration)
logger = create_logger(configuration)
logger.replay_logs(bootstrap_logger.get_logs())  # Replay bootstrap logs
```

#### Phase 4: Singleton-Using Extension Points
Load remaining extension points with full singleton support:
```python
singletons = Singletons(plugin_system, logger, configuration, storage, task_queue, state_storage, cache)
# The ordering is important here; the exact mechanisms are illustrative.
content_extractors = ContentExtractorHostCreator(singletons)
content_fetchers = ContentFetcherHostCreator(singletons, content_extractors)
content_sources = ContentSourceHostCreator(singletons, content_fetchers)
```

#### Phase 5: Start!
```python
content_sources.start()
```

## Extension Points

Extension points are categorized by their startup requirements:

### Phase 2: Singleton-Contributing Extension Points

These extension points contribute to system singletons and must be loaded first.

#### ConfigurationProviders

ConfigurationProviders allow plugins to contribute default configuration files. When the system reloads configuration, it looks for configuration for each provider, and if not found, uses the default.

```python
from typing import Protocol

class ConfigurationProvider(Protocol):
    def get_default_configuration(self) -> str: ...  # YAML string with comments
    def get_configuration_id(self) -> str: ...
```

**Default Implementation Available:**
```python
class FileConfigurationProvider(ConfigurationProvider):
    def __init__(self, file_path: str, plugin_module=None):
        # Handle relative paths to plugin module if provided
        if plugin_module and not os.path.isabs(file_path):
            module_dir = os.path.dirname(os.path.abspath(plugin_module.__file__))
            self.file_path = os.path.join(module_dir, file_path)
        else:
            self.file_path = file_path
        self._config_id = os.path.basename(file_path)

    def get_default_configuration(self) -> str: ...
    def get_configuration_id(self) -> str: ...
```

#### DataStorageProvider

DataStorageProviders allow plugins to contribute a metadata storage layer. The DataStorage component stores metadata about indexed content, but the actual content is stored elsewhere (in cache or original location) to minimize disk usage and avoid duplication. Storage implementations process both text and binary data through the Content type (Union[bytes, str]) for computing derived data (like content hashes or embeddings), but do not store the actual content.

```python
from typing import Optional, List, Union

class DataStorageProvider(Protocol):
    def create_data_storage(self, configuration: Configuration) -> DataStorage: ...

class DataStorage(Protocol):
    async def add_item(self, host: DataStorageHost, content: Content, metadata: Metadata) -> ItemId: ...
    async def update_item(self, host: DataStorageHost, item_id: ItemId, content: Content) -> None: ...
    async def update_metadata(self, host: DataStorageHost, item_id: ItemId, metadata: Metadata) -> None: ...
    async def find_item_id(self, host: BaseHost, metadata: Metadata) -> Optional[ItemId]: ...  # Accepts any BaseHost for read-only operations
    async def find_item(self, item_id: ItemId) -> Metadata: ...
    async def remove_item(self, host: DataStorageHost, item_id: ItemId) -> Optional[CacheId]: ...
    async def remove_items_by_metadata(self, host: DataStorageHost, metadata: Metadata) -> List[CacheId]: ...
    async def remove_items_by_url(self, host: DataStorageHost, url: str) -> List[CacheId]: ...
```

#### TaskQueueProvider

TaskQueueProviders configure Huey task queue instances for different deployment environments. The system uses [Huey](https://huey.readthedocs.io/) directly without additional abstraction layers.

```python
from huey import SqliteHuey, RedisHuey

class TaskQueueProvider(Protocol):
    def create_task_queue(self, configuration: Configuration) -> Huey: ...
```

**Profile-Based Configuration:**

Different profiles provide different Huey configurations:

- **Test Profile**: `NoTaskQueueProvider` for synchronous execution in tests
- **Development Profile**: `HueySQLiteTaskQueueProvider` with SQLite backend
- **Production Profile**: `HueyRedisTaskQueueProvider` with Redis backend

**Provider Implementations:**

```python
# For testing - synchronous execution
class NoTaskQueueProvider(TaskQueueProvider):
    def create_task_queue(self, configuration: Configuration) -> Huey:
        # Return None for synchronous execution
        return None

# For development - SQLite backend
class HueySQLiteTaskQueueProvider(TaskQueueProvider):
    def __init__(self, immediate: bool = False):
        self.immediate = immediate

    def create_task_queue(self, configuration: Configuration) -> Huey:
        db_path = configuration.get("task_queue.sqlite_path", "~/.local/share/paise2/tasks.db")
        return SqliteHuey(
            "paise2",
            filename=Path(db_path).expanduser(),
            immediate=self.immediate,
            results=True,
            utc=True
        )

# For production - Redis backend
class HueyRedisTaskQueueProvider(TaskQueueProvider):
    def create_task_queue(self, configuration: Configuration) -> Huey:
        return RedisHuey(
            "paise2",
            host=configuration.get("redis.host", "localhost"),
            port=configuration.get("redis.port", 6379),
            db=configuration.get("redis.db", 0),
            immediate=False,
            results=True
        )
```

**Task Definition:**

Tasks are defined separately after singletons are created:

```python
def setup_tasks(huey: Huey, singletons: Singletons) -> dict[str, Callable]:
    """Define tasks with the provided Huey instance and singletons."""

    if huey is None:
        # No tasks for synchronous execution
        return {}

    @huey.task()
    def fetch_content_task(url: str, metadata: dict | None = None):
        """Fetch content using appropriate ContentFetcher plugin."""
        fetcher_host = ContentFetcherHost(singletons)
        fetchers = singletons.plugin_manager.get_registered_content_fetchers()

        for fetcher in fetchers:
            if await fetcher.can_fetch(url):
                content = await fetcher.fetch(fetcher_host, url)

                # Enqueue extraction task
                metadata_obj = Metadata.from_dict(metadata) if metadata else Metadata()
                extract_content_task(content, metadata_obj.to_dict())

                return {"status": "success", "content_length": len(content)}

        return {"status": "error", "message": "No fetcher found for URL"}

    @huey.task()
    def extract_content_task(content: bytes | str, metadata: dict):
        """Extract content using appropriate ContentExtractor plugin."""
        extractor_host = ContentExtractorHost(singletons)
        extractors = singletons.plugin_manager.get_registered_content_extractors()

        metadata_obj = Metadata.from_dict(metadata)

        for extractor in extractors:
            if await extractor.can_extract(content, metadata_obj):
                extracted = await extractor.extract(extractor_host, content, metadata_obj)

                return {"status": "success", "extracted_items": len(extracted)}

        return {"status": "error", "message": "No extractor found for content"}

    @huey.task()
    def store_content_task(content: dict, metadata: dict):
        """Store processed content in the data storage."""
        storage_host = DataStorageHost(singletons)
        # Implementation details...
        return {"status": "success"}

    @huey.task()
    def cleanup_cache_task(cache_ids: list[str]):
        """Clean up specified cache entries."""
        # Implementation details...
        return {"status": "success", "cleaned": len(cache_ids)}

    return {
        "fetch_content": fetch_content_task,
        "extract_content": extract_content_task,
        "store_content": store_content_task,
        "cleanup_cache": cleanup_cache_task,
    }
```

**Host Integration:**

Hosts enqueue tasks using the configured task queue:

```python
class ContentSourceHost(BaseHost):
    def __init__(self, singletons: Singletons):
        super().__init__(singletons)

    def schedule_fetch(self, url: str, metadata: Metadata | None = None):
        """Schedule a content fetch task."""
        if self._singletons.task_queue is None:
            # Synchronous execution for testing
            return self._fetch_synchronously(url, metadata)

        # Enqueue async task
        task_data = {"url": url, "metadata": metadata.to_dict() if metadata else None}
        result = self._singletons.tasks["fetch_content"](**task_data)

        self.logger.info(f"Enqueued fetch task for {url}")
        return result.id if hasattr(result, 'id') else None

class ContentFetcherHost(BaseHost):
    def extract_file(self, content: Content, metadata: Metadata):
        """Schedule content extraction task."""
        if self._singletons.task_queue is None:
            # Synchronous execution for testing
            return self._extract_synchronously(content, metadata)

        # Enqueue async task
        task_data = {"content": content, "metadata": metadata.to_dict()}
        result = self._singletons.tasks["extract_content"](**task_data)

        return result.id if hasattr(result, 'id') else None
```

**Worker Process:**

Workers use the same application setup to ensure identical plugin configuration:

```python
# worker.py
def run_worker(profile: str = "production"):
    """Start a Huey worker process."""

    # Initialize the same plugin system as main app
    singletons = setup_application(profile)

    # Start the Huey consumer
    if singletons.task_queue:
        singletons.task_queue.run_consumer()
    else:
        raise RuntimeError("No Huey instance available for worker")

def setup_application(profile: str) -> Singletons:
    """Common setup used by both main app and workers."""
    plugin_manager = create_plugin_manager_from_profile(profile)
    configuration = create_configuration_from_providers(plugin_manager)

    # Create all singletons except task queue
    storage = create_storage_from_providers(configuration)
    cache = create_cache_from_providers(configuration)
    state_storage = create_state_storage_from_providers(configuration)

    # Create task queue (just Huey instance)
    task_queue = create_task_queue_from_providers(configuration)

    # Create singletons with incomplete task setup
    singletons = Singletons(plugin_manager, logger, configuration, storage, task_queue, state_storage, cache)

    # Setup tasks and store them in singletons
    tasks = setup_tasks(task_queue, singletons)
    singletons.tasks = tasks

    return singletons

if __name__ == "__main__":
    run_worker()
```

**Configuration:**

Task queue behavior is controlled through configuration:

```yaml
# Development configuration
task_queue:
  provider: "sqlite"
  sqlite_path: "~/.local/share/paise2/dev_tasks.db"
  immediate: true  # Execute tasks immediately for debugging

# Production configuration
task_queue:
  provider: "redis"
  redis:
    host: "localhost"
    port: 6379
    db: 0
```

#### StateStorageProvider

StateStorageProviders allow plugins to contribute state storage implementations.

```python
class StateStorageProvider(Protocol):
    def create_state_storage(self, configuration: Configuration) -> StateStorage: ...

class StateStorage(Protocol):
    def store(self, partition_key: str, key: str, value: Any, version: int = 1) -> None: ...
    def get(self, partition_key: str, key: str, default: Any = None) -> Any: ...
    def get_versioned_state(self, partition_key: str, older_than_version: int) -> List[Tuple[str, Any, int]]: ...
    def get_all_keys_with_value(self, partition_key: str, value: Any) -> List[str]: ...
```

#### CacheProvider

CacheProviders allow plugins to contribute cache implementations.

```python
class CacheProvider(Protocol):
    def create_cache(self, configuration: Configuration) -> CacheManager: ...

class CacheManager(Protocol):
    async def save(self,
        partition_key: str,
        content: Content,
        file_extension: str = ""
    ) -> CacheId: ...
    async def get(self, cache_id: CacheId) -> Content: ...
    async def remove(self, cache_id: CacheId) -> bool: ...
    async def remove_all(self, cache_ids: List[CacheId]) -> List[CacheId]: ...
    async def get_all(self, partition_key: str) -> List[CacheId]: ...
```

A facade cache manager, ExtensionCacheManager is given to the extensions via the hosts which provides the same interface, but fills in the partition key.

```python
class ExtensionCacheManager:
    __init__(cache_manager: CacheManager, partition_key: str): ...
        async def save(self,
        content: Content,
        file_extension: str = ""
    ) -> CacheId: ...
    async def get(self, cache_id: CacheId) -> Content: ...
    # ..etc.
```

### Phase 4: Singleton-Using Extension Points

These extension points use system singletons and are loaded after singletons are created.

#### ContentExtractors

ContentExtractors know how to extract one or more content items from a given file. They are called after content is fetched, with the host system identifying the best extension based on file extension, MIME type, and heuristics.

Examples:
- Extract text from a single HTML file and add to index
- Split an EPUB file into chapters and add each to index
- Transcribe an audio file and add to index

```python
from typing import Protocol, List, Union, Optional

class ContentExtractor(Protocol):
    def can_extract(self, url: str, mime_type: str = None) -> bool: ...
    def preferred_mime_types(self) -> List[str]: ...
    async def extract(self, host: ContentExtractorHost, content: Union[bytes, str], metadata: Optional[Metadata] = None) -> None: ...
```

#### ContentSources

ContentSources extract lists of files or URLs from human-writable local configuration. They take app configuration (YAML files) and derive a list of files to fetch, using the host to schedule those files for fetching.

ContentSources have read-only access to the data storage through the host to check for existing content and avoid duplicate fetching. This enables efficient resumable operations where the system can restart without re-processing content that already exists.

Examples:
- Take directory lists from config and set up file watchers
- Read Firefox places.db and schedule bookmark fetching

```python
class ContentSource(Protocol):
    async def start_source(self, host: ContentSourceHost) -> None: ...
    async def stop_source(self, host: ContentSourceHost) -> None: ...
```

#### ContentFetchers

ContentFetchers transform URLs or file paths into content for the ContentExtractor system. The host system chooses the best extension using scheme, URL patterns, or extension-specific methods.

Examples:
- Load file from disk
- Fetch file from internet
- Fetch file using authenticated API (e.g., Google Docs)
- Fetch repository from GitHub

```python
class ContentFetcher(Protocol):
    def can_fetch(self, url: str) -> bool: ...
    async def fetch(self, host: ContentFetcherHost, url: str) -> None: ...
```

Fetchers are tried in order, with the first one to match wins. The most general one should be tried last, the most specific first. The system should define these first and last resorts.

#### LifecycleAction

LifecycleActions handle system startup and shutdown with full access to the configured system:

```python
class LifecycleAction(Protocol):
    async def startup(self, host: LifecycleActionHost) -> None: ...
    async def shutdown(self, host: LifecycleActionHost) -> None: ...
```

Example implementations:

```python
class WorkerLifecycleAction:
    """Manages Huey worker processes."""

    def __init__(self):
        self.worker_processes = []

    async def startup(self, host: LifecycleActionHost) -> None:
        singletons = host.singletons
        if singletons.task_queue.huey:
            # Start background worker processes
            import subprocess
            worker_process = subprocess.Popen([
                "python", "-m", "paise2.worker",
                "--profile", singletons.configuration.get("profile", "production")
            ])
            self.worker_processes.append(worker_process)

    async def shutdown(self, host: LifecycleActionHost) -> None:
        for process in self.worker_processes:
            process.terminate()
            process.wait()
```

## Extension Registration

Extensions are registered using pluggy's native approach with separate registration hooks for each extension type:

```python
from typing import Callable

class Plugin:
    @hookimpl
    def register_lifecycle_action(self, register: Callable[[LifecycleAction], None]) -> None: ...
    @hookimpl
    def register_configuration_provider(self, register: Callable[[ConfigurationProvider], None]) -> None: ...
    @hookimpl
    def register_content_extractor(self, register: Callable[[ContentExtractor], None]) -> None: ...
    @hookimpl
    def register_content_source(self, register: Callable[[ContentSource], None]) -> None: ...
    @hookimpl
    def register_content_fetcher(self, register: Callable[[ContentFetcher], None]) -> None: ...
    @hookimpl
    def register_data_storage_provider(self, register: Callable[[DataStorageProvider], None]) -> None: ...
    @hookimpl
    def register_task_queue_provider(self, register: Callable[[TaskQueueProvider], None]) -> None: ...
    @hookimpl
    def register_state_storage_provider(self, register: Callable[[StateStorageProvider], None]) -> None: ...
    @hookimpl
    def register_cache_provider(self, register: Callable[[CacheProvider], None]) -> None: ...

@hookimpl
def register_plugin(register):
    register(Plugin())
```

## Host Interfaces

Each extension type interacts with the system through a specialized host interface. Host interfaces use a base class pattern with extensions for type-specific methods.

### Base Host Interface

All host interfaces inherit from a common base that provides shared functionality:

```python
from datetime import timedelta
from pathlib import Path

class BaseHost:
    @property
    def logger(self) -> Logger: ...

    @property
    def configuration(self) -> Configuration: ...

    # Segmented state (automatically partitioned by plugin module name)
    @property
    def state(self) -> StateManager: ...

    def schedule_fetch(self, url: str, metadata: Metadata | None = None) -> None: ...
```

### Specialized Host Interfaces

```python
class ContentExtractorHost(BaseHost):
    @property
    def storage(self) -> DataStorage: ...
    @property
    def cache(self) -> ExtensionCacheManager: ...

    def extract_file(self, content: Union[bytes, str], metadata: Metadata) -> None: ...

class ContentSourceHost(BaseHost):
    @property
    def cache(self) -> ExtensionCacheManager: ...
    @property
    def data_storage(self) -> DataStorage: ...
    def schedule_next_run(self, time_interval: timedelta) -> None: ...

class ContentFetcherHost(BaseHost):
    @property
    def cache(self) -> ExtensionCacheManager: ...

    def extract_file(self, content: Union[bytes, str], metadata: Metadata) -> None: ...

class DataStorageHost(BaseHost):
    pass

class LifecycleHost(BaseHost):
    pass
```

### State Manager Interface

The state manager provides automatic partitioning by plugin module name:

```python
class StateManager:
    def __init__(self, state_storage: StateStorage, plugin_module_name: str):
        self.state_storage = state_storage
        self.partition_key = plugin_module_name

    def store(self, key: str, value: Any, version: int = 1) -> None:
        self.state_storage.store(self.partition_key, key, value, version)

    def get(self, key: str, default: Any = None) -> Any:
        return self.state_storage.get(self.partition_key, key, default)

    def get_versioned_state(self, older_than_version: int) -> List[Tuple[str, Any, int]]:
        return self.state_storage.get_versioned_state(self.partition_key, older_than_version)

    def get_all_keys_with_value(self, value: Any) -> List[str]:
        return self.state_storage.get_all_keys_with_value(self.partition_key, value)
```

## Plugin Flow

The typical flow through the plugin system is:

1. A ContentSource plugin identifies resources and calls `schedule_fetch()`
2. The ContentSourceHost creates a "fetch_content" task via the task queue
3. A task worker picks up the fetch task and identifies an appropriate ContentFetcher
4. The ContentFetcher fetches the content and calls `extract_file()`
5. The ContentFetcherHost creates an "extract_content" task via the task queue
6. A task worker picks up the extract task and identifies an appropriate ContentExtractor
7. The ContentExtractor processes the content and may:
   - Call `storage.add_item()` for extracted content
   - Call `host.extract_file()` for recursive extraction (e.g., files within ZIP archives)
   - Call `schedule_fetch()` for additional resources
8. The system routes each item through any configured metadata enrichers
9. The enriched content is added to the search index

### Recursive Extraction Example

For a ZIP file containing multiple documents:

1. **ContentFetcher** downloads ZIP bytes
2. **ContentFetcher** calls `host.extract_file()` with ZIP bytes and metadata
3. **ZipContentExtractor** receives ZIP, extracts individual files
4. **ZipContentExtractor** calls `host.extract_file()` for each extracted file
5. Appropriate ContentExtractors handle each file type (PDF, HTML, etc.)

The host always goes through the full ContentExtractor selection process for recursive extractions.

### Task-Based Processing

Most operations are handled through the task queue system:

```python
# In ContentSourceHost
def schedule_fetch(self, url: str, metadata: Optional[Metadata] = None):
    task_data = {"url": url, "metadata": metadata}
    await self._task_queue.enqueue("fetch_content", task_data, priority=1)

# In ContentFetcherHost
def extract_file(self, content: Content, metadata: Metadata):
    job_data = {"content": content, "metadata": metadata}
    await self._job_queue.enqueue("extract_content", job_data, priority=2)
```

## Plugin State Management

Plugins can persist state between runs using the host's state management:
- `state.store(key, value)` - Save plugin-specific state
- `state.get(key, default=None)` - Retrieve previously stored state

**Key Features:**
- State is automatically partitioned by plugin module name (e.g., `paise2.plugins.extractors.pdf`)
- No explicit name spacing required
- Supports versioning for re-indexing when plugins update
- Can query state across versions for cleanup/migration
- Can get all keys with specific state values

**Versioning API:**
```python
# Get all key-value pairs for versions older than X, with their versions
old_state = state.get_versioned_state(older_than_version=5)

# Re-index items when plugin updates
for key, value, version in old_state:
    if version < current_version:
        # Re-process this item
        pass
```

## Configuration System

Configuration uses a merged approach where all plugins can access the entire configuration.

### Key Features
- Merges plugin default configurations with user configurations
- User configuration stored in directory defined by $PAISE_CONFIG_DIR (by default ~/.config/paise).
- Uses YAML format for all configuration files
- Provides access via `host.configuration` property
- Supports dynamic reloading with diff detection and state persistence
- Exposes configuration changes to plugins via Configuration protocol

### Configuration Merging Rules

1. **Plugin-to-plugin merging**: Later discovered plugins override earlier ones for scalar values
2. **List concatenation**: Lists from different plugins are merged together
3. **User overrides**: User settings completely override plugin defaults for the same keys
4. **Comment preservation**: Comments from default configuration are preserved when copying to user config
5. **Dictionary merging**: Dictionaries are merged recursively

### Configuration Access
```python
# In any extension
max_size = host.configuration.get("plugin_name.max_file_size", default=1024)
global_setting = host.configuration.get("global.log_level", default="INFO")
```

### Configuration Reloading and Diffing

The configuration system supports dynamic reloading with diff detection to notify plugins about configuration changes.

#### Configuration State Persistence

When the configuration system initializes, it saves the merged configuration state for comparison during future reloads:

1. **Merged state storage**: The final merged configuration (plugin defaults + user overrides) is persisted
2. **State comparison**: During reload operations, the new merged configuration is compared against the previous state
3. **Diff calculation**: The system calculates tree-based differences including additions, removals, and modifications

#### Configuration Diff Detection

The system provides detailed diff information accessible via the Configuration protocol:

```python
# Configuration diff structure
@dataclass(frozen=True)
class ConfigurationDiff:
    added: dict[str, Any]      # New configuration keys/sections
    removed: dict[str, Any]    # Removed configuration keys/sections
    modified: dict[str, Any]   # Changed configuration values
    unchanged: dict[str, Any]  # Configuration that remained the same

# Access diffs via Configuration protocol
class Configuration(Protocol):
    def get(self, key: str, default: Any) -> Any | None:
        ...

    def addition(self, key: str, default: T | None = None) -> T | None:
        """Get the additions at the key path, or the default if none exist at that path"""
        ...

    def removal(self, key: str, default: T | None = None) -> T | None:
        """Get the removals at the key path, or the default if none exist at that path"""
        ...

    def has_changed(self, key: str) -> bool:
        """Check if a specific configuration key changed in the last reload."""
        ...

    @property
    def last_diff(self): ConfigurationDiff | None
```

#### Configuration Change Notifications

Plugins can be notified of configuration changes through the Configuration protocol:

1. **Diff availability**: After a reload, `get_last_diff()` returns the differences between old and new configuration
2. **Key-specific checks**: Use `has_changed("plugin.setting")` to check if specific settings changed
3. **Comprehensive change detection**: Diffs include nested dictionary changes, list modifications, and scalar value updates

#### Configuration Reload Workflow

1. **Trigger reload**: Configuration reload can be triggered by file system changes or explicit API calls
2. **Collect current state**: Gather plugin default configurations and current user overrides
3. **Merge new configuration**: Apply the same merging rules to create new merged configuration
4. **Calculate diff**: Compare new merged state against previously saved state
5. **Update state**: Replace the current configuration state with the new merged configuration
6. **Expose diffs**: Make diff information available to plugins via the Configuration protocol

#### Usage Examples

```python
# Check for configuration changes in a plugin
def on_configuration_reload(self, host):
    config = host.configuration
    diff = config.get_last_diff()

    if diff and config.has_changed("my_plugin.api_key"):
        # Reinitialize API client with new key
        self.api_client = APIClient(config.get("my_plugin.api_key"))

    if diff and diff.added:
        # Handle new configuration sections
        for key, value in diff.added.items():
            self.handle_new_config(key, value)
```

This configuration diffing system enables plugins to react efficiently to configuration changes without needing to reload or reinitialize unnecessarily.

#### Startup Configuration Diffing

**Enhanced Feature**: The configuration system also provides diff detection during application startup by comparing the current configuration against the configuration from the previous application run.

**State Storage Integration**: The previous application's merged configuration is persisted using the StateStorage system under a special system partition key (`_system.configuration.last_merged`), enabling cross-session configuration change detection.

**Startup Sequence Integration**: Configuration diffing is integrated into the phased startup sequence:

1. **Phase 2**: Load singleton-contributing extensions (including StateStorageProvider)
2. **Phase 3**: Create StateStorage singleton
3. **Phase 3**: Create Configuration singleton:
   - Collect and merge current configuration
   - Retrieve previous configuration from StateStorage
   - Calculate diff between previous and current configuration
   - Store current configuration in StateStorage for next startup
   - Expose diff via Configuration protocol

**Plugin Benefits**: This enables plugins to detect configuration changes across application restarts:

```python
def on_startup(self, host):
    config = host.configuration
    diff = config.last_diff

    if diff and config.has_changed("my_plugin.extraction_rules"):
        # Plugin's extraction rules changed, re-indexing existing content
        logger.info("Extraction rules changed, scheduling re-indexing")
        for item_id in host.state.get_all_keys_with_value("extracted"):
            host.schedule_job("re_extract", {"item_id": item_id})

    elif diff and config.has_changed("my_plugin.cache_settings"):
        # Cache settings changed, invalidate plugin cache
        host.cache.clear_partition("my_plugin")

    elif not diff:
        # No configuration changes, resume normal operations
        logger.info("Configuration unchanged, resuming from previous state")
```

**Use Cases**:
- **Plugin Updates**: Detect when plugin defaults change and trigger re-processing
- **State Migration**: Use configuration changes to trigger state schema migrations
- **Cache Invalidation**: Clear caches when configuration affects cached data
- **Resume vs Restart Logic**: Differentiate between configuration-driven restarts and simple resumes

## Cache Management

Plugins have access to a cache, which is segmented by plugin module name. By default it's a file-based cache.

### Cache Usage

Two primary uses for caching:
- Caching expensive computations (e.g., LLM summaries for long documents)
- Caching fetched documents

When saving documents into the cache, the cache manager returns a cache id. This is a serializable opaque identifier.

Cache ids are added to the metadata as `location` of a document before being given to the data storage.

### Cache Cleanup

When DataStorage removes an item—which may include multiple subitems—a list of cache ids are returned. The host automatically handles cache cleanup by calling `cache.remove_all()` with the returned cache IDs.

## Resumable Operations

The system supports stopping and starting with minimal duplicated work:

### Resumability Strategy

1. **Processing state tracking**: Add `processing_state` field to Metadata ("pending", "fetching", "extracting", "completed")
2. **Job-based resumption**: On startup, query job queue for incomplete jobs and resume processing
3. **Storage-based deduplication**: ContentSources check data storage before scheduling fetches to avoid duplicates
4. **Idempotent operations**: Make storage operations safe to repeat (add_item checks for existing items first)
5. **Automatic cleanup**: Cache cleanup happens automatically when items are removed from storage

### Benefits
- Plugin authors don't need to handle resumability explicitly
- Job queue infrastructure handles persistence and recovery
- Uses existing storage/cache systems
- Transparent to plugin implementations

## Data Types

```python
@dataclass(frozen=True)  # Immutable
class Metadata:
    source_url: str  # A natural or synthetic URL, e.g. synthetic == chapter in a book
    location: Optional[Union[CacheId, Path]] = None
    title: Optional[str] = None
    parent_id: Optional[ItemId] = None  # Make it possible to define a tree
    description: Optional[str] = None
    processing_state: str = "pending"  # For resumability
    indexed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    modified_at: Optional[datetime] = None
    author: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    mime_type: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    # Immutable update methods
    def copy(self, **changes) -> 'Metadata':
        """Create a new Metadata instance with specified changes"""
        current_dict = asdict(self)
        current_dict.update(changes)
        return Metadata(**current_dict)

    def merge(self, patch: 'Metadata') -> 'Metadata':
        """Create a new Metadata instance merged with patch"""
        current_dict = asdict(self)
        patch_dict = asdict(patch)

        # Merge dictionaries recursively, lists are concatenated
        merged = {}
        for key in set(current_dict.keys()) | set(patch_dict.keys()):
            if key in patch_dict and patch_dict[key] is not None:
                if key in current_dict and isinstance(current_dict[key], list) and isinstance(patch_dict[key], list):
                    merged[key] = current_dict[key] + patch_dict[key]
                else:
                    merged[key] = patch_dict[key]
            elif key in current_dict:
                merged[key] = current_dict[key]

        return Metadata(**merged)

# Type aliases
ItemId = Any  # To be defined by implementation
JobId = Any   # To be defined by implementation
Logger = Any  # To be defined by implementation
Configuration = Any  # To be defined by implementation
Content = Union[bytes, str]
CacheId = Any  # To be defined by implementation
```

## Error Handling Strategy

### Phase 1: Fail Fast (Initial Implementation)
- Plugin failures halt the system
- Immediate feedback for development
- Simplified debugging
- Transition to isolation when core system is working or specific error scenarios become problematic

### Phase 2: Isolation (Future Enhancement)
- Add "good fences" protection around plugin calls
- Timeouts for plugin operations
- Exception handling with fallback mechanisms
- Error reporting without system shutdown
- Job retry mechanisms for transient failures

### Error Categories
1. **Configuration errors**: Invalid plugin configuration
2. **Runtime errors**: Plugin crashes during operation
3. **Resource errors**: Plugin exhausts system resources
4. **Network errors**: Plugin fails to fetch external content
5. **Job processing errors**: Failures in job queue processing

## Content Deduplication Strategy

### Fetch-Level Deduplication
- ContentSources can check if content already exists before scheduling fetches
- ContentSourceHost provides `data_storage` property for read-only access to check existing content
- ContentSources use `await host.data_storage.find_item_id(host, metadata)` to check for duplicates
- Saves bandwidth and processing time by avoiding duplicate fetches

### Storage-Level Deduplication
- DataStorage handles content-level deduplication
- Can detect same content from different URLs/paths
- Different storage providers may have different strategies

### ContentSource Duplicate Detection Pattern
```python
async def start_source(self, host: ContentSourceHost) -> None:
    """Example showing duplicate detection pattern."""
    content_items = await self.discover_content(host)

    scheduled_count = 0
    skipped_count = 0

    for url, metadata in content_items:
        # Check if content already exists in data storage
        try:
            existing_item_id = await host.data_storage.find_item_id(host, metadata)
            if existing_item_id:
                host.logger.debug("Skipping %s - already exists with ID %s", url, existing_item_id)
                skipped_count += 1
                continue
        except Exception as e:
            host.logger.warning("Failed to check for existing content: %s", e)
            # Continue with scheduling if duplicate check fails

        # Schedule for fetching
        host.schedule_fetch(url, metadata)
        scheduled_count += 1

    host.logger.info("Scheduled %d files, skipped %d duplicates", scheduled_count, skipped_count)
```

## Implementation Requirements

### Core Requirements
1. **Plugin Infrastructure Focus**: Initial implementation focuses on plugin system infrastructure with test plugins as simulacra
2. **Minimal Extension Points**: Adding new extension point requires only:
   - Protocol definition using `typing.Protocol`
   - Registration hook using `@hookimpl` pattern
   - Additional infrastructure added only when needed

3. **Plugin Discovery**:
   - Scan entire paise2 codebase for internal plugins with `@hookimpl` decorations
   - Use pluggy's standard mechanisms for external plugins
   - Simple discovery order loading

4. **Type Safety**:
   - All extension points defined as Protocol classes
   - Static type checking support
   - Runtime validation of plugin interfaces

### Technical Requirements

#### Dependencies
- Python 3.8+
- Managed by uv
- pluggy for plugin system
- asyncio for asynchronous operations
- typing.Protocol for interface definitions
- dataclasses for immutable data structures

#### Project Structure
```
paise2/
├── src/
│   ├── plugins/
│   │   ├── core/
│   │   │   ├── interfaces.py      # Protocol definitions
│   │   │   ├── registry.py        # Plugin registration
│   │   │   ├── manager.py         # Plugin management
│   │   │   ├── hosts.py           # Host implementations
│   │   │   ├── startup.py         # Phased startup sequence
│   │   │   └── jobs.py            # Job processing infrastructure
│   │   ├── providers/
│   │   │   ├── config.py          # Configuration providers
│   │   │   ├── storage.py         # Storage providers
│   │   │   ├── jobs.py            # Job queue providers
│   │   │   ├── state.py           # State storage providers
│   │   │   └── cache.py           # Cache providers
│   ├── config/
│   │   ├── manager.py            # Configuration management
│   │   └── models.py             # Configuration data models
│   ├── storage/
│   │   └── models.py             # Storage data models
│   ├── state/
│   │   └── models.py             # State management models
│   └── utils/
│       └── logging.py            # Logging utilities
├── tests/
│   ├── unit/
│   │   ├── test_plugin_system.py
│   │   ├── test_interfaces.py
│   │   ├── test_hosts.py
│   │   ├── test_jobs.py
│   │   └── test_providers.py
│   └── integration/
│       ├── test_plugin_flow.py
│       ├── test_startup_sequence.py
│       └── test_job_processing.py
└── docs/
    └── plugins/
        └── spec.md              # This specification
```

## Testing Strategy

### Unit Tests
```python
# Test extension point protocols
def test_content_extractor_protocol():
    class TestExtractor:
        def can_extract(self, url: str, mime_type: str = None) -> bool:
            return True
        def preferred_mime_types(self) -> List[str]:
            return ["plain/test"]
        async def extract(self, host, content, metadata=None):
            await host.storage.add_item("test content", metadata or Metadata())

    # Verify protocol compliance
    assert isinstance(TestExtractor(), ContentExtractor)

# Test plugin state partitioning
def test_state_partitioning():
    plugin1_state = create_test_state("paise2.plugins.test1")
    plugin2_state = create_test_state("paise2.plugins.test2")

    plugin1_state.store("key", "value1")
    plugin2_state.store("key", "value2")

    assert plugin1_state.get("key") == "value1"
    assert plugin2_state.get("key") == "value2"

# Test configuration merging
def test_configuration_merging():
    config1 = {"scalar": "first", "list": [1, 2]}
    config2 = {"scalar": "second", "list": [3, 4]}

    merged = merge_configurations([config1, config2])

    assert merged["scalar"] == "second"  # Last wins
    assert merged["list"] == [1, 2, 3, 4]  # Lists concatenated

# Test task queue functionality
def test_task_queue():
    queue = SynchronousTaskQueue()  # For testing

    task_id = await queue.enqueue("test_task", {"data": "test"})
    assert task_id is not None

    task = await queue.dequeue("test_worker")
    # In synchronous mode, tasks are executed immediately
    assert task is None
```

### Integration Tests
```python
def create_test_plugin_system() -> PluginSystem:
    plugin_system = TestPluginSystem()

    # Add extensions.
    plugin_system.register_configuration_provider(TestConfigurationProvider())
    plugin_system.register_context_extractor(TestContentExtractor())

    return plugin_system

```python
# Test full plugin flow
async def test_full_plugin_flow():
    # Setup test environment
    plugin_system = create_test_plugin_system()

    # Test phased startup
    await plugin_system.phase_1_bootstrap()
    await plugin_system.phase_2_singleton_contributors()
    await plugin_system.phase_3_singleton_creation()
    await plugin_system.phase_4_singleton_users()
    await plugin_system.phase_5_start()

    # Test content processing flow
    source = plugin_system.get_content_source("test_source")
    await source.start_source(test_host)

    # Verify content was processed and stored
    items = await test_storage.get_all_items()
    assert len(items) > 0

# Test recursive extraction
async def test_recursive_extraction():
    zip_extractor = ZipContentExtractor()
    test_host = create_test_host()

    # Simulate ZIP content with multiple files
    zip_content = create_test_zip_content()
    metadata = Metadata(source_url="test.zip")

    await zip_extractor.extract(test_host, zip_content, metadata)

    # Verify recursive extractions were scheduled
    assert len(test_host.scheduled_extractions) > 1

# Test resumable operations
async def test_resumable_operations():
    # Start processing
    plugin_system = create_test_plugin_system()
    await plugin_system.start()

    # Simulate system shutdown during processing
    await plugin_system.stop()

    # Restart and verify resumption
    plugin_system2 = create_test_plugin_system()
    await plugin_system2.start()

    # Check that incomplete jobs are resumed
    incomplete_tasks = await test_task_queue.get_incomplete_tasks()
    assert len(incomplete_tasks) == 0  # Should be resumed and completed

# Test task processing
async def test_task_processing():
    task_queue = HueySQLiteTaskQueue(":memory:")

    # Enqueue a task
    task_id = await task_queue.enqueue("fetch_content", {"url": "test://example.com"})

    # Dequeue and process
    task = await task_queue.dequeue("test_worker")
    assert task is not None
    assert task.task_type == "fetch_content"

    # Complete the task
    await task_queue.complete(task.task_id, {"status": "success"})

    # Verify no incomplete tasks remain
    incomplete = await task_queue.get_incomplete_tasks()
    assert len(incomplete) == 0
```

### Plugin Tests
```python
# Test individual plugins
def test_test_content_extractor():
    extractor = TestContentExtractor()
    assert extractor.can_extract("test://example.txt")
    assert "text/plain" in extractor.preferred_mime_types()

def test_test_content_source():
    source = TestContentSource()
    host = create_test_host()

    # Should schedule some test fetches
    await source.start_source(host)
    assert len(host.scheduled_fetches) > 0

def test_task_queue_providers():
    # Test synchronous provider
    sync_provider = NoTaskQueueProvider()
    sync_queue = sync_provider.create_task_queue({})
    assert isinstance(sync_queue, SynchronousTaskQueue)

    # Test Huey SQLite provider
    sqlite_provider = HueySQLiteTaskQueueProvider()
    sqlite_queue = sqlite_provider.create_task_queue({"task_queue.sqlite_path": ":memory:"})
    assert isinstance(sqlite_queue, HueyTaskQueueAdapter)
```

### Host Interface Tests
```python
# Test host implementations
def test_content_extractor_host():
    host = ContentExtractorHost(
        storage=mock_storage,
        logger=mock_logger,
        cache=mock_cache,
        task_queue=mock_task_queue
    )
    assert host.storage is not None
    assert host.logger is not None
    assert host.cache is not None

def test_host_state_partitioning():
    host1 = create_test_host("paise2.plugins.test1")
    host2 = create_test_host("paise2.plugins.test2")

    # States should be automatically partitioned
    host1.state.store("key", "value1")
    host2.state.store("key", "value2")

    assert host1.state.get("key") != host2.state.get("key")
```

## Development Workflow

### Adding a New Extension Point
1. Define Protocol interface in `interfaces.py`
2. Add registration hook in registry
3. Update plugin manager to handle new extension type
4. Create host interface if needed
5. Add to appropriate startup phase
6. Add job types if needed
7. Write tests

### Adding a New Plugin
1. Implement extension point Protocol
2. Create registration function with `@hookimpl`
3. Add configuration if needed
4. Write unit tests
5. Add integration tests
6. Document plugin capabilities

### Example: Adding a Test PDF Content Extractor
```python
# 1. Implement the protocol
class TestPDFContentExtractor:
    def preferred_mime_types(self) -> List[str]:
        return ["application/pdf"]

    def can_extract(self, url: str, mime_type: str = None) -> bool:
        return url.endswith(".pdf") or (mime_type and "pdf" in mime_type)

    async def extract(self, host: ContentExtractorHost, content: bytes, metadata: Optional[Metadata] = None) -> None:
        # Simulate PDF text extraction
        text = f"Simulated PDF text from {metadata.source_url if metadata else 'unknown'}"
        new_metadata = metadata.copy(processing_state="completed") if metadata else Metadata(processing_state="completed")
        await host.storage.add_item(text, new_metadata)

# 2. Register the plugin
@hookimpl
def register_content_extractor(register):
    register(TestPDFContentExtractor())
```

## Initial Implementation Focus

### Phase 1: Core Plugin Infrastructure
Focus on building the plugin system infrastructure with test plugins:

1. **Plugin System Core**:
   - pluggy integration
   - Plugin discovery (scanning paise2 codebase)
   - Extension point registration
   - Phased startup sequence

2. **Essential Extension Points**:
   - ConfigurationProvider (Phase 2)
   - DataStorageProvider (Phase 2)
   - TaskQueueProvider (Phase 2)
   - StateStorageProvider (Phase 2)
   - CacheProvider (Phase 2)
   - ContentExtractor (Phase 4)
   - ContentSource (Phase 4)
   - ContentFetcher (Phase 4)

3. **Host Interfaces**:
   - BaseHost with common functionality
   - Specialized hosts for each extension type
   - State management integration
   - Configuration access
   - Task queue integration

4. **Default Providers**:
   - NoTaskQueueProvider (synchronous execution for development)
   - HueySQLiteTaskQueueProvider (persistent task queue for development)
   - HueyRedisTaskQueueProvider (distributed task queue for production)
   - FileConfigurationProvider
   - Basic storage, state, and cache providers

5. **Test Plugin Simulacra**:
   - TestConfigurationProvider
   - TestDataStorageProvider
   - TestContentExtractor (simple text extraction)
   - TestContentSource (generates test URLs)
   - TestContentFetcher (simulates fetching)

6. **Supporting Systems**:
   - Configuration merging
   - State management with automatic partitioning
   - Cache management
   - Job queue processing infrastructure
   - Resumability support

### Success Criteria
- Complete phased startup sequence works
- Test plugins can be discovered and loaded
- End-to-end flow: ContentSource → Job Queue → ContentFetcher → Job Queue → ContentExtractor → DataStorage
- Plugin state is properly partitioned
- Configuration merging works correctly
- Task queue can handle both synchronous and asynchronous processing
- System can restart and resume operations via task queue

### Development Progression
1. **Start with NoTaskQueueProvider**: Everything runs synchronously, easier to debug
2. **Switch to HueySQLiteTaskQueueProvider**: Add persistence and async processing
3. **Scale to HueyRedisTaskQueueProvider**: Add distributed task processing for production
3. **Add real plugin implementations**: Replace test plugins with actual functionality
4. **Add error isolation**: Implement Phase 2 error handling
5. **Add monitoring and management**: Job queue status, plugin performance, etc.

## Future Enhancements

### Planned Features
- Real plugin implementations (HTML, PDF, ZIP extractors, etc.)
- Dynamic plugin loading/unloading
- Plugin sandboxing for security
- Remote plugin repositories
- Plugin dependency management
- Web-based plugin configuration UI
- Plugin performance monitoring
- Distributed processing support
- Advanced job queue features (retries, priorities, scheduling)

### Extension Points to Consider Later
- MetadataEnricher - Enhance content metadata
- ContentTransformer - Transform content before indexing
- SearchRanker - Custom search result ranking
- IndexOptimizer - Optimize search index
- NotificationProvider - Send notifications on events
- JobHandler - Custom job processing logic
- WorkerManager - Manage job processing workers

---

This specification provides a comprehensive foundation for implementing the PAISE2 plugin system. The focus on infrastructure first with test plugins and a job queue system will establish a solid, scalable foundation that can be extended with real functionality once the core architecture is proven.
