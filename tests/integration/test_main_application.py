# ABOUTME: Integration tests for the main application entry point with system lifecycle
# ABOUTME: Tests application startup, shutdown, configuration, and full integration

from __future__ import annotations

import pytest

from paise2.main import Application


class TestMainApplication:
    """Integration tests for the main application entry point."""

    def test_application_creation_with_default_profile(self) -> None:
        """Test that Application can be created with default test profile."""
        app = Application()

        assert app is not None
        assert not app.is_running()

    def test_application_creation_with_explicit_profile(self) -> None:
        """Test that Application can be created with explicit profile."""
        app = Application(profile="test")

        assert app is not None
        assert not app.is_running()

    def test_application_startup_and_shutdown_cycle(self) -> None:
        """Test complete application startup and shutdown cycle."""
        app = Application(profile="test")

        # Should start successfully
        app.start()
        assert app.is_running()

        # Should shutdown gracefully
        app.stop()
        assert not app.is_running()

    def test_application_restart_functionality(self) -> None:
        """Test that application can be restarted after shutdown."""
        app = Application(profile="test")

        # First cycle
        app.start()
        assert app.is_running()
        app.stop()
        assert not app.is_running()

        # Second cycle - should work again
        app.start()
        assert app.is_running()
        app.stop()
        assert not app.is_running()

    def test_application_provides_access_to_singletons(self) -> None:
        """Test that running application provides access to system singletons."""
        app = Application(profile="test")
        app.start()

        try:
            singletons = app.get_singletons()

            # Should have all required singletons
            assert singletons.logger is not None
            assert singletons.configuration is not None
            assert singletons.state_storage is not None
            assert singletons.cache is not None
            assert singletons.data_storage is not None
            assert singletons.plugin_manager is not None
            # task_queue may be None for test profile (synchronous execution)
            assert hasattr(singletons, "task_queue")
        finally:
            app.stop()

    def test_application_with_user_configuration_override(self) -> None:
        """Test that application accepts user configuration overrides."""
        user_config = {
            "test_setting": "test_value",
            "application": {"name": "test_app"},
        }

        app = Application(profile="test", user_config=user_config)
        app.start()

        try:
            singletons = app.get_singletons()
            config = singletons.configuration

            # Should be able to access user configuration
            assert config.get("test_setting") == "test_value"
            assert config.get("application.name") == "test_app"
        finally:
            app.stop()

    def test_application_error_handling_during_startup(self) -> None:
        """Test that application handles startup errors gracefully."""
        # Test with an invalid profile that should cause startup failure

        # This should raise an error since the profile doesn't exist
        with pytest.raises(ValueError, match="Unknown profile"):
            _ = Application(profile="invalid_profile_that_does_not_exist")

    def test_application_lifecycle_with_context_manager(self) -> None:
        """Test that Application can be used as a context manager."""
        with Application(profile="test") as app:
            assert app.is_running()

            singletons = app.get_singletons()
            assert singletons is not None

        # Should be stopped after context exit
        assert not app.is_running()
