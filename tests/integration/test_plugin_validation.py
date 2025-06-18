# ABOUTME: System validation and health checking tools for the plugin system
# ABOUTME: Provides utilities for plugin compatibility and system diagnostics

from __future__ import annotations

from typing import Any

from paise2.plugins.core.interfaces import (  # noqa: TC001
    ConfigurationProvider,
    ContentExtractor,
    ContentFetcher,
    ContentSource,
    LifecycleAction,
)
from paise2.plugins.core.manager import PluginSystem
from paise2.plugins.core.tasks import TaskQueue
from tests.fixtures import create_test_plugin_manager_with_mocks


class PluginCompatibilityChecker:
    """Utility class for checking plugin compatibility and interface compliance."""

    def __init__(self, plugin_system: PluginSystem):
        self.plugin_system = plugin_system
        self.validation_results: dict[str, list[str]] = {}

    def check_all_plugins(self) -> dict[str, list[str]]:
        """Check compatibility of all registered plugins."""
        plugin_manager = self.plugin_system.get_plugin_manager()

        # Check each plugin type
        self._check_configuration_providers(
            plugin_manager.get_configuration_providers()
        )
        self._check_content_extractors(plugin_manager.get_content_extractors())
        self._check_content_sources(plugin_manager.get_content_sources())
        self._check_content_fetchers(plugin_manager.get_content_fetchers())
        self._check_lifecycle_actions(plugin_manager.get_lifecycle_actions())

        return self.validation_results

    def _check_configuration_providers(
        self, providers: list[ConfigurationProvider]
    ) -> None:
        """Check configuration provider compatibility."""
        issues = []

        for i, provider in enumerate(providers):
            try:
                # Test required methods
                config = provider.get_default_configuration()
                config_id = provider.get_configuration_id()

                # Validate return types
                if not isinstance(config, str):
                    issues.append(  # type: ignore[unreachable]
                        f"Provider {i}: get_default_configuration() must return str, "
                        f"got {type(config)}"
                    )

                if not isinstance(config_id, str):
                    issues.append(  # type: ignore[unreachable]
                        f"Provider {i}: get_configuration_id() must return str, "
                        f"got {type(config_id)}"
                    )

                # Validate YAML content
                if config.strip():
                    import yaml

                    try:
                        yaml.safe_load(config)
                    except yaml.YAMLError as e:
                        issues.append(f"Provider {i}: Invalid YAML configuration: {e}")

            except Exception as e:  # noqa: PERF203
                issues.append(f"Provider {i}: Error during validation: {e}")

        self.validation_results["configuration_providers"] = issues

    def _check_content_extractors(self, extractors: list[ContentExtractor]) -> None:
        """Check content extractor compatibility."""
        issues = []

        for i, extractor in enumerate(extractors):
            try:
                # Test required methods
                can_extract_result = extractor.can_extract("test://example.txt")
                mime_types = extractor.preferred_mime_types()

                # Validate return types
                if not isinstance(can_extract_result, bool):
                    issues.append(  # type: ignore[unreachable]
                        f"Extractor {i}: can_extract() must return bool, "
                        f"got {type(can_extract_result)}"
                    )

                if not isinstance(mime_types, list):
                    issues.append(  # type: ignore[unreachable]
                        f"Extractor {i}: preferred_mime_types() must return list, "
                        f"got {type(mime_types)}"
                    )
                elif not all(isinstance(mt, str) for mt in mime_types):
                    issues.append(
                        f"Extractor {i}: preferred_mime_types() must return list of str"
                    )

                # Test with different inputs
                test_urls = [
                    "http://example.com/doc.pdf",
                    "file:///path/to/doc.txt",
                    "",
                    "invalid-url",
                ]

                for url in test_urls:
                    try:
                        result = extractor.can_extract(url)
                        if not isinstance(result, bool):
                            issues.append(  # type: ignore[unreachable]
                                f"Extractor {i}: can_extract('{url}') returned "
                                f"{type(result)}, expected bool"
                            )
                    except Exception as e:  # noqa: PERF203
                        issues.append(f"Extractor {i}: can_extract('{url}') raised {e}")

            except Exception as e:  # noqa: PERF203
                issues.append(f"Extractor {i}: Error during validation: {e}")

        self.validation_results["content_extractors"] = issues

    def _check_content_sources(self, sources: list[ContentSource]) -> None:
        """Check content source compatibility."""
        issues = []

        for i, source in enumerate(sources):
            try:
                # Verify required methods exist and are callable
                if not hasattr(source, "start_source") or not callable(
                    source.start_source
                ):
                    issues.append(f"Source {i}: Missing or non-callable start_source")

                if not hasattr(source, "stop_source") or not callable(
                    source.stop_source
                ):
                    issues.append(f"Source {i}: Missing or non-callable stop_source")

                # Check method signatures (basic check)
                import inspect

                start_sig = inspect.signature(source.start_source)
                if len(start_sig.parameters) != 1:
                    issues.append(
                        f"Source {i}: start_source should take exactly 1 parameter "
                        f"(host)"
                    )

                stop_sig = inspect.signature(source.stop_source)
                if len(stop_sig.parameters) != 1:
                    issues.append(
                        f"Source {i}: stop_source should take exactly 1 parameter "
                        f"(host)"
                    )

            except Exception as e:  # noqa: PERF203
                issues.append(f"Source {i}: Error during validation: {e}")

        self.validation_results["content_sources"] = issues

    def _check_content_fetchers(self, fetchers: list[ContentFetcher]) -> None:
        """Check content fetcher compatibility."""
        issues = []

        for i, fetcher in enumerate(fetchers):
            try:
                # Verify required methods exist and are callable
                if not hasattr(fetcher, "can_fetch") or not callable(fetcher.can_fetch):
                    issues.append(f"Fetcher {i}: Missing or non-callable can_fetch")

                if not hasattr(fetcher, "fetch") or not callable(fetcher.fetch):
                    issues.append(f"Fetcher {i}: Missing or non-callable fetch")

                # Check method signatures (basic check)
                import inspect

                can_fetch_sig = inspect.signature(fetcher.can_fetch)
                if len(can_fetch_sig.parameters) != 2:
                    issues.append(
                        f"Fetcher {i}: can_fetch should take exactly 2 parameters "
                        f"(host, url)"
                    )

                fetch_sig = inspect.signature(fetcher.fetch)
                if len(fetch_sig.parameters) != 2:
                    issues.append(
                        f"Fetcher {i}: fetch should take exactly 2 parameters "
                        f"(host, url)"
                    )

            except Exception as e:  # noqa: PERF203
                issues.append(f"Fetcher {i}: Error during validation: {e}")

        self.validation_results["content_fetchers"] = issues

    def _check_lifecycle_actions(self, actions: list[LifecycleAction]) -> None:
        """Check lifecycle action compatibility."""
        issues = []

        for i, action in enumerate(actions):
            try:
                # Verify required methods exist and are callable
                if not hasattr(action, "on_start") or not callable(action.on_start):
                    issues.append(f"Action {i}: Missing or non-callable on_start")

                if not hasattr(action, "on_stop") or not callable(action.on_stop):
                    issues.append(f"Action {i}: Missing or non-callable on_stop")

                # Check method signatures (basic check)
                import inspect

                start_sig = inspect.signature(action.on_start)
                if len(start_sig.parameters) != 1:
                    issues.append(
                        f"Action {i}: on_start should take exactly 1 parameter (host)"
                    )

                stop_sig = inspect.signature(action.on_stop)
                if len(stop_sig.parameters) != 1:
                    issues.append(
                        f"Action {i}: on_stop should take exactly 1 parameter (host)"
                    )

            except Exception as e:  # noqa: PERF203
                issues.append(f"Action {i}: Error during validation: {e}")

        self.validation_results["lifecycle_actions"] = issues


