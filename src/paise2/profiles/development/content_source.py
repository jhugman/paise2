from typing import Callable

from paise2.plugins.core.interfaces import ContentSource
from paise2.plugins.core.registry import hookimpl
from paise2.plugins.providers.content_sources import DirectoryWatcherContentSource


@hookimpl
def register_content_source(register: Callable[[ContentSource], None]) -> None:
    register(
        DirectoryWatcherContentSource(
            watch_directory="~/Documents", file_extensions=[".txt", ".md"]
        )
    )
