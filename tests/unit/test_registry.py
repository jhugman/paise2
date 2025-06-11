# ABOUTME: Unit tests for the plugin registration system
# ABOUTME: Testing plugin discovery, registration, validation, and error handling


from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import Mock, patch

import paise2
import paise2.profiles
import paise2.profiles.test
from paise2.plugins.core.interfaces import (
    ContentExtractor,
    ContentExtractorHost,
)
from tests.fixtures import MockConfigurationProvider
from tests.fixtures.mock_plugins import MockContentExtractor

if TYPE_CHECKING:
    from paise2.models import Metadata


class TestPluginManager:
    """Test the core PluginManager class."""

    def test_plugin_manager_creation(self) -> None:
        """Test that PluginManager can be created with proper initialization."""
        # This will fail until we implement the registry
        from paise2.plugins.core.registry import PluginManager

        manager = PluginManager()
        assert manager is not None
        assert hasattr(manager, "pm")  # Should wrap pluggy.PluginManager

    def test_plugin_manager_has_hook_specs(self) -> None:
        """Test that PluginManager defines all required hook specifications."""
        from paise2.plugins.core.registry import PluginManager

        manager = PluginManager()

        # Check that hook specifications exist for all extension points
        expected_hooks = [
            "register_configuration_provider",
            "register_content_extractor",
            "register_content_source",
            "register_content_fetcher",
            "register_lifecycle_action",
            "register_data_storage_provider",
            "register_job_queue_provider",
            "register_state_storage_provider",
            "register_cache_provider",
        ]

        for hook_name in expected_hooks:
            assert hasattr(manager.pm.hook, hook_name), f"Missing hook: {hook_name}"


class TestPluginDiscovery:
    """Test plugin discovery functionality."""

    def test_internal_plugin_discovery(self) -> None:
        """Test discovery of internal plugins with @hookimpl decorators."""
        from paise2.plugins.core.registry import PluginManager

        manager = PluginManager()

        # Test that internal plugin discovery works
        # This should scan the paise2 codebase for @hookimpl functions
        internal_plugins = manager.discover_internal_plugins()

        # Should return a list (even if empty initially)
        assert isinstance(internal_plugins, list)

    def test_external_plugin_discovery(self) -> None:
        """Test discovery of external plugins via setuptools entry points."""
        from paise2.plugins.core.registry import PluginManager

        manager = PluginManager()

        # Test external plugin discovery (should not fail even if no external plugins)
        manager.discover_external_plugins()

        # Should complete without error
        assert True

    def test_plugin_discovery_error_handling(self) -> None:
        """Test that plugin discovery handles errors gracefully."""
        from paise2.plugins.core.registry import PluginManager

        manager = PluginManager()

        # Test that discovery continues even if some plugins fail to load
        with patch(
            "importlib.import_module", side_effect=ImportError("Mock import error")
        ):
            plugins = manager.discover_internal_plugins()
            # Should not raise, should return empty list or log error
            assert isinstance(plugins, list)


class TestPluginRegistration:
    """Test plugin registration functionality."""

    def test_register_configuration_provider(self) -> None:
        """Test registration of ConfigurationProvider plugins."""
        from paise2.plugins.core.registry import PluginManager

        manager = PluginManager()

        # Test registration
        provider = MockConfigurationProvider()
        manager.register_configuration_provider(provider)

        # Verify it was registered
        providers = manager.get_configuration_providers()
        assert len(providers) >= 1
        assert any(isinstance(p, MockConfigurationProvider) for p in providers)

    def test_register_content_extractor(self) -> None:
        """Test registration of ContentExtractor plugins."""
        from paise2.plugins.core.registry import PluginManager

        manager = PluginManager()

        # Test registration
        extractor = MockContentExtractor()
        manager.register_content_extractor(extractor)

        # Verify it was registered
        extractors = manager.get_content_extractors()
        assert len(extractors) == 1
        assert any(isinstance(e, MockContentExtractor) for e in extractors)

    def test_multiple_registrations_same_type(self) -> None:
        """Test that multiple plugins of the same type can be registered."""
        from paise2.plugins.core.registry import PluginManager

        manager = PluginManager()

        # Register both
        manager.register_content_extractor(MockContentExtractor())
        manager.register_content_extractor(MockContentExtractor())

        # Verify both were registered
        extractors = manager.get_content_extractors()
        assert len(extractors) == 2


class TestPluginValidation:
    """Test plugin validation functionality."""

    def test_valid_plugin_passes_validation(self) -> None:
        """Test that valid plugins pass validation."""
        from paise2.plugins.core.registry import PluginManager

        manager = PluginManager()

        # Create a valid content extractor
        class ValidExtractor:
            def can_extract(self, url: str, mime_type: str | None = None) -> bool:
                return True

            def preferred_mime_types(self) -> list[str]:
                return ["text/plain"]

            async def extract(
                self,
                host: ContentExtractorHost,
                content: bytes | str,
                metadata: Metadata | None = None,
            ) -> None:
                pass

        extractor = ValidExtractor()

        # Should not raise any validation errors
        is_valid = manager.validate_plugin(extractor, ContentExtractor)
        assert is_valid is True

    def test_invalid_plugin_fails_validation(self) -> None:
        """Test that invalid plugins fail validation."""
        from paise2.plugins.core.registry import PluginManager

        manager = PluginManager()

        # Create an invalid content extractor (missing methods)
        class InvalidExtractor:
            def can_extract(self, url: str, mime_type: str | None = None) -> bool:
                return True

            # Missing preferred_mime_types and extract methods

        extractor = InvalidExtractor()

        # Should fail validation
        is_valid = manager.validate_plugin(extractor, ContentExtractor)
        assert is_valid is False

    def test_validation_with_wrong_signature(self) -> None:
        """Test validation fails for methods with wrong signatures."""
        from paise2.plugins.core.registry import PluginManager

        manager = PluginManager()

        # Create an extractor with wrong method signature
        class WrongSignatureExtractor:
            def can_extract(self, wrong_param: str) -> bool:  # Wrong signature
                return True

            def preferred_mime_types(self) -> list[str]:
                return ["text/plain"]

            async def extract(
                self,
                host: ContentExtractorHost,
                content: bytes | str,
                metadata: Metadata | None = None,
            ) -> None:
                pass

        extractor = WrongSignatureExtractor()

        # Should fail validation due to wrong signature
        is_valid = manager.validate_plugin(extractor, ContentExtractor)
        assert is_valid is False


