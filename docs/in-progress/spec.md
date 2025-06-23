# PAISE2 Worker System: Design Decisions Summary

## Overview
PAISE2 is a content processing system built on a plugin architecture with profile-based configuration. This document outlines the design for adding asynchronous task processing using Huey, enabling background workers to handle core operations (fetch, extract, store, cleanup) while maintaining full integration with the existing plugin system and configuration framework.

## Core Architectural Decisions

### 1. Task Queue Integration Strategy
**Decision**: Use existing TaskQueueProvider plugin system
**Rationale**: Maintains consistency with PAISE2's architecture where providers create configured instances
**Implementation**:
- Production profile: `HueySQLiteTaskQueueProvider` with SQLite backend for persistence
- Development profile: `NoTaskQueueProvider` and `HueySQLiteTaskQueueProvider` for flexibility
- Test profile: `NoTaskQueueProvider` with immediate execution for fast testing
- Tasks access Huey via TaskQueue singleton from plugin system

### 2. Profile Propagation Mechanism
**Decision**: Use `PAISE2_PROFILE` environment variable
**Rationale**: Leverages existing profile system, simple and reliable
**Implementation**: CLI commands set environment variable before starting workers

### 3. Worker Lifecycle Management
**Decision**: Use programmatic consumer creation (not huey_consumer command)
**Rationale**: `huey_consumer` required module-level Huey instance that conflicted with PAISE2's plugin-based architecture
**Implementation**:
- CLI commands use `huey.create_consumer()` programmatically
- Access Huey instance via TaskQueue singleton from plugin system
- Workers started as separate processes within PAISE2 application context

### 4. Worker Context Strategy
**Decision**: Worker-specific singletons with complete isolation
**Rationale**: Avoids shared state issues, ensures clean worker environments
**Implementation**: Each worker recreates full application context via `@huey.on_startup()` hooks

### 5. Development vs Production Behavior
**Decision**: Development uses immediate execution option, production uses persistent queues
**Rationale**: Fast feedback during development, reliable async processing in production
**Implementation**:
- Development: `NoTaskQueueProvider` (immediate) or `HueySQLiteTaskQueueProvider` (persistent)
- Production: `HueySQLiteTaskQueueProvider` with separate worker processes
- Test: `NoTaskQueueProvider` with immediate execution for fast, reliable testing

### 6. Task Scope (Initial Release)
**Decision**: Core tasks only (fetch, extract, store, cleanup)
**Rationale**: Focused initial scope, plugin-defined tasks as future enhancement
**Implementation**: Tasks defined in `paise2.plugins.core.tasks`

### 7. Error Handling Strategy
**Decision**: Use Huey's built-in `RetryTask` for task-specific, plugin-specific retry policies
**Rationale**: Leverages proven library functionality, configurable per error type
**Implementation**: Different retry policies for network timeouts, HTTP errors, etc.

### 8. Worker Monitoring Approach
**Decision**: Rely on Huey's native capabilities initially
**Rationale**: Faster implementation, custom monitoring as future enhancement
**Implementation**: Basic status commands, detailed monitoring in future phases

## Implementation Architecture

### Component Structure
```
┌─────────────────────┐    ┌──────────────────────┐
│   Main Application  │    │   Worker Processes   │
│                     │    │                      │
│  ┌─────────────────┐│    │ ┌──────────────────┐ │
│  │ TaskQueue       ││    │ │ Worker Context   │ │
│  │ (via Provider)  ││    │ │ (Recreated)      │ │
│  └─────────────────┘│    │ └──────────────────┘ │
│                     │    │                      │
│  ┌─────────────────┐│    │ ┌──────────────────┐ │
│  │ Core Tasks      ││────┤ │ Task Execution   │ │
│  │ (Enqueue)       ││    │ │ (Process)        │ │
│  └─────────────────┘│    │ └──────────────────┘ │
└─────────────────────┘    └──────────────────────┘
```

### CLI Interface Design
**Decision**: Use Huey's programmatic consumer API (not huey_consumer command)
**Rationale**: `huey_consumer` forced awkward module structure that didn't fit PAISE2's plugin architecture
**Approach**: Programmatic consumer creation within PAISE2 CLI commands
```python
# Inside paise2 workers start command:
huey = singletons.task_queue.huey
consumer = huey.create_consumer(workers=N)
consumer.run()  # Blocks until interrupted
```