class SystemHealthDiagnostics:
    """System health and diagnostics utilities."""

    def __init__(self, plugin_system: PluginSystem):
        self.plugin_system = plugin_system

    def run_full_health_check(self) -> dict[str, Any]:
        """Run a comprehensive system health check."""
        health_report: dict[str, Any] = {
            "system_running": False,
            "singletons_available": False,
            "configuration_accessible": False,
            "state_storage_functional": False,
            "task_queue_functional": False,
            "cache_functional": False,
            "data_storage_functional": False,
            "plugin_counts": {},
            "errors": [],
        }

        try:
            # Check if system is running
            health_report["system_running"] = self.plugin_system.is_running()

            if not health_report["system_running"]:
                health_report["errors"].append("Plugin system is not running")
                return health_report

            # Check singletons availability
            try:
                singletons = self.plugin_system.get_singletons()
                health_report["singletons_available"] = singletons is not None
            except Exception as e:
                health_report["errors"].append(f"Cannot access singletons: {e}")
                return health_report

            # Check each singleton
            self._check_configuration_health(singletons, health_report)
            self._check_state_storage_health(singletons, health_report)
            self._check_cache_health(singletons, health_report)
            self._check_data_storage_health(singletons, health_report)
            self._check_job_queue_health(singletons, health_report)

            # Check plugin counts
            self._check_plugin_counts(health_report)

        except Exception as e:
            health_report["errors"].append(f"Health check failed: {e}")

        return health_report

    def _check_configuration_health(
        self, singletons: Any, health_report: dict[str, Any]
    ) -> None:
        """Check configuration system health."""
        try:
            config = singletons.configuration
            # Test basic configuration access
            test_value = config.get("nonexistent.key", "default_value")
            health_report["configuration_accessible"] = test_value == "default_value"
        except Exception as e:
            health_report["errors"].append(f"Configuration health check failed: {e}")

    def _check_state_storage_health(
        self, singletons: Any, health_report: dict[str, Any]
    ) -> None:
        """Check state storage system health."""
        try:
            state_storage = singletons.state_storage
            # Test basic state operations
            test_key = "health_check_state"
            test_value = "health_check_value"

            state_storage.store("health_check", test_key, test_value)
            retrieved = state_storage.get("health_check", test_key)

            health_report["state_storage_functional"] = retrieved == test_value
        except Exception as e:
            health_report["errors"].append(f"State storage health check failed: {e}")

    def _check_cache_health(
        self, singletons: Any, health_report: dict[str, Any]
    ) -> None:
        """Check cache system health."""
        try:
            import asyncio

            async def check_cache() -> bool:
                cache = singletons.cache
                # Test basic cache operations
                cache_id = await cache.save(
                    "health_check", "health_check_content", ".txt"
                )
                retrieved = await cache.get(cache_id)
                return retrieved == "health_check_content"

            health_report["cache_functional"] = asyncio.run(check_cache())
        except Exception as e:
            health_report["errors"].append(f"Cache health check failed: {e}")

    def _check_data_storage_health(
        self, singletons: Any, health_report: dict[str, Any]
    ) -> None:
        """Check data storage system health."""
        try:
            import asyncio

            async def check_storage() -> bool:
                from paise2.models import Metadata
                from tests.fixtures.mock_plugins import MockDataStorageHost

                storage = singletons.data_storage
                host = MockDataStorageHost()

                # Test basic storage operations
                metadata = Metadata(source_url="health://check.txt")
                item_id = await storage.add_item(host, "health_content", metadata)
                retrieved = await storage.find_item(item_id)

                return (
                    retrieved is not None
                    and retrieved.source_url == "health://check.txt"
                )

            health_report["data_storage_functional"] = asyncio.run(check_storage())
        except Exception as e:
            health_report["errors"].append(f"Data storage health check failed: {e}")

    def _check_job_queue_health(
        self, singletons: Any, health_report: dict[str, Any]
    ) -> None:
        """Check task queue system health."""
        try:
            # Check that task queue is available and functional
            task_queue = singletons.task_queue

            health_report["task_queue_functional"] = (
                task_queue is not None and isinstance(task_queue, TaskQueue)
            )
        except Exception as e:
            health_report["errors"].append(f"Task queue health check failed: {e}")

    def _check_plugin_counts(self, health_report: dict[str, Any]) -> None:
        """Check plugin registration counts."""
        try:
            plugin_manager = self.plugin_system.get_plugin_manager()

            health_report["plugin_counts"] = {
                "configuration_providers": len(
                    plugin_manager.get_configuration_providers()
                ),
                "data_storage_providers": len(
                    plugin_manager.get_data_storage_providers()
                ),
                "task_queue_providers": len(plugin_manager.get_task_queue_providers()),
                "state_storage_providers": len(
                    plugin_manager.get_state_storage_providers()
                ),
                "cache_providers": len(plugin_manager.get_cache_providers()),
                "content_extractors": len(plugin_manager.get_content_extractors()),
                "content_sources": len(plugin_manager.get_content_sources()),
                "content_fetchers": len(plugin_manager.get_content_fetchers()),
                "lifecycle_actions": len(plugin_manager.get_lifecycle_actions()),
            }
        except Exception as e:
            health_report["errors"].append(f"Plugin count check failed: {e}")


