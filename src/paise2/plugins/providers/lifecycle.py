# ABOUTME: Lifecycle action providers for managing application startup/shutdown
# ABOUTME: Provides ContentSourceLifecycleAction for managing content source lifecycle

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from paise2.plugins.core.hosts import create_content_source_host_from_singletons

if TYPE_CHECKING:
    from paise2.plugins.core.interfaces import (
        ContentSource,
        ContentSourceHost,
        LifecycleHost,
    )


class ContentSourceLifecycleAction:
    """Lifecycle action that manages starting and stopping content sources."""

    def __init__(self) -> None:
        self._content_source_hosts: list[tuple[ContentSource, ContentSourceHost]] = []

    async def on_start(self, host: LifecycleHost) -> None:
        """Start all registered content sources."""
        # Cast singletons to get access to the plugin manager and other singletons
        from paise2.plugins.core.startup import Singletons

        singletons = host.singletons
        if not isinstance(singletons, Singletons):
            host.logger.error("ContentSourceLifecycleAction requires Singletons access")
            return

        # Access the plugin manager
        plugin_manager = singletons.plugin_manager

        content_sources = plugin_manager.get_content_sources()

        if not content_sources:
            host.logger.debug("No content sources registered")
            return

        # Check if task queue is available
        task_queue = singletons.task_queue
        if task_queue is None:
            host.logger.error("Task queue not available for content source startup")
            return

        host.logger.info("Starting %d content sources", len(content_sources))

        # Create hosts for each content source and start them
        start_tasks = []

        for source in content_sources:
            # Create a specialized host for this content source
            source_host = create_content_source_host_from_singletons(
                singletons=singletons,
                plugin_module_name=source.__class__.__module__,
            )

            # Store the pairing for later shutdown
            self._content_source_hosts.append((source, source_host))

            # Create start task
            start_task = self._start_source_with_error_handling(
                source, source_host, host
            )
            start_tasks.append(start_task)

        # Start all sources in parallel
        if start_tasks:
            await asyncio.gather(*start_tasks, return_exceptions=True)

        host.logger.info("Content source startup complete")

    async def on_stop(self, host: LifecycleHost) -> None:
        """Stop all content sources in reverse order."""
        if not self._content_source_hosts:
            host.logger.debug("No content sources to stop")
            return

        host.logger.info("Stopping %d content sources", len(self._content_source_hosts))

        # Create stop tasks in reverse order
        stop_tasks = []

        for source, source_host in reversed(self._content_source_hosts):
            stop_task = self._stop_source_with_error_handling(source, source_host, host)
            stop_tasks.append(stop_task)

        # Stop all sources in parallel
        if stop_tasks:
            await asyncio.gather(*stop_tasks, return_exceptions=True)

        # Clear the hosts list
        self._content_source_hosts.clear()

        host.logger.info("Content source shutdown complete")

    async def _start_source_with_error_handling(
        self,
        source: ContentSource,
        source_host: ContentSourceHost,
        lifecycle_host: LifecycleHost,
    ) -> None:
        """Start a single content source with error handling."""
        source_name = source.__class__.__name__
        try:
            lifecycle_host.logger.debug("Starting content source: %s", source_name)
            await source.start_source(source_host)
            lifecycle_host.logger.debug(
                "Content source started successfully: %s", source_name
            )
        except Exception:
            lifecycle_host.logger.exception(
                "Failed to start content source: %s", source_name
            )
            # Continue with other sources rather than failing completely

    async def _stop_source_with_error_handling(
        self,
        source: ContentSource,
        source_host: ContentSourceHost,
        lifecycle_host: LifecycleHost,
    ) -> None:
        """Stop a single content source with error handling."""
        source_name = source.__class__.__name__
        try:
            lifecycle_host.logger.debug("Stopping content source: %s", source_name)
            await source.stop_source(source_host)
            lifecycle_host.logger.debug(
                "Content source stopped successfully: %s", source_name
            )
        except Exception:
            lifecycle_host.logger.exception(
                "Failed to stop content source: %s", source_name
            )
            # Continue with other sources rather than failing completely
