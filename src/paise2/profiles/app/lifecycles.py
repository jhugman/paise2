# ABOUTME: App profile lifecycle actions for managing content sources
# ABOUTME: Registers lifecycle actions that coordinate system startup and shutdown

from typing import Callable

from paise2.plugins.core.interfaces import LifecycleAction
from paise2.plugins.core.registry import hookimpl
from paise2.profiles.app.content_sources import ContentSourceLifecycleAction


@hookimpl
def register_lifecycle_action(
    register: Callable[[LifecycleAction], None],
) -> None:
    """Register the content source lifecycle action for app profile."""
    register(ContentSourceLifecycleAction())
