# ABOUTME: Unit tests for the PluginSystem manager class that orchestrates
# ABOUTME: the complete plugin lifecycle from discovery through shutdown.

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from paise2.plugins.core.manager import PluginSystem
from paise2.plugins.core.registry import PluginManager
from paise2.plugins.core.startup import Singletons


class TestPluginSystem:
    """Test the main PluginSystem class that manages complete plugin lifecycle."""

    def test_plugin_system_initialization(self) -> None:
        """Test PluginSystem can be initialized with proper dependencies."""
        plugin_system = PluginSystem()

        assert plugin_system is not None
        assert hasattr(plugin_system, "_startup_manager")
        assert hasattr(plugin_system, "_singletons")
        assert hasattr(plugin_system, "_is_running")

    def test_plugin_system_has_startup_lifecycle_methods(self) -> None:
        """Test PluginSystem provides complete startup lifecycle methods."""
        plugin_system = PluginSystem()

        # Should have all lifecycle methods
        assert hasattr(plugin_system, "bootstrap")
        assert hasattr(plugin_system, "start")
        assert hasattr(plugin_system, "stop")
        assert hasattr(plugin_system, "is_running")

    @patch("paise2.plugins.core.manager.create_development_plugin_manager")
    @patch("paise2.plugins.core.manager.StartupManager")
    def test_plugin_system_bootstrap_creates_startup_manager(
        self, mock_startup_manager_class: Mock, mock_create_plugin_manager: Mock
    ) -> None:
        """Test bootstrap phase creates StartupManager and initializes logging."""
        mock_plugin_manager = Mock(spec=PluginManager)
        mock_create_plugin_manager.return_value = mock_plugin_manager

        mock_startup_manager = Mock()
        mock_startup_manager_class.return_value = mock_startup_manager

        plugin_system = PluginSystem()
        plugin_system.bootstrap()

        # Should create plugin manager and StartupManager
        mock_create_plugin_manager.assert_called_once()
        mock_startup_manager_class.assert_called_once_with(mock_plugin_manager)
        assert plugin_system._startup_manager is mock_startup_manager  # noqa: SLF001

    @patch("paise2.plugins.core.manager.create_development_plugin_manager")
    @patch("paise2.plugins.core.manager.StartupManager")
    @patch("paise2.plugins.core.manager.asyncio.run")
    def test_plugin_system_start_calls_full_startup_sequence(
        self,
        mock_asyncio_run: Mock,
        mock_startup_manager_class: Mock,
        mock_create_plugin_manager: Mock,
    ) -> None:
        """Test start method calls the complete startup sequence."""
        mock_plugin_manager = Mock(spec=PluginManager)
        mock_create_plugin_manager.return_value = mock_plugin_manager

        mock_startup_manager = Mock()
        # Make execute_startup return a mock coroutine
        mock_coroutine = Mock()
        mock_coroutine.__await__ = Mock(return_value=iter([]))
        mock_startup_manager.execute_startup.return_value = mock_coroutine
        mock_startup_manager_class.return_value = mock_startup_manager

        # Mock the singletons returned by startup
        mock_singletons = Mock(spec=Singletons)
        mock_asyncio_run.return_value = mock_singletons

        plugin_system = PluginSystem()
        plugin_system.bootstrap()
        plugin_system.start()

        # Should run complete startup sequence via asyncio.run
        mock_asyncio_run.assert_called_once()
        args, _ = mock_asyncio_run.call_args
        # The first argument should be a coroutine from execute_startup
        assert hasattr(args[0], "__await__")  # Check it's awaitable

        assert plugin_system._singletons is mock_singletons  # noqa: SLF001
        assert plugin_system.is_running() is True

    def test_plugin_system_start_without_bootstrap_raises_error(self) -> None:
        """Test starting without bootstrap raises appropriate error."""
        plugin_system = PluginSystem()

        with pytest.raises(RuntimeError, match="Must call bootstrap.*before start"):
            plugin_system.start()

    @patch("paise2.plugins.core.manager.create_development_plugin_manager")
    @patch("paise2.plugins.core.manager.StartupManager")
    @patch("paise2.plugins.core.manager.asyncio.run")
    def test_plugin_system_stop_cleanup(
        self,
        mock_asyncio_run: Mock,
        mock_startup_manager_class: Mock,
        mock_create_plugin_manager: Mock,
    ) -> None:
        """Test stop method performs proper cleanup."""
        mock_plugin_manager = Mock(spec=PluginManager)
        mock_create_plugin_manager.return_value = mock_plugin_manager

        mock_startup_manager = Mock()
        mock_startup_manager_class.return_value = mock_startup_manager

        mock_singletons = Mock(spec=Singletons)
        mock_asyncio_run.return_value = mock_singletons

        plugin_system = PluginSystem()
        plugin_system.bootstrap()
        plugin_system.start()

        # Should be running before stop
        assert plugin_system.is_running() is True

        plugin_system.stop()

        # Should reset state (graceful shutdown is placeholder for now)
        assert plugin_system.is_running() is False
        assert plugin_system._singletons is None  # noqa: SLF001

    def test_plugin_system_stop_when_not_running(self) -> None:
        """Test stop method when system is not running."""
        plugin_system = PluginSystem()

        # Should not raise error when stopping non-running system
        plugin_system.stop()
        assert plugin_system.is_running() is False

    @patch("paise2.plugins.core.manager.create_development_plugin_manager")
    @patch("paise2.plugins.core.manager.StartupManager")
    @patch("paise2.plugins.core.manager.asyncio.run")
    def test_plugin_system_get_singletons_when_running(
        self,
        mock_asyncio_run: Mock,
        mock_startup_manager_class: Mock,
        mock_create_plugin_manager: Mock,
    ) -> None:
        """Test accessing singletons when system is running."""
        mock_plugin_manager = Mock(spec=PluginManager)
        mock_create_plugin_manager.return_value = mock_plugin_manager

        mock_startup_manager = Mock()
        mock_startup_manager_class.return_value = mock_startup_manager

        mock_singletons = Mock(spec=Singletons)
        mock_asyncio_run.return_value = mock_singletons

        plugin_system = PluginSystem()
        plugin_system.bootstrap()
        plugin_system.start()

        singletons = plugin_system.get_singletons()
        assert singletons is mock_singletons

    def test_plugin_system_get_singletons_when_not_running(self) -> None:
        """Test accessing singletons when system is not running raises error."""
        plugin_system = PluginSystem()

        with pytest.raises(RuntimeError, match="System is not running"):
            plugin_system.get_singletons()

    @patch("paise2.plugins.core.manager.create_development_plugin_manager")
    @patch("paise2.plugins.core.manager.StartupManager")
    @patch("paise2.plugins.core.manager.asyncio.run")
    def test_plugin_system_error_handling_during_startup(
        self,
        mock_asyncio_run: Mock,
        mock_startup_manager_class: Mock,
        mock_create_plugin_manager: Mock,
    ) -> None:
        """Test error handling during startup sequence."""
        mock_plugin_manager = Mock(spec=PluginManager)
        mock_create_plugin_manager.return_value = mock_plugin_manager

        # Create a non-spec mock to avoid async mock creation issues
        mock_startup_manager = Mock()
        mock_startup_manager_class.return_value = mock_startup_manager

        # Simulate startup failure
        mock_asyncio_run.side_effect = Exception("Startup failed")

        plugin_system = PluginSystem()
        plugin_system.bootstrap()

        with pytest.raises(Exception, match="Startup failed"):
            plugin_system.start()

        # Should remain not running after failure
        assert plugin_system.is_running() is False
        assert plugin_system._singletons is None  # noqa: SLF001

    @patch("paise2.plugins.core.manager.create_development_plugin_manager")
    @patch("paise2.plugins.core.manager.StartupManager")
    @patch("paise2.plugins.core.manager.asyncio.run")
    def test_plugin_system_restart_sequence(
        self,
        mock_asyncio_run: Mock,
        mock_startup_manager_class: Mock,
        mock_create_plugin_manager: Mock,
    ) -> None:
        """Test stopping and restarting the plugin system."""
        mock_plugin_manager = Mock(spec=PluginManager)
        mock_create_plugin_manager.return_value = mock_plugin_manager

        mock_startup_manager = Mock()
        mock_startup_manager_class.return_value = mock_startup_manager

        mock_singletons = Mock(spec=Singletons)
        mock_asyncio_run.return_value = mock_singletons

        plugin_system = PluginSystem()
        plugin_system.bootstrap()
        plugin_system.start()

        assert plugin_system.is_running() is True

        plugin_system.stop()
        assert plugin_system.is_running() is False

        # Should be able to start again
        plugin_system.start()
        assert plugin_system.is_running() is True

    @patch("paise2.plugins.core.manager.create_development_plugin_manager")
    @patch("paise2.plugins.core.manager.StartupManager")
    def test_plugin_system_get_plugin_manager(
        self, mock_startup_manager_class: Mock, mock_create_plugin_manager: Mock
    ) -> None:
        """Test accessing the plugin manager from the system."""
        mock_plugin_manager = Mock(spec=PluginManager)
        mock_create_plugin_manager.return_value = mock_plugin_manager

        mock_startup_manager = Mock()
        mock_startup_manager.plugin_manager = mock_plugin_manager
        mock_startup_manager_class.return_value = mock_startup_manager

        plugin_system = PluginSystem()
        plugin_system.bootstrap()

        plugin_manager = plugin_system.get_plugin_manager()
        assert plugin_manager is mock_plugin_manager

    def test_plugin_system_get_plugin_manager_before_bootstrap(self) -> None:
        """Test accessing plugin manager before bootstrap raises error."""
        plugin_system = PluginSystem()

        with pytest.raises(RuntimeError, match="Must call bootstrap.*before accessing"):
            plugin_system.get_plugin_manager()
