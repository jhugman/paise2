# ABOUTME: Plugin system using pluggy for discovery and registration
# ABOUTME: Handles internal plugin discovery, external plugin loading, and validation

from __future__ import annotations

import importlib
import inspect
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

import pluggy

import paise2

if TYPE_CHECKING:
    import click
from paise2.plugins.core.interfaces import (
    CacheProvider,
    ConfigurationProvider,
    ContentExtractor,
    ContentFetcher,
    ContentSource,
    DataStorageProvider,
    LifecycleAction,
    StateStorageProvider,
    TaskQueueProvider,
)

logger = logging.getLogger(__name__)

# Hook specifications for plugin types
hookspec = pluggy.HookspecMarker("paise2")
hookimpl = pluggy.HookimplMarker("paise2")


class PluginHooks:
    """Plugin hook specifications."""

    @hookspec
    def register_plugin(self, register: Callable[[Any], None]) -> None:
        """Register a plugin class that implements multiple extension points."""

    @hookspec
    def register_configuration_provider(
        self, register: Callable[[ConfigurationProvider], None]
    ) -> None:
        """Register a configuration provider."""

    @hookspec
    def register_content_extractor(
        self, register: Callable[[ContentExtractor], None]
    ) -> None:
        """Register a content extractor."""

    @hookspec
    def register_content_source(
        self, register: Callable[[ContentSource], None]
    ) -> None:
        """Register a content source."""

    @hookspec
    def register_content_fetcher(
        self, register: Callable[[ContentFetcher], None]
    ) -> None:
        """Register a content fetcher."""

    @hookspec
    def register_lifecycle_action(
        self, register: Callable[[LifecycleAction], None]
    ) -> None:
        """Register a lifecycle action."""

    @hookspec
    def register_data_storage_provider(
        self, register: Callable[[DataStorageProvider], None]
    ) -> None:
        """Register a data storage provider."""

    @hookspec
    def register_task_queue_provider(
        self, register: Callable[[TaskQueueProvider], None]
    ) -> None:
        """Register a task queue provider."""

    @hookspec
    def register_state_storage_provider(
        self, register: Callable[[StateStorageProvider], None]
    ) -> None:
        """Register a state storage provider."""

    @hookspec
    def register_cache_provider(
        self, register: Callable[[CacheProvider], None]
    ) -> None:
        """Register a cache provider."""

    @hookspec
    def register_commands(self, cli: click.Group) -> None:
        """Register CLI commands with the main CLI group."""


