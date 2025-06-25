# ABOUTME: Test for the content source lifecycle action in the app profile
# ABOUTME: Verifies that content sources are started and stopped during app lifecycle

from typing import Any

import pytest

from tests.fixtures.factory import create_test_plugin_manager_with_mocks


class TestContentSourceLifecycleAction:
    """Test ContentSourceLifecycleAction integration."""

    @pytest.mark.asyncio
    async def test_content_source_lifecycle_integration(self) -> None:
        """Test that content sources are started and stopped during lifecycle."""
        # Create a plugin manager with mock content sources
        plugin_manager = create_test_plugin_manager_with_mocks()

        # Also register our lifecycle action
        from paise2.profiles.app.content_sources import ContentSourceLifecycleAction

        lifecycle_action = ContentSourceLifecycleAction()
        plugin_manager.register_lifecycle_action(lifecycle_action)

        # Create and start the plugin system
        from paise2.plugins.core.manager import PluginSystem

        plugin_system = PluginSystem(plugin_manager)

        try:
            plugin_system.bootstrap()
            await plugin_system.start_async()

            # Verify system is running
            assert plugin_system.is_running()
            singletons = plugin_system.get_singletons()
            assert singletons is not None

            # Verify content sources are available
            content_sources = plugin_manager.get_content_sources()
            assert len(content_sources) > 0

        finally:
            # Stop the system
            await plugin_system.stop_async()

            # System should stop cleanly
            assert not plugin_system.is_running()

    @pytest.mark.asyncio
    async def test_content_source_lifecycle_error_handling(self) -> None:
        """Test that errors in individual content sources don't stop others."""
        # Create a plugin manager
        plugin_manager = create_test_plugin_manager_with_mocks()

        # Create a problematic content source that raises exceptions
        class ProblematicContentSource:
            async def start_source(self, host: Any) -> None:
                error_msg = "Simulated startup error"
                raise RuntimeError(error_msg)

            async def stop_source(self, host: Any) -> None:
                error_msg = "Simulated shutdown error"
                raise RuntimeError(error_msg)

        # Register the problematic source along with good ones
        plugin_manager.register_content_source(ProblematicContentSource())

        # Register our lifecycle action
        from paise2.profiles.app.content_sources import ContentSourceLifecycleAction

        lifecycle_action = ContentSourceLifecycleAction()
        plugin_manager.register_lifecycle_action(lifecycle_action)

        # Create and start the plugin system
        from paise2.plugins.core.manager import PluginSystem

        plugin_system = PluginSystem(plugin_manager)

        try:
            plugin_system.bootstrap()
            await plugin_system.start_async()

            # System should still be running despite the error
            assert plugin_system.is_running()

            # Should have content sources including the problematic one
            content_sources = plugin_manager.get_content_sources()
            assert len(content_sources) > 1  # Original mocks + problematic one

        finally:
            # Stop the system - should handle errors gracefully
            await plugin_system.stop_async()

            # Should still clean up properly
            assert not plugin_system.is_running()
