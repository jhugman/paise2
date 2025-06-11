# Profile-Based Plugin Loading Example

This document demonstrates the new profile-based plugin loading system in PAISE2.

## Overview

The `PluginManager` now supports parameterized `paise2_root` for flexible plugin loading based on context/environment. This solves the problem of having multiple providers for the same service by allowing different profiles to load different sets of system plugins.

## Usage Examples

### 1. Profile-Based Plugin Loading

```python
from paise2.profiles.factory import (
    create_production_plugin_manager,
    create_development_plugin_manager,
    create_test_plugin_manager,
)

# Production: File-based storage only
production_pm = create_production_plugin_manager()
production_pm.discover_plugins()
production_pm.load_plugins()
providers = production_pm.get_state_storage_providers()
# providers = [FileStateStorageProvider()]

# Development: Both memory and file storage
dev_pm = create_development_plugin_manager()
dev_pm.discover_plugins()
dev_pm.load_plugins()
providers = dev_pm.get_state_storage_providers()
# providers = [MemoryStateStorageProvider(), FileStateStorageProvider()]

# Test: Memory-only storage for fast tests
test_pm = create_test_plugin_manager()
test_pm.discover_plugins()
test_pm.load_plugins()
providers = test_pm.get_state_storage_providers()
# providers = [MemoryStateStorageProvider()]
```

### 2. Custom Plugin Directory

```python
from pathlib import Path
from paise2.plugins.core.registry import PluginManager

# Use a custom directory for plugins
custom_plugin_dir = Path("/path/to/custom/plugins")
plugin_manager = PluginManager(paise2_root=str(custom_plugin_dir))
plugin_manager.discover_plugins()
plugin_manager.load_plugins()
```

### 3. Backward Compatibility

```python
from paise2.plugins.core.registry import PluginManager

# Default behavior - scans full paise2 package
plugin_manager = PluginManager()  # Uses paise2.__file__ as root
plugin_manager.discover_plugins()
plugin_manager.load_plugins()
```

## Profile Directory Structure

```
src/paise2/profiles/
├── __init__.py
├── factory.py              # Helper functions
├── production/
│   ├── __init__.py
│   └── state_storage.py    # File-based providers only
├── development/
│   ├── __init__.py
│   └── state_storage.py    # Both memory and file providers
└── test/
    ├── __init__.py
    └── state_storage.py    # Memory-only providers
```

## Benefits

### 1. Context-Appropriate Plugin Loading
- **Production**: Only persistent, production-ready providers
- **Development**: Multiple options for flexibility
- **Testing**: Fast, memory-only providers

### 2. Provider Selection Resolution
- No need for complex selection logic during singleton creation
- Each profile loads exactly the providers needed
- Clear separation of concerns

### 3. Extensibility
- Easy to add new profiles (e.g., `staging`, `ci`, `integration`)
- Custom plugin directories for special use cases
- Profile-specific configuration can be added

### 4. Future Plugin Types
When implementing job queues (PROMPT 9), cache providers (PROMPT 10), etc.:

```python
# profiles/production/job_queue.py
@hookimpl
def register_job_queue_provider(register):
    register(SQLiteJobQueueProvider())  # Persistent only

# profiles/test/job_queue.py
@hookimpl
def register_job_queue_provider(register):
    register(NoJobQueueProvider())  # Synchronous for tests
```

## Migration from Legacy Registration

The old `src/paise2/state/plugin_registration.py` approach:
- ❌ Always loaded both providers
- ❌ Required selection logic during singleton creation
- ❌ No environment-specific customization

The new profile-based approach:
- ✅ Loads only appropriate providers per profile
- ✅ No selection logic needed
- ✅ Environment-specific customization built-in
- ✅ Extensible for new profiles and plugin types

## Implementation Details

### PluginManager Changes
```python
class PluginManager:
    def __init__(self, paise2_root: str | None = None) -> None:
        # Set plugin discovery root (for profile-based plugin loading)
        self._paise2_root = Path(paise2_root) if paise2_root else Path(paise2.__file__).parent
```

### Module Path Calculation
The system correctly calculates module names relative to the main `paise2` package, allowing profile directories to be anywhere in the `paise2` namespace while maintaining proper import paths.

This approach provides a clean, flexible, and extensible solution to the multi-provider problem while maintaining backward compatibility.