**Commands**:
- `paise2 worker start [--concurrency N] [--daemonize]`
- `paise2 worker stop`
- `paise2 worker status`

### Configuration Integration
**Decision**: Use PAISE2's configuration system with ConfigurationProvider
**Structure**:
```yaml
workers:
  concurrency: 4
  retry:
    max_retries: 3
    retry_delay: 60
task_queue:
  sqlite:
    path: "~/.local/share/paise2/tasks.db"
    immediate: false  # For development debugging
```

## Key Technical Decisions

### 1. Worker Context Initialization
**Decision**: Still use `@huey.on_startup()` hook for worker context initialization
**Rationale**: Even with programmatic consumers, Huey manages individual worker threads/processes that need their own application context
**Pattern**: Thread-local storage with deferred initialization
```python
@huey.on_startup()
def initialize_worker_context():
    # Each worker thread/process recreates its own application context
    plugin_manager = get_plugin_manager()
    app = Application(plugin_manager=plugin_manager)
    app.start()
    _worker_context.singletons = app.get_singletons()
```

**Alternative considered**: Initialize context before consumer creation, but rejected because individual worker threads still need isolated contexts.

### 2. Task Registration Flow
**Pattern**: TaskQueue handles task setup during application initialization
```python
# Tasks are already registered when TaskQueue is created
# Workers simply recreate the application context:

@huey.on_startup()
def initialize_worker_context():
    # Recreate complete application (including TaskQueue setup)
    plugin_manager = get_plugin_manager()
    app = Application(plugin_manager=plugin_manager)
    app.start()  # This sets up TaskQueue and registers tasks
    _worker_context.singletons = app.get_singletons()
```

### 3. Profile-Specific Behavior
**Production**: SQLite backend, separate worker processes, configurable concurrency
**Development**: Choice of immediate (NoTaskQueueProvider) or persistent (SQLite) execution
**Test**: Immediate execution only, no background processing

### 4. Graceful Degradation
**Decision**: Tasks queue up if no workers are running
**Behavior**: Main application continues functioning, tasks wait for workers

## Future Extensions (Not in Initial Scope)

### Service-Style Management
- Persistent worker management with PID tracking
- `paise2 workers restart --concurrency N`
- Background daemon control

### Task-Specific Workers
- Specialized worker pools: `paise2 workers start-fetchers`
- Task routing and queue segmentation
- Performance optimization per task type

### Plugin-Defined Tasks
- Extension point for plugins to register custom tasks
- Task validation and sandboxing
- Plugin-specific retry policies

### Advanced Monitoring
- Worker health dashboards
- Task processing metrics
- Performance analytics and alerting

### Distributed Scaling (Future)
- Redis backend for distributed task queues
- Multi-machine worker deployment
- Advanced load balancing and scaling

## Implementation Priority

1. **Phase 1**: TaskQueueProvider integration, basic CLI commands
2. **Phase 2**: Worker context initialization, core task definitions
3. **Phase 3**: Error handling, retry policies, status reporting
4. **Phase 4**: Future extensions (service management, custom tasks)

## Key Files to Create/Modify

### New Files
- `src/paise2/profiles/common/workers/cli.py` - Worker configuration
- `src/paise2/profiles/common/workers/config.py` - Worker CLI commands

### Modified Files
- `src/paise2/profiles/*/cli.py` - Add worker management commands (if needed)
- No dependency changes needed - using existing SQLite TaskQueueProvider

**Note**: No changes needed to `src/paise2/main.py` since TaskQueue already handles task setup during application initialization.

## Success Criteria

✅ **Simple Integration**: Workers use existing plugin/configuration system
✅ **Profile Awareness**: Different behavior per profile (dev vs production)
✅ **Developer Friendly**: Easy CLI management, fast development feedback
✅ **Extensible Design**: Clear path for future enhancements
✅ **Robust Error Handling**: Configurable retry policies
✅ **Clean Architecture**: No shared state between main app and workers

This design provides a solid foundation for asynchronous task processing while maintaining PAISE2's architectural principles and ensuring future extensibility.
