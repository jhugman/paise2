# PAISE2 Worker System - Implementation Prompt Plan

## Project Overview

PAISE2 is a production-ready content indexing system with a comprehensive plugin architecture. The system includes:

- **Plugin Architecture**: 448 passing tests, protocol-based interfaces, 5-phase startup
- **TaskQueueProvider System**: Complete with Huey integration (NoTaskQueueProvider, HueySQLiteTaskQueueProvider, HueyRedisTaskQueueProvider)
- **Core Tasks**: Already defined (fetch_content, extract_content, store_content, cleanup_cache)
- **CLI System**: Extensible command system with run, status, validate, version commands
- **Profile System**: Test, development, and production configurations

**Goal**: Add worker management functionality to enable background task processing while maintaining the existing architecture.

## Implementation Strategy

The implementation follows these architectural principles:
1. **Incremental Enhancement**: Build on existing TaskQueueProvider system
2. **Profile Consistency**: Different behavior for test/dev/production profiles
3. **CLI Integration**: Extend existing CLI system with worker commands
4. **Clean Architecture**: No shared state, proper isolation
5. **Test-Driven**: Strong testing for each increment

## Detailed Prompt Sequence

---

## PROMPT 1: Worker Configuration Foundation

### Context
The PAISE2 system already has a complete TaskQueueProvider system with Huey integration. We need to add worker management configuration that integrates with the existing profile system and configuration framework.

### Task
```
Create the worker configuration foundation that integrates with PAISE2's existing configuration system.

Requirements:
1. Create worker configuration schema that extends existing Configuration system
2. Add worker-specific configuration options for different profiles
3. Create configuration providers for worker settings
4. Integrate with existing profile system (test/development/production)
5. Ensure configuration follows existing patterns in the codebase

Configuration structure needed:
- worker.concurrency: Number of worker processes
- worker.retry.max_retries: Maximum retry attempts for failed tasks
- worker.retry.retry_delay: Delay between retries
- worker.monitoring.enable: Enable worker monitoring
- task_queue.sqlite.immediate: Control immediate vs queued execution

Profile-specific behavior:
- Test profile: No worker configuration (immediate execution only)
- Development profile: Optional worker configuration with immediate option
- Production profile: Full worker configuration with persistent queues

Integration points:
- Use existing ConfigurationProvider interface
- Follow existing configuration merging patterns
- Maintain compatibility with current task queue configuration
- Ensure proper validation and defaults
```

### Task List
- [x] Create `src/paise2/profiles/common/workers/config.py` with worker configuration provider
- [x] Add worker configuration schema to match existing configuration patterns
- [x] Create default worker configurations for development and production profiles
- [x] Add worker configuration validation and error handling
- [x] Update existing configuration files to include worker settings
- [x] Create tests for worker configuration loading and validation
- [x] Verify configuration merging works correctly with existing system
- [x] Test profile-specific worker configuration behavior
- [x] Ensure backward compatibility with existing configurations
- [x] Document worker configuration options and defaults
- [x] **PROMPT 1 COMPLETE ✅**

---

## PROMPT 2: Worker Context Initialization

### Context
With worker configuration in place, we need to implement the worker context initialization system that allows worker processes to recreate the complete PAISE2 application context. This follows the design decision to use worker-specific singletons with complete isolation.

### Task
```
Implement worker context initialization using Huey's @huey.on_startup() hooks to ensure each worker process has its own complete application context.

Requirements:
1. Create worker context initialization system
2. Use @huey.on_startup() decorator for worker context setup
3. Implement profile propagation via PAISE2_PROFILE environment variable
4. Ensure complete application context recreation in worker processes
5. Add proper error handling and logging for worker initialization
6. Create thread-local storage for worker context
7. Implement graceful worker context cleanup

Worker initialization pattern:
``python
@huey.on_startup()
def initialize_worker_context():
    # Recreate complete application context
    plugin_manager = get_plugin_manager_from_profile()
    app = Application(plugin_manager=plugin_manager)
    app.start()
    _worker_context.singletons = app.get_singletons()
``

Integration requirements:
- Use existing Application class and plugin system
- Leverage existing profile factory functions
- Maintain consistency with main application startup
- Ensure proper resource cleanup on worker shutdown
```

