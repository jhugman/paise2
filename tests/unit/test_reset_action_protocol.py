# ABOUTME: Unit tests for ResetAction protocol and registration functionality
# ABOUTME: Tests the ResetAction interface, host integration, and plugin registration

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import Mock

if TYPE_CHECKING:
    from paise2.plugins.core.interfaces import Configuration, LifecycleHost


class TestResetActionProtocol:
    """Test the ResetAction protocol definition and implementation."""

    def test_reset_action_protocol_exists(self) -> None:
        """Test that ResetAction protocol is properly defined."""
        from paise2.plugins.core.interfaces import ResetAction

        # Test that protocol can be implemented
        class TestResetAction:
            def hard_reset(
                self, host: LifecycleHost, configuration: Configuration
            ) -> None:
                pass

            def soft_reset(
                self, host: LifecycleHost, configuration: Configuration
            ) -> None:
                pass

        action = TestResetAction()
        assert isinstance(action, ResetAction)

    def test_register_reset_action_hook_spec_exists(self) -> None:
        """Test that the register_reset_action hook specification exists."""
        from paise2.plugins.core.registry import PluginManager

        manager = PluginManager()
        assert hasattr(manager.pm.hook, "register_reset_action")

    def test_reset_action_with_mock_implementations(self) -> None:
        """Test reset actions with mock implementations."""
        from paise2.plugins.core.interfaces import Configuration, LifecycleHost

        # Mock host and configuration
        mock_host = Mock(spec=LifecycleHost)
        mock_config = Mock(spec=Configuration)

        class CacheResetAction:
            def __init__(self) -> None:
                self.hard_reset_called = False
                self.soft_reset_called = False

            def hard_reset(
                self, host: LifecycleHost, configuration: Configuration
            ) -> None:
                self.hard_reset_called = True
                # Would clear all cache

            def soft_reset(
                self, host: LifecycleHost, configuration: Configuration
            ) -> None:
                self.soft_reset_called = True
                # Would clear only expired cache

        cache_action = CacheResetAction()

        # Test hard reset
        cache_action.hard_reset(mock_host, mock_config)
        assert cache_action.hard_reset_called is True

        # Test soft reset
        cache_action.soft_reset(mock_host, mock_config)
        assert cache_action.soft_reset_called is True

    def test_reset_action_registration(self) -> None:
        """Test that reset actions can be registered."""
        from paise2.plugins.core.registry import PluginManager

        class MockResetAction:
            def hard_reset(
                self, host: LifecycleHost, configuration: Configuration
            ) -> None:
                pass

            def soft_reset(
                self, host: LifecycleHost, configuration: Configuration
            ) -> None:
                pass

        manager = PluginManager()
        action = MockResetAction()

        # Register the action
        result = manager.register_reset_action(action)
        assert result is True

        # Verify it was registered
        actions = manager.get_reset_actions()
        assert action in actions

    def test_reset_action_hook_implementation(self) -> None:
        """Test registering reset actions via hook implementation."""
        from paise2.plugins.core.registry import PluginManager, hookimpl

        manager = PluginManager()

        class MockResetAction:
            def hard_reset(
                self, host: LifecycleHost, configuration: Configuration
            ) -> None:
                pass

            def soft_reset(
                self, host: LifecycleHost, configuration: Configuration
            ) -> None:
                pass

        class TestPlugin:
            @hookimpl
            def register_reset_action(self, register: Any) -> None:
                register(MockResetAction())

        # Create a module-like object and attach the plugin
        import types

        mock_module = types.SimpleNamespace()
        mock_module.register_reset_action = TestPlugin().register_reset_action

        # Register the module and load plugins
        manager.pm.register(mock_module)
        manager.load_plugins()

        # Verify the reset action was registered
        actions = manager.get_reset_actions()
        assert len(actions) == 1
        assert isinstance(actions[0], MockResetAction)
