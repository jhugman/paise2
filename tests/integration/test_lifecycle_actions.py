# ABOUTME: Tests for LifecycleAction integration with application startup and shutdown
# ABOUTME: Validates that lifecycle actions are properly called during system phases

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from paise2.plugins.core.interfaces import LifecycleHost


class TestLifecycleActionIntegration:
    """Tests for LifecycleAction integration with the application lifecycle."""

    def test_lifecycle_actions_called_during_startup(self) -> None:
        """Test that lifecycle actions are called during application startup."""
        # Create a test lifecycle action that tracks calls
        startup_calls = []
        shutdown_calls = []

        class TestLifecycleAction:
            async def on_start(self, host: LifecycleHost) -> None:
                startup_calls.append("startup")
                assert host is not None
                assert host.logger is not None
                assert host.configuration is not None

            async def on_stop(self, host: LifecycleHost) -> None:
                shutdown_calls.append("shutdown")
                assert host is not None

        # Create lifecycle action instance
        lifecycle_action = TestLifecycleAction()

        # Create a custom plugin manager and register the lifecycle action
        # before startup
        from tests.fixtures.factory import create_test_plugin_manager_with_mocks

        plugin_manager = create_test_plugin_manager_with_mocks()
        plugin_manager.register_lifecycle_action(lifecycle_action)

        # Create PluginSystem with our custom plugin manager
        from paise2.plugins.core.manager import PluginSystem

        plugin_system = PluginSystem(plugin_manager)

        try:
            plugin_system.bootstrap()
            plugin_system.start()

            # Now lifecycle actions should have been called during startup
            assert len(startup_calls) == 1
            assert startup_calls[0] == "startup"
        finally:
            plugin_system.stop()
            # shutdown_calls should contain ["shutdown"] after stop
            assert len(shutdown_calls) == 1
            assert shutdown_calls[0] == "shutdown"

    def test_lifecycle_actions_called_during_shutdown(self) -> None:
        """Test that lifecycle actions are called during application shutdown."""
        # Create a test lifecycle action that tracks calls
        shutdown_calls = []

        class TestLifecycleAction:
            async def on_start(self, host: LifecycleHost) -> None:
                pass  # Don't need to track start for this test

            async def on_stop(self, host: LifecycleHost) -> None:
                shutdown_calls.append("shutdown")
                assert host is not None

        # Create lifecycle action instance
        lifecycle_action = TestLifecycleAction()

        # Create a custom plugin manager and register the lifecycle action
        # before startup
        from tests.fixtures.factory import create_test_plugin_manager_with_mocks

        plugin_manager = create_test_plugin_manager_with_mocks()
        plugin_manager.register_lifecycle_action(lifecycle_action)

        # Create PluginSystem with our custom plugin manager
        from paise2.plugins.core.manager import PluginSystem

        plugin_system = PluginSystem(plugin_manager)

        try:
            plugin_system.bootstrap()
            plugin_system.start()
        finally:
            plugin_system.stop()
            # shutdown_calls should contain ["shutdown"] after stop
            assert len(shutdown_calls) == 1
            assert shutdown_calls[0] == "shutdown"

    def test_multiple_lifecycle_actions_executed_in_order(self) -> None:
        """Test that multiple lifecycle actions are executed in discovery order."""
        # Create multiple test lifecycle actions that track execution order
        execution_order = []

        class FirstLifecycleAction:
            async def on_start(self, host: LifecycleHost) -> None:
                execution_order.append("first_start")

            async def on_stop(self, host: LifecycleHost) -> None:
                execution_order.append("first_stop")

        class SecondLifecycleAction:
            async def on_start(self, host: LifecycleHost) -> None:
                execution_order.append("second_start")

            async def on_stop(self, host: LifecycleHost) -> None:
                execution_order.append("second_stop")

        # Create lifecycle action instances
        first_action = FirstLifecycleAction()
        second_action = SecondLifecycleAction()

        # Create a custom plugin manager and register the lifecycle actions
        from tests.fixtures.factory import create_test_plugin_manager_with_mocks

        plugin_manager = create_test_plugin_manager_with_mocks()
        plugin_manager.register_lifecycle_action(first_action)
        plugin_manager.register_lifecycle_action(second_action)

        # Create PluginSystem with our custom plugin manager
        from paise2.plugins.core.manager import PluginSystem

        plugin_system = PluginSystem(plugin_manager)

        try:
            plugin_system.bootstrap()
            plugin_system.start()
        finally:
            plugin_system.stop()

        # Should execute start actions in registration order
        # and stop actions in reverse order
        expected_order = [
            "first_start",
            "second_start",
            "second_stop",  # Stop is reversed
            "first_stop",
        ]
        assert execution_order == expected_order

    def test_lifecycle_action_error_handling(self) -> None:
        """Test error handling when lifecycle actions fail."""
        # Create test lifecycle actions, one that fails and one that succeeds
        execution_order = []

        class FailingLifecycleAction:
            async def on_start(self, host: LifecycleHost) -> None:
                execution_order.append("failing_start")
                error_msg = "Intentional test failure"
                raise RuntimeError(error_msg)

            async def on_stop(self, host: LifecycleHost) -> None:
                execution_order.append("failing_stop")
                error_msg = "Intentional test failure"
                raise RuntimeError(error_msg)

        class SuccessfulLifecycleAction:
            async def on_start(self, host: LifecycleHost) -> None:
                execution_order.append("successful_start")

            async def on_stop(self, host: LifecycleHost) -> None:
                execution_order.append("successful_stop")

        # Create lifecycle action instances
        failing_action = FailingLifecycleAction()
        successful_action = SuccessfulLifecycleAction()

        # Create a custom plugin manager and register the lifecycle actions
        from tests.fixtures.factory import create_test_plugin_manager_with_mocks

        plugin_manager = create_test_plugin_manager_with_mocks()
        plugin_manager.register_lifecycle_action(failing_action)
        plugin_manager.register_lifecycle_action(successful_action)

        # Create PluginSystem with our custom plugin manager
        from paise2.plugins.core.manager import PluginSystem

        plugin_system = PluginSystem(plugin_manager)

        try:
            plugin_system.bootstrap()
            # Should not raise exception despite failing lifecycle action
            plugin_system.start()
        finally:
            plugin_system.stop()

        # Both actions should be attempted despite one failing
        expected_calls = [
            "failing_start",
            "successful_start",
            "successful_stop",  # Stop is reversed order
            "failing_stop",
        ]
        assert execution_order == expected_calls

    def test_worker_lifecycle_action_example(self) -> None:
        """Test example worker lifecycle action from the spec."""
        from typing import Any
        from unittest.mock import Mock

        # Test the worker lifecycle action using existing plugin system
        startup_calls = []
        stopped_process = None

        class TestableWorkerLifecycleAction:
            def __init__(self) -> None:
                self.worker_processes: list = []

            async def on_start(self, host: Any) -> None:
                startup_calls.append("worker_startup")
                # Mock starting a worker process
                mock_process = Mock()
                mock_process.pid = 12345
                mock_process.terminate = Mock()
                mock_process.wait = Mock()
                self.worker_processes.append(mock_process)

            async def on_stop(self, host: Any) -> None:
                nonlocal stopped_process
                if self.worker_processes:
                    stopped_process = self.worker_processes[0]
                    for process in self.worker_processes:
                        process.terminate()
                        process.wait()
                    self.worker_processes.clear()

        lifecycle_action = TestableWorkerLifecycleAction()

        # Use existing plugin manager creation pattern
        from tests.fixtures.factory import create_test_plugin_manager_with_mocks

        plugin_manager = create_test_plugin_manager_with_mocks()
        plugin_manager.register_lifecycle_action(lifecycle_action)

        from paise2.plugins.core.manager import PluginSystem

        plugin_system = PluginSystem(plugin_manager)

        try:
            plugin_system.bootstrap()
            plugin_system.start()

            # Should have called startup
            assert "worker_startup" in startup_calls
            assert len(lifecycle_action.worker_processes) == 1
            assert lifecycle_action.worker_processes[0].pid == 12345

        finally:
            plugin_system.stop()

            # Should have called shutdown and cleaned up
            assert len(lifecycle_action.worker_processes) == 0
            if stopped_process:
                stopped_process.terminate.assert_called_once()
                stopped_process.wait.assert_called_once()