### Task List
- [x] Create `src/paise2/workers/context.py` with worker context management
- [x] Implement worker context initialization using @huey.on_startup() hooks
- [x] Add profile propagation mechanism using PAISE2_PROFILE environment variable
- [x] Create thread-local storage for worker context (ThreadContextManager)
- [x] Implement worker context cleanup and resource management
- [x] Add proper logging and error handling for worker initialization
- [x] Create worker context access helpers for task functions
- [x] Test worker context initialization with different profiles
- [x] Verify complete application context recreation in workers
- [x] Test error handling and recovery in worker context setup
- [x] **PROMPT 2 COMPLETE ✅**

---

## PROMPT 3: Enhanced Task Execution

### Context
The core tasks are already defined in `src/paise2/plugins/core/tasks.py`, but they need to be enhanced to work properly with the new worker context system. Tasks need to access the worker-specific singletons rather than main application context.

### Task
```
Enhance the existing task execution system to properly integrate with worker contexts and add comprehensive error handling.

Requirements:
1. Update existing task implementations to use worker context
2. Add comprehensive error handling and retry logic
3. Implement task-specific retry policies (network timeouts, HTTP errors, etc.)
4. Add task execution monitoring and logging
5. Ensure tasks work in both immediate (test) and queued (production) modes
6. Add task result tracking and status reporting

Current tasks to enhance:
- fetch_content_task: Add network error handling and retries
- extract_content_task: Add extraction error handling
- store_content_task: Add storage error handling and validation
- cleanup_cache_task: Add cleanup error handling and verification

Error handling patterns:
- Use Huey's built-in RetryTask for configurable retry policies
- Different retry policies for different error types
- Proper logging with worker context information
- Task status tracking and reporting
```

### Task List
- [ ] Update task functions in `src/paise2/plugins/core/tasks.py` to use worker context
- [ ] Add comprehensive error handling to all task functions
- [ ] Implement RetryTask-based retry policies for different error types
- [ ] Add task execution logging with proper worker context
- [ ] Create task status tracking and reporting system
- [ ] Add task-specific error recovery mechanisms
- [ ] Test task execution in both immediate and queued modes
- [ ] Test retry logic and error handling for each task type
- [ ] Verify task isolation and context management
- [ ] Add task performance monitoring and metrics
- [ ] **PROMPT 3 COMPLETE**

---

## PROMPT 4: CLI Worker Management Commands

### Context
PAISE2 has an extensible CLI system with core commands (run, status, validate, version). We need to add worker management commands that integrate seamlessly with the existing CLI architecture and profile system.

### Task
```
Create worker management CLI commands that integrate with PAISE2's existing CLI system and provide comprehensive worker lifecycle management.

Requirements:
1. Create worker management commands using existing CLI patterns
2. Integrate with existing profile system and plugin architecture
3. Use programmatic Huey consumer creation (not huey_consumer command)
4. Add proper signal handling and graceful shutdown
5. Support different profiles with appropriate behavior
6. Add comprehensive status reporting and monitoring

Commands to implement:
- `paise2 worker start [--concurrency N] [--daemonize]`: Start worker processes
- `paise2 worker stop`: Stop running workers (future: with PID tracking)
- `paise2 worker status`: Show worker status and queue metrics
- `paise2 worker restart [--concurrency N]`: Restart workers (future enhancement)

Integration requirements:
- Follow existing CLI command patterns in `src/paise2/profiles/base/cli/`
- Use existing plugin manager and application context
- Integrate with existing configuration system
- Support profile-specific behavior (test profile should show helpful error)
- Add proper error handling and user feedback
```

### Task List
- [ ] Create `src/paise2/profiles/common/workers/cli.py` with worker CLI commands
- [ ] Implement `paise2 worker start` command with programmatic consumer creation
- [ ] Add `paise2 worker status` command with queue metrics and worker information
- [ ] Create `paise2 worker stop` command (basic version, PID tracking future)
- [ ] Add signal handling and graceful shutdown for worker processes
- [ ] Integrate worker commands with existing CLI system and plugin registration
- [ ] Add profile-specific behavior (test profile warnings, dev/prod support)
- [ ] Create comprehensive help and documentation for worker commands
- [ ] Test worker commands with different profiles and configurations
- [ ] Add proper error messages and user feedback for common scenarios
- [ ] **PROMPT 4 COMPLETE**