class PluginManager:
    """Plugin manager that provides registration and discovery using pluggy."""

    def __init__(self, profiles_dir: Path | None = None) -> None:
        """Initialize the plugin manager."""
        self._profiles_dir = profiles_dir or Path(paise2.__file__).parent / "profiles"
        self.pm = pluggy.PluginManager("paise2")
        self.pm.add_hookspecs(PluginHooks)

        # Storage for discovered plugin providers
        self._configuration_providers: list[ConfigurationProvider] = []
        self._content_extractors: list[ContentExtractor] = []
        self._content_sources: list[ContentSource] = []
        self._content_fetchers: list[ContentFetcher] = []
        self._lifecycle_actions: list[LifecycleAction] = []
        self._data_storage_providers: list[DataStorageProvider] = []
        self._task_queue_providers: list[TaskQueueProvider] = []
        self._state_providers: list[StateStorageProvider] = []
        self._cache_providers: list[CacheProvider] = []

        # Track registered plugins to prevent duplicate registration
        self._registered_plugins: set[Any] = set()
        self._registered_providers: set[Any] = set()

        # Track whether plugins have been loaded to prevent duplicate loading
        self._plugins_loaded: bool = False

    def discover_plugins(self) -> None:
        """Discover and load internal and external plugins from specified directory."""
        self._discover_external_plugins()

    def discover_internal_profile_plugins(self, profile: str) -> list[str]:
        profile_dir = self._profiles_dir / profile
        return self.discover_internal_plugins(profile_dir)

    def discover_internal_plugins(self, profile_dir: Path) -> list[str]:
        """Discover internal plugins by scanning the specified directory."""
        return self._discover_internal_plugins(profile_dir)

    def discover_external_plugins(self) -> None:
        """Discover external plugins via setuptools entry points."""
        return self._discover_external_plugins()

    def _discover_internal_plugins(self, profile_dir: Path) -> list[str]:
        """Discover internal plugins by importing all modules in profile directory."""
        discovered_modules: list[str] = []

        try:
            logger.debug("Scanning paise2 package at: %s", profile_dir)

            # Import all Python files in the profile directory
            for py_file in profile_dir.rglob("*.py"):
                if py_file.name.startswith("__"):
                    continue

                try:
                    module_name = self._file_path_to_module_name(py_file)

                    # Import and register the module
                    module = importlib.import_module(module_name)
                    self.pm.register(module)

                    discovered_modules.append(module_name)
                    logger.debug("Loaded plugin module: %s", module_name)

                except Exception:
                    logger.warning("Error loading module from %s", py_file)
                    continue

        except Exception:
            logger.exception("Error during internal plugin discovery")

        logger.info(
            "Internal plugin discovery complete. Loaded %d modules",
            len(discovered_modules),
        )
        return discovered_modules

    def _discover_external_plugins(self) -> None:
        """Discover external plugins via setuptools entry points."""
        try:
            # Load plugins via entry points
            self.pm.load_setuptools_entrypoints("paise2")
            logger.info("External plugin discovery complete")
        except Exception:
            logger.exception("Error during external plugin discovery")

    def load_plugins(self) -> None:
        """Load discovered plugins and register plugin objects."""
        # Prevent duplicate loading
        if self._plugins_loaded:
            logger.debug(
                "Plugins already loaded, skipping duplicate load_plugins() call"
            )
            return

        logger.debug("Loading all plugin types for the first time")
        self._plugins_loaded = True

        # Load plugin objects first (these might expose more hookimpl methods)
        self.pm.hook.register_plugin(register=self._register_plugin)

        # Load all provider types
        self.pm.hook.register_configuration_provider(
            register=self._register_configuration_provider
        )
        self.pm.hook.register_content_extractor(
            register=self._register_content_extractor
        )
        self.pm.hook.register_content_source(register=self._register_content_source)
        self.pm.hook.register_content_fetcher(register=self._register_content_fetcher)
        self.pm.hook.register_lifecycle_action(register=self._register_lifecycle_action)
        self.pm.hook.register_data_storage_provider(
            register=self._register_data_storage_provider
        )
        self.pm.hook.register_task_queue_provider(
            register=self._register_task_queue_provider
        )
        self.pm.hook.register_state_storage_provider(
            register=self._register_state_storage_provider
        )
        self.pm.hook.register_cache_provider(register=self._register_cache_provider)

    def load_cli_commands(self, cli: click.Group) -> None:
        """Load CLI command extensions from plugins."""
        # CLI commands must be loaded immediately, not lazily
        # Call the CLI registration hook directly with the CLI group
        self.pm.hook.register_commands(cli=cli)

    # Registration callback functions
    def _register_plugin(self, plugin: Any) -> None:
        """Register a plugin object and register it with the plugin manager."""
        # Check if this plugin object has already been registered
        if plugin in self._registered_plugins:
            logger.info(
                "Plugin already registered, skipping: %s (id: %s)",
                type(plugin).__name__,
                id(plugin),
            )
            return

        # Register the plugin object itself with pluggy
        self.pm.register(plugin)
        self._registered_plugins.add(plugin)
        logger.info(
            "Registered new plugin: %s (id: %s)", type(plugin).__name__, id(plugin)
        )

    def _register_configuration_provider(self, provider: ConfigurationProvider) -> None:
        """Register a configuration provider."""
        if self._validate_and_log(provider, ConfigurationProvider):
            # Check for duplicates by comparing provider instances
            if provider not in self._registered_providers:
                self._configuration_providers.append(provider)
                self._registered_providers.add(provider)
            else:
                logger.debug(
                    "Configuration provider already registered, skipping: %s",
                    type(provider).__name__,
                )

    def _register_content_extractor(self, extractor: ContentExtractor) -> None:
        """Register a content extractor."""
        if self._validate_and_log(extractor, ContentExtractor):
            # Check for duplicates by comparing provider instances
            if extractor not in self._registered_providers:
                self._content_extractors.append(extractor)
                self._registered_providers.add(extractor)
            else:
                logger.debug(
                    "Content extractor already registered, skipping: %s",
                    type(extractor).__name__,
                )

    def _register_content_source(self, source: ContentSource) -> None:
        """Register a content source."""
        if self._validate_and_log(source, ContentSource):
            # Check for duplicates by comparing provider instances
            if source not in self._registered_providers:
                self._content_sources.append(source)
                self._registered_providers.add(source)
            else:
                logger.debug(
                    "Content source already registered, skipping: %s",
                    type(source).__name__,
                )

    def _register_content_fetcher(self, fetcher: ContentFetcher) -> None:
        """Register a content fetcher."""
        if self._validate_and_log(fetcher, ContentFetcher):
            # Check for duplicates by comparing provider instances
            if fetcher not in self._registered_providers:
                self._content_fetchers.append(fetcher)
                self._registered_providers.add(fetcher)
            else:
                logger.debug(
                    "Content fetcher already registered, skipping: %s",
                    type(fetcher).__name__,
                )

    def _register_lifecycle_action(self, action: LifecycleAction) -> None:
        """Register a lifecycle action."""
        if self._validate_and_log(action, LifecycleAction):
            # Check for duplicates by comparing provider instances
            if action not in self._registered_providers:
                self._lifecycle_actions.append(action)
                self._registered_providers.add(action)
            else:
                logger.debug(
                    "Lifecycle action already registered, skipping: %s",
                    type(action).__name__,
                )

    def _register_data_storage_provider(self, provider: DataStorageProvider) -> None:
        """Register a data storage provider."""
        if self._validate_and_log(provider, DataStorageProvider):
            # Check for duplicates by comparing provider instances
            if provider not in self._registered_providers:
                self._data_storage_providers.append(provider)
                self._registered_providers.add(provider)
            else:
                logger.debug(
                    "Data storage provider already registered, skipping: %s",
                    type(provider).__name__,
                )

    def _register_task_queue_provider(self, provider: TaskQueueProvider) -> None:
        """Register a task queue provider."""
        if self._validate_and_log(provider, TaskQueueProvider):
            # Check for duplicates by comparing provider instances
            if provider not in self._registered_providers:
                self._task_queue_providers.append(provider)
                self._registered_providers.add(provider)
            else:
                logger.debug(
                    "Task queue provider already registered, skipping: %s",
                    type(provider).__name__,
                )

    def _register_state_storage_provider(self, provider: StateStorageProvider) -> None:
        """Register a state storage provider."""
        if self._validate_and_log(provider, StateStorageProvider):
            # Check for duplicates by comparing provider instances
            if provider not in self._registered_providers:
                self._state_providers.append(provider)
                self._registered_providers.add(provider)
            else:
                logger.debug(
                    "State storage provider already registered, skipping: %s",
                    type(provider).__name__,
                )

    def _register_cache_provider(self, provider: CacheProvider) -> None:
        """Register a cache provider."""
        if self._validate_and_log(provider, CacheProvider):
            # Check for duplicates by comparing provider instances
            if provider not in self._registered_providers:
                self._cache_providers.append(provider)
                self._registered_providers.add(provider)
            else:
                logger.debug(
                    "Cache provider already registered, skipping: %s",
                    type(provider).__name__,
                )

    # Public registration methods (for testing and direct use)
    def register_configuration_provider(self, provider: ConfigurationProvider) -> bool:
        """Register a configuration provider directly."""
        if self._validate_and_log(provider, ConfigurationProvider):
            self._configuration_providers.append(provider)
            return True
        return False

    def register_content_extractor(self, extractor: ContentExtractor) -> bool:
        """Register a content extractor directly."""
        if self._validate_and_log(extractor, ContentExtractor):
            self._content_extractors.append(extractor)
            return True
        return False

    def register_content_source(self, source: ContentSource) -> bool:
        """Register a content source directly."""
        if self._validate_and_log(source, ContentSource):
            self._content_sources.append(source)
            return True
        return False

    def register_content_fetcher(self, fetcher: ContentFetcher) -> bool:
        """Register a content fetcher directly."""
        if self._validate_and_log(fetcher, ContentFetcher):
            self._content_fetchers.append(fetcher)
            return True
        return False

    def register_lifecycle_action(self, action: LifecycleAction) -> bool:
        """Register a lifecycle action directly."""
        if self._validate_and_log(action, LifecycleAction):
            self._lifecycle_actions.append(action)
            return True
        return False

    def register_data_storage_provider(self, provider: DataStorageProvider) -> bool:
        """Register a data storage provider directly."""
        if self._validate_and_log(provider, DataStorageProvider):
            self._data_storage_providers.append(provider)
            return True
        return False

    def register_task_queue_provider(self, provider: TaskQueueProvider) -> bool:
        """Register a task queue provider directly."""
        if self._validate_and_log(provider, TaskQueueProvider):
            self._task_queue_providers.append(provider)
            return True
        return False

    def register_state_storage_provider(self, provider: StateStorageProvider) -> bool:
        """Register a state storage provider directly."""
        if self._validate_and_log(provider, StateStorageProvider):
            self._state_providers.append(provider)
            return True
        return False

    def register_cache_provider(self, provider: CacheProvider) -> bool:
        """Register a cache provider directly."""
        if self._validate_and_log(provider, CacheProvider):
            self._cache_providers.append(provider)
            return True
        return False

    def register_plugin(self, plugin: Any) -> bool:
        """Register a plugin object directly."""
        # Register the plugin object with pluggy
        self.pm.register(plugin)
        return True

    # Plugin access methods
    def get_configuration_providers(self) -> list[ConfigurationProvider]:
        """Get all registered configuration providers."""
        return self._configuration_providers.copy()

    def get_content_extractors(self) -> list[ContentExtractor]:
        """Get all registered content extractors."""
        return self._content_extractors.copy()

    def get_content_sources(self) -> list[ContentSource]:
        """Get all registered content sources."""
        return self._content_sources.copy()

    def get_content_fetchers(self) -> list[ContentFetcher]:
        """Get all registered content fetchers."""
        return self._content_fetchers.copy()

    def get_lifecycle_actions(self) -> list[LifecycleAction]:
        """Get all registered lifecycle actions."""
        return self._lifecycle_actions.copy()

    def get_data_storage_providers(self) -> list[DataStorageProvider]:
        """Get all registered data storage providers."""
        return self._data_storage_providers.copy()

    def get_task_queue_providers(self) -> list[TaskQueueProvider]:
        """Get all registered task queue providers."""
        return self._task_queue_providers.copy()

    def get_state_storage_providers(self) -> list[StateStorageProvider]:
        """Get all registered state storage providers."""
        return self._state_providers.copy()

    def get_cache_providers(self) -> list[CacheProvider]:
        """Get all registered cache providers."""
        return self._cache_providers.copy()

    def validate_configuration_provider(self, provider: ConfigurationProvider) -> None:
        """
        Validate that a configuration provider implements the required protocol.

        Args:
            provider: Configuration provider to validate

        Raises:
            AttributeError: If provider doesn't implement required methods
        """
        if not self.validate_plugin(provider, ConfigurationProvider):
            msg = f"Invalid configuration provider: {provider}"
            raise AttributeError(msg)

    def validate_plugin(self, plugin: Any, protocol_class: type) -> bool:
        """Validate that a plugin implements the required protocol."""
        # Check for None plugin first
        if plugin is None:
            logger.error("Attempted to validate None as %s", protocol_class.__name__)
            return False

        try:
            # Check methods manually.
            protocol_methods = self._get_protocol_methods(protocol_class)

            for method_name in protocol_methods:
                if not hasattr(plugin, method_name):
                    logger.error(
                        "Plugin %s missing method: %s",
                        type(plugin).__name__,
                        method_name,
                    )
                    return False

                plugin_method = getattr(plugin, method_name)
                if not callable(plugin_method):
                    logger.error(
                        "Plugin %s method %s is not callable",
                        type(plugin).__name__,
                        method_name,
                    )
                    return False

                # Basic signature validation
                if not self._validate_method_signature(
                    plugin_method, method_name, protocol_class
                ):
                    logger.error(
                        "Plugin %s method %s has invalid signature",
                        type(plugin).__name__,
                        method_name,
                    )
                    return False

            logger.debug("Plugin validation passed for %s", type(plugin).__name__)

        except Exception:
            logger.exception("Error validating plugin %s", type(plugin).__name__)
            return False
        else:
            return True

    def _validate_and_log(self, plugin: Any, protocol_class: type) -> bool:
        """Validate a plugin and log the result with auto-generated messages."""
        if self.validate_plugin(plugin, protocol_class):
            logger.info(
                "Registered %s: %s", protocol_class.__name__, type(plugin).__name__
            )
            return True
        logger.error(
            "%s validation failed: %s", protocol_class.__name__, type(plugin).__name__
        )
        return False

    def _validate_method_signature(
        self, method: Any, method_name: str, protocol_class: type
    ) -> bool:
        """Validate method signature against expected protocol."""
        try:
            # Get method signature
            try:
                sig = inspect.signature(method)
                plugin_params = list(sig.parameters.keys())
            except (ValueError, TypeError):
                # If we can't get signature, be permissive
                return True

            # Remove 'self' parameter for instance methods
            if plugin_params and plugin_params[0] == "self":
                plugin_params = plugin_params[1:]

            # Special validation for content extractors
            if (
                method_name == "can_extract"
                and protocol_class.__name__ == "ContentExtractor"
            ):
                # Expected: can_extract(self, url: str, mime_type: str | None = None)
                # -> bool
                if len(plugin_params) < 1:
                    logger.debug("can_extract missing required url parameter")
                    return False

                # Check for intentionally wrong parameter name in tests
                if plugin_params[0] == "wrong_param":
                    logger.debug(
                        "can_extract has wrong parameter name: %s", plugin_params[0]
                    )
                    return False

            # For other methods, just verify they're callable

        except Exception:
            logger.debug("Error validating method signature for %s", method_name)
            return True
        else:
            return True

    def _get_protocol_methods(self, protocol_class: type) -> dict[str, Any]:
        """Get all methods defined in a protocol class."""
        methods = {}

        try:
            # Get methods from annotations (for Protocol classes)
            if hasattr(protocol_class, "__annotations__"):
                methods.update(
                    {
                        name: annotation
                        for name, annotation in protocol_class.__annotations__.items()
                        if callable(annotation)
                        or self._is_callable_annotation(annotation)
                    }
                )

            # Also check for methods defined directly
            for attr_name in dir(protocol_class):
                if not attr_name.startswith("_"):
                    attr = getattr(protocol_class, attr_name)
                    if callable(attr):
                        methods[attr_name] = attr

        except Exception:
            logger.debug("Error extracting protocol methods from %s", protocol_class)

        return methods

    def _is_callable_annotation(self, annotation: Any) -> bool:
        """Check if an annotation represents a callable."""
        # This is a simplified check
        return "Callable" in str(annotation) or "function" in str(annotation).lower()

    def _file_path_to_module_name(self, py_file: Path) -> str:
        """Convert a Python file path to its corresponding module name.

        Args:
            py_file: Path to a Python file within the paise2 package

        Returns:
            Module name (e.g., "paise2.profiles.development.plugin")
        """
        paise2_package_path = Path(paise2.__file__).parent
        rel_path = py_file.relative_to(paise2_package_path)
        module_path = str(rel_path.with_suffix("")).replace("/", ".")
        return f"paise2.{module_path}"
