# ABOUTME: App profile lifecycle actions for managing content sources
# ABOUTME: Registers lifecycle actions that coordinate system startup and shutdown

from typing import Any, Callable

from paise2.plugins.core.interfaces import LifecycleAction
from paise2.plugins.core.registry import hookimpl
from paise2.profiles.app.content_sources import ContentSourceLifecycleAction


class AppPlugin:
    @hookimpl
    def register_lifecycle_action(
        self,
        register: Callable[[LifecycleAction], None],
    ) -> None:
        """Register the content source lifecycle action for app profile."""
        register(ContentSourceLifecycleAction())


@hookimpl
def register_plugin(register: Callable[[Any], None]) -> None:
    register(AppPlugin())