---

## PROMPT 5: Worker Status and Monitoring

### Context
PAISE2 already has a comprehensive monitoring system in `src/paise2/monitoring.py`. We need to extend this system to include worker-specific monitoring and integrate it with the existing status command and health reporting.

### Task
```
Extend the existing monitoring system to include comprehensive worker status and queue monitoring capabilities.

Requirements:
1. Extend existing SystemHealthMonitor to include worker information
2. Add task queue metrics and status reporting
3. Integrate with existing `paise2 status` command
4. Add worker-specific health checks and diagnostics
5. Support both text and JSON output formats (following existing patterns)
6. Add queue depth, processing rates, and worker status information

Monitoring additions needed:
- Task queue status (queue depth, processing rate, failed tasks)
- Worker process information (if workers are running)
- Task execution metrics (completed, failed, retried)
- Queue backend health (SQLite/Redis connectivity)
- Profile-specific monitoring (immediate vs queued execution)

Integration points:
- Extend existing SystemHealthMonitor class
- Integrate with existing `paise2 status` command output
- Follow existing Rich formatting patterns for text output
- Maintain existing JSON output structure
- Use existing health check patterns
```

### Task List
- [ ] Extend SystemHealthMonitor in `src/paise2/monitoring.py` with worker monitoring
- [ ] Add task queue health checks and metrics collection
- [ ] Create worker status detection and reporting functions
- [ ] Add queue metrics (depth, processing rate, error rate) to health reports
- [ ] Integrate worker monitoring with existing `paise2 status` command
- [ ] Add worker information to both text and JSON status output
- [ ] Create profile-specific monitoring (test vs development vs production)
- [ ] Add task execution metrics and queue backend health checks
- [ ] Test monitoring integration with different TaskQueueProvider implementations
- [ ] Verify monitoring works correctly with both immediate and queued execution
- [ ] **PROMPT 5 COMPLETE**

---

## PROMPT 6: Profile Integration and Configuration

### Context
PAISE2 has a sophisticated profile system (test/development/production) with different TaskQueueProvider configurations. We need to ensure the worker system integrates properly with each profile and provides appropriate behavior.

### Task
```
Complete the profile integration for the worker system, ensuring each profile behaves appropriately and configurations are properly merged.

Requirements:
1. Test profile: Show helpful messages about immediate execution, disable worker commands
2. Development profile: Support both immediate and queued execution options
3. Production profile: Full worker support with persistent queues
4. Configuration validation: Ensure worker configs are valid for each profile
5. Profile-specific defaults: Appropriate defaults for each deployment type
6. Error handling: Clear error messages for profile-specific limitations

Profile behaviors needed:
- Test: Worker commands show educational messages about immediate execution
- Development: Flexible configuration with immediate option for debugging
- Production: Full worker lifecycle management with persistent queues
- Configuration inheritance: Proper merging of worker settings with existing configs

Integration requirements:
- Use existing profile factory functions
- Follow existing configuration merging patterns
- Maintain backward compatibility with existing profiles
- Add appropriate validation for profile-specific constraints
```

### Task List
- [ ] Update test profile to handle worker commands with educational messages
- [ ] Enhance development profile with flexible worker configuration options
- [ ] Ensure production profile has complete worker support and validation
- [ ] Add profile-specific configuration validation and defaults
- [ ] Create configuration inheritance tests for worker settings
- [ ] Test worker system with all three profiles (test/development/production)
- [ ] Add profile-specific error messages and user guidance
- [ ] Verify backward compatibility with existing profile configurations
- [ ] Test configuration merging and override behavior for worker settings
- [ ] Document profile-specific worker behavior and configuration options
- [ ] **PROMPT 6 COMPLETE**

---

## PROMPT 7: Error Handling and Recovery

### Context
The worker system needs robust error handling that integrates with PAISE2's existing error handling patterns and provides reliable task processing with appropriate recovery mechanisms.