class TestPluginErrorHandling:
    """Test error handling during plugin operations."""

    def test_registration_error_handling(self) -> None:
        """Test that registration errors are handled gracefully."""
        from paise2.plugins.core.registry import PluginManager

        manager = PluginManager()

        # Try to register None (should handle gracefully)
        result = manager.register_content_extractor(None)  # type: ignore[arg-type]
        assert result is False  # Should return False for failed registration

    def test_discovery_with_broken_module(self) -> None:
        """Test discovery continues even with broken modules."""
        from paise2.plugins.core.registry import PluginManager

        manager = PluginManager()

        # Mock a broken module that raises during import
        with patch(
            "paise2.plugins.core.registry.importlib.import_module"
        ) as mock_import:
            mock_import.side_effect = [ImportError("Broken module"), Mock()]

            # Discovery should continue and not raise
            plugins = manager.discover_internal_plugins()
            assert isinstance(plugins, list)

    def test_plugin_loading_error_recovery(self) -> None:
        """Test that the system recovers from plugin loading errors."""
        from paise2.plugins.core.registry import PluginManager

        manager = PluginManager()

        # Test that we can continue operations even after a failed plugin load
        manager.register_content_extractor(None)  # type: ignore[arg-type]

        # But valid registrations should still work
        class ValidExtractor:
            def can_extract(self, url: str, mime_type: str | None = None) -> bool:
                return True

            def preferred_mime_types(self) -> list[str]:
                return ["text/plain"]

            async def extract(
                self,
                host: ContentExtractorHost,
                content: bytes | str,
                metadata: Metadata | None = None,
            ) -> None:
                pass

        result = manager.register_content_extractor(ValidExtractor())
        assert result is True


class TestLoadOrdering:
    """Test plugin load ordering functionality."""

    def test_discovery_order_preserved(self) -> None:
        """Test that plugins are loaded in discovery order."""
        from paise2.plugins.core.registry import PluginManager

        manager = PluginManager()

        # Create multiple test plugins and register in order
        class Plugin1:
            def can_extract(self, url: str, mime_type: str | None = None) -> bool:
                return True

            def preferred_mime_types(self) -> list[str]:
                return ["type1"]

            async def extract(
                self,
                host: ContentExtractorHost,
                content: bytes | str,
                metadata: Metadata | None = None,
            ) -> None:
                pass

        class Plugin2:
            def can_extract(self, url: str, mime_type: str | None = None) -> bool:
                return True

            def preferred_mime_types(self) -> list[str]:
                return ["type2"]

            async def extract(
                self,
                host: ContentExtractorHost,
                content: bytes | str,
                metadata: Metadata | None = None,
            ) -> None:
                pass

        # Register in specific order
        manager.register_content_extractor(Plugin1())
        manager.register_content_extractor(Plugin2())

        # Get plugins and verify order is preserved
        extractors = manager.get_content_extractors()
        assert len(extractors) >= 2

        # First registered should be first in list (discovery order)
        plugin_types = [e.preferred_mime_types()[0] for e in extractors[-2:]]
        assert plugin_types == ["type1", "type2"]


class TestLogging:
    """Test logging during plugin operations."""

    def test_plugin_discovery_logging(self) -> None:
        """Test that plugin discovery events are logged."""
        from paise2.plugins.core.registry import PluginManager

        manager = PluginManager(profile=paise2.profiles.test.__file__)

        # Test that discovery logs information (we'll check logger was called)
        with patch("paise2.plugins.core.registry.logger") as mock_logger:
            manager.discover_internal_plugins()

            # Should have logged discovery information
            assert mock_logger.info.called or mock_logger.debug.called

    def test_plugin_registration_logging(self) -> None:
        """Test that plugin registration is logged."""
        from paise2.plugins.core.registry import PluginManager

        manager = PluginManager()

        class TestExtractor:
            def can_extract(self, url: str, mime_type: str | None = None) -> bool:
                return True

            def preferred_mime_types(self) -> list[str]:
                return ["text/plain"]

            async def extract(
                self,
                host: ContentExtractorHost,
                content: bytes | str,
                metadata: Metadata | None = None,
            ) -> None:
                pass

        with patch("paise2.plugins.core.registry.logger") as mock_logger:
            manager.register_content_extractor(TestExtractor())

            # Should have logged registration
            assert mock_logger.info.called or mock_logger.debug.called

    def test_error_logging(self) -> None:
        """Test that errors during plugin operations are logged."""
        from paise2.plugins.core.registry import PluginManager

        manager = PluginManager()

        with patch("paise2.plugins.core.registry.logger") as mock_logger:
            # Try to register invalid plugin
            manager.register_content_extractor(None)  # type: ignore[arg-type]

            # Should have logged error
            assert mock_logger.error.called or mock_logger.warning.called
