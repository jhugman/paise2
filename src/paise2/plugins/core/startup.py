# ABOUTME: Phased startup system for plugin infrastructure with singleton management
# ABOUTME: 5-phase startup sequence with dependency injection and config completing

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from paise2.utils.logging import SimpleInMemoryLogger

if TYPE_CHECKING:
    from typing import Any

    from huey import Huey

    from paise2.plugins.core.interfaces import (
        CacheManager,
        Configuration,
        DataStorage,
        Logger,
        StateStorage,
    )
    from paise2.plugins.core.registry import PluginManager

__all__ = [
    "Singletons",
    "StartupError",
    "StartupManager",
    "StartupPhase",
    "setup_tasks",
]


def setup_tasks(huey: Huey | None, singletons: Singletons) -> dict[str, Callable]:
    """
    Define tasks with the provided Huey instance and singletons.

    Implements the two-phase initialization pattern: first create TaskQueueProvider,
    then create singletons, then setup tasks with both.

    Args:
        huey: Huey instance for task definition (may be None for sync execution)
        singletons: System singletons for task implementation

    Returns:
        Dict mapping task names to task functions. Empty dict for sync execution.
    """
    if huey is None:
        # No tasks for synchronous execution
        return {}

    @huey.task()  # type: ignore[misc]
    def fetch_content_task(
        url: str, metadata: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Fetch content using appropriate ContentFetcher plugin."""
        # Placeholder implementation - will be enhanced in future prompts
        # with actual ContentFetcher integration
        _ = metadata  # Will be used in future implementation
        singletons.logger.info("Fetch task scheduled")
        return {"status": "success", "message": f"Fetched content from {url}"}

    @huey.task()  # type: ignore[misc]
    def extract_content_task(
        content: bytes | str, metadata: dict[str, Any]
    ) -> dict[str, Any]:
        """Extract content using appropriate ContentExtractor plugin."""
        # Placeholder implementation - will be enhanced in future prompts
        # with actual ContentExtractor integration
        _ = content  # Will be used in future implementation
        _ = metadata  # Will be used in future implementation
        singletons.logger.info("Extract task scheduled")
        return {"status": "success", "message": "Content extraction completed"}

    @huey.task()  # type: ignore[misc]
    def store_content_task(
        content: dict[str, Any], metadata: dict[str, Any]
    ) -> dict[str, Any]:
        """Store processed content in the data storage."""
        # Placeholder implementation - will be enhanced in future prompts
        # with actual DataStorage integration
        _ = content  # Will be used in future implementation
        _ = metadata  # Will be used in future implementation
        singletons.logger.info("Store task scheduled for processed content")
        return {"status": "success", "message": "Content stored successfully"}

    @huey.task()  # type: ignore[misc]
    def cleanup_cache_task(cache_ids: list[str]) -> dict[str, Any]:
        """Clean up specified cache entries."""
        # Placeholder implementation - will be enhanced in future prompts
        # with actual cache cleanup integration
        count = len(cache_ids)
        singletons.logger.info("Cache cleanup task scheduled")
        return {"status": "success", "message": f"Cleaned up {count} cache entries"}

    return {
        "fetch_content": fetch_content_task,
        "extract_content": extract_content_task,
        "store_content": store_content_task,
        "cleanup_cache": cleanup_cache_task,
    }


# Error messages constants
_SINGLETONS_NOT_CREATED = "Singletons not created during startup"
_NO_CONFIG_PROVIDERS = "No configuration providers found"
_NO_STATE_PROVIDERS = "No state storage providers found"
_NO_TASK_QUEUE_PROVIDERS = "No task queue providers found"
_NO_CACHE_PROVIDERS = "No cache providers found"
_NO_DATA_STORAGE_PROVIDERS = "No data storage providers found"
_NO_STATE_PROVIDERS_AVAILABLE = "No state storage providers available"


class StartupError(Exception):
    """Exception raised during startup phase failures."""


class StartupPhase:
    """Constants for startup phases."""

    BOOTSTRAP = 1
    SINGLETON_CONTRIBUTING = 2
    SINGLETON_CREATION = 3
    SINGLETON_USING = 4
    START = 5


class Singletons:
    """Container for application singletons created during startup."""

    def __init__(  # noqa: PLR0913
        self,
        logger: Logger,
        configuration: Configuration,
        state_storage: StateStorage,
        task_queue: Huey | None,
        cache: CacheManager,
        data_storage: DataStorage,
        tasks: dict[str, Any] | None = None,
    ):
        self.logger = logger
        self.configuration = configuration
        self.state_storage = state_storage
        self.task_queue = task_queue
        self.cache = cache
        self.data_storage = data_storage
        self.tasks = tasks or {}


class StartupManager:
    """Manages the phased startup sequence for the plugin system."""

    def __init__(self, plugin_manager: PluginManager):
        self.plugin_manager = plugin_manager
        self.bootstrap_logger = SimpleInMemoryLogger()
        self.current_phase = StartupPhase.BOOTSTRAP
        self.singletons: Singletons | None = None

    async def execute_startup(
        self, user_config_dict: dict[str, Any] | None = None
    ) -> Singletons:
        """Execute the complete startup sequence."""
        try:
            await self._phase_1_bootstrap()
            await self._phase_2_singleton_contributing()
            await self._phase_3_singleton_creation(user_config_dict)
            await self._phase_4_singleton_using()
            await self._phase_5_start()

            if self.singletons is None:
                raise StartupError(_SINGLETONS_NOT_CREATED)  # noqa: TRY301

            return self.singletons  # noqa: TRY300

        except Exception as e:
            error_msg = f"Startup failed in phase {self.current_phase}: {e}"
            self.bootstrap_logger.error(error_msg)  # noqa: TRY400
            raise StartupError(error_msg) from e

    async def phase_1_bootstrap(self) -> None:
        """Phase 1: Bootstrap - Create minimal logger and plugin system."""
        return await self._phase_1_bootstrap()

    async def phase_2_singleton_contributing(self) -> None:
        """Phase 2: Load singleton-contributing extensions."""
        return await self._phase_2_singleton_contributing()

    async def phase_3_singleton_creation(
        self, user_config_dict: dict[str, Any] | None = None
    ) -> None:
        """Phase 3: Create singletons from providers."""
        return await self._phase_3_singleton_creation(user_config_dict)

    async def phase_4_singleton_using(self) -> None:
        """Phase 4: Load singleton-using extensions."""
        return await self._phase_4_singleton_using()

    async def phase_5_start(self) -> None:
        """Phase 5: Start the system."""
        return await self._phase_5_start()

    async def _phase_1_bootstrap(self) -> None:
        """Phase 1: Bootstrap - Create minimal logger and plugin system."""
        self.current_phase = StartupPhase.BOOTSTRAP
        self.bootstrap_logger.info("Phase 1: Bootstrap starting")

        # Bootstrap is just logging setup, which is already done in __init__
        self.bootstrap_logger.info("Phase 1: Bootstrap complete")

    async def _phase_2_singleton_contributing(self) -> None:
        """Phase 2: Load singleton-contributing extensions."""
        self.current_phase = StartupPhase.SINGLETON_CONTRIBUTING
        self.bootstrap_logger.info("Phase 2: Loading singleton-contributing extensions")

        # Load plugins that contribute to singletons
        self.plugin_manager.discover_plugins()
        self.plugin_manager.load_plugins()

        # Validate that we have the required providers
        if not self.plugin_manager.get_configuration_providers():
            raise StartupError(_NO_CONFIG_PROVIDERS)

        if not self.plugin_manager.get_state_storage_providers():
            raise StartupError(_NO_STATE_PROVIDERS)

        if not self.plugin_manager.get_task_queue_providers():
            raise StartupError(_NO_TASK_QUEUE_PROVIDERS)

        if not self.plugin_manager.get_cache_providers():
            raise StartupError(_NO_CACHE_PROVIDERS)

        if not self.plugin_manager.get_data_storage_providers():
            raise StartupError(_NO_DATA_STORAGE_PROVIDERS)

        self.bootstrap_logger.info("Phase 2: Singleton-contributing extensions loaded")

    async def _phase_3_singleton_creation(
        self, user_config_dict: dict[str, Any] | None = None
    ) -> None:
        """Phase 3: Create singletons from providers."""
        self.current_phase = StartupPhase.SINGLETON_CREATION
        self.bootstrap_logger.info("Phase 3: Creating singletons")

        # Step 1: Load initial configuration from plugin providers and config dir
        from paise2.config.factory import ConfigurationFactory

        configuration_factory = ConfigurationFactory()
        initial_configuration = configuration_factory.load_initial_configuration(
            self.plugin_manager, user_config_dict=user_config_dict
        )

        # Step 2: Create state storage (needed for configuration completing)
        state_storage = self._create_state_storage_singleton(initial_configuration)

        # Step 3: Complete configuration with startup state and change detection
        final_configuration = configuration_factory.complete_configuration(
            initial_configuration, state_storage
        )

        # Step 4: Create other singletons
        cache = self._create_cache_singleton(final_configuration)
        task_queue = self._create_task_queue_singleton(final_configuration)
        data_storage = self._create_data_storage_singleton(final_configuration)

        # Step 5: Create logger and replay bootstrap logs
        logger = self._create_logger_singleton(final_configuration)
        self._replay_bootstrap_logs(logger)

        # Create initial singletons container (without tasks)
        initial_singletons = Singletons(
            logger=logger,
            configuration=final_configuration,
            state_storage=state_storage,
            task_queue=task_queue,
            cache=cache,
            data_storage=data_storage,
        )

        # Step 6: Setup tasks and create final singletons container
        tasks = setup_tasks(task_queue, initial_singletons)
        self.singletons = Singletons(
            logger=logger,
            configuration=final_configuration,
            state_storage=state_storage,
            task_queue=task_queue,
            cache=cache,
            data_storage=data_storage,
            tasks=tasks,
        )

        self.bootstrap_logger.info("Phase 3: Singletons created with task registry")

    async def _phase_4_singleton_using(self) -> None:
        """Phase 4: Load singleton-using extensions."""
        self.current_phase = StartupPhase.SINGLETON_USING
        self.bootstrap_logger.info("Phase 4: Loading singleton-using extensions")

        # Singleton-using extensions like ContentExtractor, ContentSource, etc.
        # For now, just log that they would be loaded here
        # Implementation will come in later prompts

        self.bootstrap_logger.info("Phase 4: Singleton-using extensions loaded")

    async def _phase_5_start(self) -> None:
        """Phase 5: Start the system."""
        self.current_phase = StartupPhase.START
        self.bootstrap_logger.info("Phase 5: Starting system")

        # System startup logic will be implemented in later prompts
        # For now, just mark that startup is complete

        self.bootstrap_logger.info("Phase 5: System started")

    def _create_state_storage_singleton(
        self, configuration: Configuration
    ) -> StateStorage:
        """Create the state storage singleton."""
        self.bootstrap_logger.info("Creating state storage singleton")

        providers = self.plugin_manager.get_state_storage_providers()
        if not providers:
            raise StartupError(_NO_STATE_PROVIDERS_AVAILABLE)

        # Use first provider (provider selection logic can be enhanced later)
        provider = providers[0]
        state_storage = provider.create_state_storage(configuration)

        self.bootstrap_logger.info("State storage singleton created")
        return state_storage

    def _create_task_queue_singleton(self, configuration: Configuration) -> Huey:
        """Create the task queue singleton."""
        self.bootstrap_logger.info("Creating task queue singleton")

        providers = self.plugin_manager.get_task_queue_providers()
        if not providers:
            error_msg = "No task queue providers available"
            raise StartupError(error_msg)

        # Use first provider (provider selection logic can be enhanced later)
        provider = providers[0]

        # Create task queue using provider
        task_queue = provider.create_task_queue(configuration)

        self.bootstrap_logger.info("Task queue singleton created")
        return task_queue

    def _create_cache_singleton(self, configuration: Configuration) -> CacheManager:
        """Create the cache singleton."""
        self.bootstrap_logger.info("Creating cache singleton")

        providers = self.plugin_manager.get_cache_providers()
        if not providers:
            error_msg = "No cache providers available"
            raise StartupError(error_msg)

        # Use first provider (provider selection logic can be enhanced later)
        provider = providers[0]
        cache = provider.create_cache(configuration)

        self.bootstrap_logger.info("Cache singleton created")
        return cache

    def _create_data_storage_singleton(
        self, configuration: Configuration
    ) -> DataStorage:
        """Create the data storage singleton."""
        self.bootstrap_logger.info("Creating data storage singleton")

        providers = self.plugin_manager.get_data_storage_providers()
        if not providers:
            error_msg = "No data storage providers available"
            raise StartupError(error_msg)

        # Use first provider (provider selection logic can be enhanced later)
        provider = providers[0]
        data_storage = provider.create_data_storage(configuration)

        self.bootstrap_logger.info("Data storage singleton created")
        return data_storage

    def _create_logger_singleton(self, configuration: Configuration) -> Any:
        """Create the logger singleton."""
        self.bootstrap_logger.info("Creating logger singleton")

        # For now, return a simple logger
        # Real logger creation based on configuration will be implemented later
        # Configuration will be used to set log level, format, handlers, etc.
        from paise2.utils.logging import SimpleInMemoryLogger

        # Placeholder: configuration will control logger creation
        _ = configuration  # Will be used in real implementation
        logger = SimpleInMemoryLogger()
        self.bootstrap_logger.info("Logger singleton created")
        return logger

    def _replay_bootstrap_logs(self, logger: Any) -> None:
        """Replay bootstrap logs to the real logger."""
        self.bootstrap_logger.info("Replaying bootstrap logs")

        bootstrap_logs = self.bootstrap_logger.get_logs()
        for timestamp, level, message in bootstrap_logs:
            # Replay to real logger
            getattr(logger, level.lower(), logger.info)(
                f"[BOOTSTRAP {timestamp}] {message}"
            )

        self.bootstrap_logger.info("Bootstrap logs replayed")


# Factory functions for common startup patterns
def create_test_startup_manager() -> StartupManager:
    """Create a startup manager configured for testing."""
    from paise2.profiles.factory import create_test_plugin_manager

    plugin_manager = create_test_plugin_manager()
    return StartupManager(plugin_manager)


def create_development_startup_manager() -> StartupManager:
    """Create a startup manager configured for development."""
    from paise2.profiles.factory import create_development_plugin_manager

    plugin_manager = create_development_plugin_manager()
    return StartupManager(plugin_manager)


def create_production_startup_manager() -> StartupManager:
    """Create a startup manager configured for production."""
    from paise2.profiles.factory import create_production_plugin_manager

    plugin_manager = create_production_plugin_manager()
    return StartupManager(plugin_manager)