### Task
```
Implement comprehensive error handling and recovery mechanisms for the worker system, building on existing PAISE2 error handling patterns.

Requirements:
1. Task-level error handling: Retry policies, error classification, recovery strategies
2. Worker-level error handling: Worker crashes, context initialization failures
3. Queue-level error handling: Backend connectivity issues, queue corruption
4. System-level error handling: Profile mismatches, configuration errors
5. Error reporting: Integration with existing logging and monitoring systems
6. Graceful degradation: System continues functioning when workers are unavailable

Error handling patterns needed:
- Task retry policies using Huey's RetryTask with configurable backoff
- Worker restart policies for crashed workers (future: process management)
- Queue backend fallback and recovery mechanisms
- Configuration validation and error reporting
- Clear error messages and recovery guidance for users

Integration requirements:
- Use existing logging patterns and logger instances
- Integrate with existing error handling in plugin system
- Follow existing patterns in monitoring and health check systems
- Maintain consistency with existing CLI error handling
```

### Task List
- [ ] Implement comprehensive task-level error handling with RetryTask policies
- [ ] Add worker-level error handling and recovery mechanisms
- [ ] Create queue backend error handling and connectivity monitoring
- [ ] Add configuration validation and error reporting for worker settings
- [ ] Implement graceful degradation when workers are unavailable
- [ ] Create error classification and appropriate retry strategies
- [ ] Add error reporting integration with existing monitoring system
- [ ] Test error scenarios: task failures, worker crashes, queue backend issues
- [ ] Verify error handling works correctly across all profiles
- [ ] Document error handling behavior and recovery procedures
- [ ] **PROMPT 7 COMPLETE**

---

## PROMPT 8: Integration Testing and Validation

### Context
With all worker system components implemented, we need comprehensive integration testing to ensure the system works correctly end-to-end and integrates properly with the existing PAISE2 architecture.

### Task
```
Create comprehensive integration tests and validation for the complete worker system, ensuring it integrates properly with existing PAISE2 components.

Requirements:
1. End-to-end worker lifecycle testing: start, process tasks, monitor, stop
2. Profile integration testing: verify correct behavior across all profiles
3. Task processing testing: complete pipeline from task creation to completion
4. Error scenario testing: task failures, worker issues, queue problems
5. Performance testing: ensure system scales properly with worker concurrency
6. CLI integration testing: verify all commands work correctly
7. Monitoring integration testing: verify status reporting and health checks

Test scenarios needed:
- Complete content processing pipeline with background workers
- Worker startup and shutdown lifecycle management
- Task retry and error handling verification
- Profile-specific behavior validation (test/dev/production)
- CLI command integration and error handling
- Configuration loading and validation testing
- Monitoring and status reporting accuracy

Integration points to verify:
- TaskQueueProvider integration works correctly
- Existing plugin system remains functional
- Configuration system properly handles worker settings
- CLI system correctly integrates worker commands
- Monitoring system accurately reports worker status
```

### Task List
- [ ] Create comprehensive integration tests for worker lifecycle management
- [ ] Add end-to-end task processing tests with background workers
- [ ] Test profile-specific worker behavior (test/development/production)
- [ ] Create error scenario tests for task failures and worker issues
- [ ] Add performance tests for worker concurrency and queue processing
- [ ] Test CLI command integration and error handling scenarios
- [ ] Verify monitoring and status reporting accuracy with workers
- [ ] Create configuration validation and loading tests
- [ ] Test backward compatibility with existing PAISE2 functionality
- [ ] Add load testing for queue processing and worker management
- [ ] **PROMPT 8 COMPLETE**

---

## PROMPT 9: Documentation and User Guide

### Context
The worker system is now complete and integrated. We need comprehensive documentation that explains how to use the worker system and integrates with existing PAISE2 documentation patterns.

### Task
```
Create comprehensive documentation for the worker system that integrates with existing PAISE2 documentation and provides clear guidance for users and developers.

Requirements:
1. User guide: How to use worker commands and configure worker settings
2. Configuration reference: Complete worker configuration options and examples
3. Profile guide: Worker behavior in different profiles (test/dev/production)
4. Troubleshooting guide: Common issues and resolution procedures
5. Architecture documentation: How the worker system integrates with PAISE2
6. Developer guide: Extending the worker system and adding custom tasks (future)

Documentation needed:
- Worker system overview and architecture
- CLI command reference with examples
- Configuration options and profile-specific settings
- Common usage patterns and best practices
- Troubleshooting guide for worker and task issues
- Integration examples with existing PAISE2 workflows

Integration requirements:
- Follow existing documentation patterns and structure
- Update existing documentation to reference worker capabilities
- Provide clear migration guidance for existing users
- Include practical examples and use cases
- Document relationship to existing TaskQueueProvider system
```