class TestPluginSystemValidation:
    """Test plugin system validation and health checking."""

    def test_plugin_compatibility_checker(self) -> None:
        """Test the plugin compatibility checker functionality."""
        test_plugin_manager = create_test_plugin_manager_with_mocks()
        plugin_system = PluginSystem(test_plugin_manager)

        try:
            plugin_system.bootstrap()

            checker = PluginCompatibilityChecker(plugin_system)
            results = checker.check_all_plugins()

            # Should have checked all plugin types
            expected_types = [
                "configuration_providers",
                "content_extractors",
                "content_sources",
                "content_fetchers",
                "lifecycle_actions",
            ]

            for plugin_type in expected_types:
                assert plugin_type in results, f"Missing validation for {plugin_type}"

            # Mock plugins should pass validation (no issues)
            for plugin_type, issues in results.items():
                assert len(issues) == 0, (
                    f"Mock {plugin_type} failed validation: {issues}"
                )

        finally:
            if plugin_system.is_running():
                plugin_system.stop()

    def test_system_health_diagnostics(self) -> None:
        """Test the system health diagnostics functionality."""
        test_plugin_manager = create_test_plugin_manager_with_mocks()
        plugin_system = PluginSystem(test_plugin_manager)

        try:
            plugin_system.bootstrap()
            plugin_system.start()

            diagnostics = SystemHealthDiagnostics(plugin_system)
            health_report = diagnostics.run_full_health_check()

            # System should be healthy
            assert health_report["system_running"] is True
            assert health_report["singletons_available"] is True
            assert health_report["configuration_accessible"] is True
            assert health_report["state_storage_functional"] is True
            assert health_report["cache_functional"] is True
            assert health_report["data_storage_functional"] is True
            assert health_report["task_queue_functional"] is True

            # Should have plugin counts
            assert "plugin_counts" in health_report
            counts = health_report["plugin_counts"]
            assert counts["configuration_providers"] > 0
            assert counts["content_extractors"] > 0
            assert counts["content_sources"] > 0
            assert counts["content_fetchers"] > 0
            assert counts["lifecycle_actions"] > 0

            # Should have no errors for healthy system
            assert len(health_report["errors"]) == 0

        finally:
            plugin_system.stop()

    def test_health_diagnostics_with_stopped_system(self) -> None:
        """Test health diagnostics with a stopped system."""
        test_plugin_manager = create_test_plugin_manager_with_mocks()
        plugin_system = PluginSystem(test_plugin_manager)

        # Don't start the system
        plugin_system.bootstrap()

        diagnostics = SystemHealthDiagnostics(plugin_system)
        health_report = diagnostics.run_full_health_check()

        # System should be detected as not running
        assert health_report["system_running"] is False
        assert health_report["singletons_available"] is False

        # Should have error about system not running
        assert len(health_report["errors"]) > 0
        assert any("not running" in error for error in health_report["errors"])

    def test_plugin_validation_with_missing_methods(self) -> None:
        """Test plugin validation detects missing methods."""

        # Create a fake plugin with missing methods
        class IncompletePlugin:
            """A plugin missing required methods."""

            def partial_method(self) -> str:
                return "incomplete"

        test_plugin_manager = create_test_plugin_manager_with_mocks()
        plugin_system = PluginSystem(test_plugin_manager)

        try:
            plugin_system.bootstrap()

            # Add the incomplete plugin to test validation
            plugin_manager = plugin_system.get_plugin_manager()
            incomplete_plugin = IncompletePlugin()

            # Manually add to lifecycle actions to test validation
            plugin_manager._lifecycle_actions = [incomplete_plugin]  # type: ignore[list-item] # noqa: SLF001

            checker = PluginCompatibilityChecker(plugin_system)
            results = checker.check_all_plugins()

            # Should detect missing methods in lifecycle actions
            lifecycle_issues = results["lifecycle_actions"]
            assert len(lifecycle_issues) > 0
            assert any("Missing" in issue for issue in lifecycle_issues)

        finally:
            if plugin_system.is_running():
                plugin_system.stop()

    def test_configuration_provider_validation_with_invalid_yaml(self) -> None:
        """Test configuration provider validation detects invalid YAML."""

        class InvalidYAMLProvider:
            """Configuration provider with invalid YAML."""

            def get_default_configuration(self) -> str:
                return "invalid: yaml: content: [unclosed"

            def get_configuration_id(self) -> str:
                return "invalid_yaml_test"

        test_plugin_manager = create_test_plugin_manager_with_mocks()
        plugin_system = PluginSystem(test_plugin_manager)

        try:
            plugin_system.bootstrap()

            # Add the invalid provider to test validation
            plugin_manager = plugin_system.get_plugin_manager()
            invalid_provider = InvalidYAMLProvider()

            # Manually add to configuration providers to test validation
            plugin_manager._configuration_providers = [invalid_provider]  # noqa: SLF001

            checker = PluginCompatibilityChecker(plugin_system)
            results = checker.check_all_plugins()

            # Should detect invalid YAML
            config_issues = results["configuration_providers"]
            assert len(config_issues) > 0
            assert any("Invalid YAML" in issue for issue in config_issues)

        finally:
            if plugin_system.is_running():
                plugin_system.stop()

    def test_extractor_validation_with_invalid_return_types(self) -> None:
        """Test content extractor validation detects invalid return types."""

        class InvalidExtractor:
            """Content extractor with invalid return types."""

            def can_extract(
                self, url: str, mime_type: str | None = None
            ) -> str:  # Wrong type
                return "not_a_boolean"

            def preferred_mime_types(self) -> str:  # Wrong type
                return "not_a_list"

            async def extract(
                self, host: Any, content: Any, metadata: Any = None
            ) -> None:
                pass

        test_plugin_manager = create_test_plugin_manager_with_mocks()
        plugin_system = PluginSystem(test_plugin_manager)

        try:
            plugin_system.bootstrap()

            # Add the invalid extractor to test validation
            plugin_manager = plugin_system.get_plugin_manager()
            invalid_extractor = InvalidExtractor()

            # Manually add to content extractors to test validation
            plugin_manager._content_extractors = [invalid_extractor]  # type: ignore[list-item] # noqa: SLF001

            checker = PluginCompatibilityChecker(plugin_system)
            results = checker.check_all_plugins()

            # Should detect invalid return types
            extractor_issues = results["content_extractors"]
            assert len(extractor_issues) > 0
            assert any("must return bool" in issue for issue in extractor_issues)
            assert any("must return list" in issue for issue in extractor_issues)

        finally:
            if plugin_system.is_running():
                plugin_system.stop()