### Task List
- [ ] Create comprehensive worker system user guide and overview
- [ ] Document all CLI commands with examples and usage patterns
- [ ] Create complete configuration reference for worker settings
- [ ] Add profile-specific documentation (test/development/production behavior)
- [ ] Create troubleshooting guide for common worker and task issues
- [ ] Document worker system architecture and integration points
- [ ] Update existing documentation to reference worker capabilities
- [ ] Add migration guide for users transitioning to background processing
- [ ] Create examples and best practices documentation
- [ ] Review and finalize all documentation for consistency and completeness
- [ ] **PROMPT 9 COMPLETE**

---

## PROMPT 10: Final Integration and System Validation

### Context
All worker system components are implemented and documented. This final prompt ensures everything works together correctly and the system is production-ready.

### Task
```
Perform final integration validation and system testing to ensure the worker system is production-ready and properly integrated with PAISE2.

Requirements:
1. Complete system validation: All components working together correctly
2. Performance validation: System performs well under realistic workloads
3. Compatibility validation: No regressions in existing PAISE2 functionality
4. Security validation: Worker system follows security best practices
5. Production readiness: System ready for real-world deployment
6. Quality assurance: All tests passing, code quality maintained

Validation areas:
- End-to-end system functionality with all profiles
- Performance under realistic content processing workloads
- Existing PAISE2 functionality remains unaffected
- Security considerations for background task processing
- Resource usage and cleanup behavior
- Error handling and recovery in realistic scenarios

Final checks:
- All 448+ tests continue to pass
- New functionality is thoroughly tested
- Documentation is complete and accurate
- System maintains PAISE2's quality standards
- No breaking changes to existing APIs
- Performance meets or exceeds expectations
```

### Task List
- [ ] Run complete test suite and verify all tests pass (448+ tests expected)
- [ ] Perform end-to-end system validation with realistic workloads
- [ ] Verify no regressions in existing PAISE2 functionality
- [ ] Test performance and resource usage under load
- [ ] Validate security considerations and best practices
- [ ] Review code quality and maintain existing standards
- [ ] Verify documentation completeness and accuracy
- [ ] Test production deployment scenarios and configurations
- [ ] Validate worker system with all three profiles under realistic conditions
- [ ] Final quality assurance review and system validation
- [ ] **PROMPT 10 COMPLETE**

---

## Implementation Summary

This prompt plan provides a systematic approach to implementing the PAISE2 worker system with the following key characteristics:

### Architectural Consistency
- **Builds on existing systems**: Leverages TaskQueueProvider, plugin architecture, CLI system
- **Profile-aware**: Different behavior for test/development/production environments
- **Configuration integration**: Uses existing configuration patterns and merging
- **Clean separation**: No shared state between main application and workers

### Incremental Development
- **Small, safe steps**: Each prompt builds incrementally on the previous
- **Strong testing**: Comprehensive testing at each stage
- **No orphaned code**: Everything integrates with existing systems
- **Backward compatibility**: No breaking changes to existing functionality

### Production Readiness
- **Robust error handling**: Comprehensive error scenarios and recovery
- **Performance considerations**: Proper scaling and resource management
- **Security awareness**: Follows security best practices
- **Operational support**: Monitoring, status reporting, troubleshooting

### Key Features Delivered
1. **Worker Management**: Start, stop, monitor background workers
2. **Profile Integration**: Appropriate behavior for test/dev/production
3. **Task Processing**: Enhanced task execution with proper error handling
4. **CLI Integration**: Seamless integration with existing CLI system
5. **Monitoring**: Comprehensive status reporting and health checks
6. **Configuration**: Flexible worker configuration with profile-specific defaults
7. **Documentation**: Complete user and developer documentation

The implementation maintains PAISE2's architectural principles while adding powerful background processing capabilities that enable the system to scale from development through production deployment.
