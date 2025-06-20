# ABOUTME: System health monitoring and observability for PAISE2
# ABOUTME: Provides health reporting, performance metrics, and system status

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from paise2.config.models import Configuration
    from paise2.plugins.core.interfaces import (
        CacheManager,
        DataStorage,
        StateStorage,
    )
    from paise2.plugins.core.registry import PluginManager
    from paise2.plugins.core.startup import Singletons
    from paise2.plugins.core.tasks import TaskQueue

logger = logging.getLogger(__name__)


@dataclass
class SystemHealthReport:
    """System health report containing status of all components."""

    status: str = "unknown"
    """Overall system status: healthy, degraded, or unhealthy."""

    timestamp: float = field(default_factory=time.time)
    """Timestamp when the health check was performed."""

    components: dict[str, dict[str, Any]] = field(default_factory=dict)
    """Health status of individual components."""

    metrics: dict[str, Any] = field(default_factory=dict)
    """System performance metrics."""

    errors: list[str] = field(default_factory=list)
    """List of errors encountered during health check."""


class SystemHealthMonitor:
    """System health monitoring and reporting."""

    def __init__(self) -> None:
        """Initialize the health monitor."""
        self.logger = logging.getLogger(__name__)

    def check_system_health(self, singletons: Singletons) -> SystemHealthReport:
        """
        Perform comprehensive system health check.

        Args:
            singletons: System singletons to check

        Returns:
            Health report with component status and metrics
        """
        report = SystemHealthReport()

        try:
            # Check configuration
            self._check_configuration(singletons.configuration, report)

            # Check plugin manager
            self._check_plugin_manager(singletons.plugin_manager, report)

            # Check task queue
            self._check_task_queue(singletons.task_queue, report)

            # Check cache
            self._check_cache(singletons.cache, report)

            # Check state storage
            self._check_state_storage(singletons.state_storage, report)

            # Check data storage
            self._check_data_storage(singletons.data_storage, report)

            # Determine overall status
            report.status = self._determine_overall_status(report)

        except Exception as e:
            self.logger.exception("Error during health check")
            report.status = "unhealthy"
            report.errors.append(f"Health check failed: {e}")

        return report

    def _check_configuration(
        self, configuration: Configuration, report: SystemHealthReport
    ) -> None:
        """Check configuration health."""
        try:
            # Basic configuration validation
            profile = configuration.get("profile", "unknown")

            report.components["configuration"] = {
                "status": "healthy",
                "profile": profile,
                "keys_count": len(getattr(configuration, "_data", {})),
            }

        except Exception as e:
            report.components["configuration"] = {
                "status": "unhealthy",
                "error": str(e),
            }
            report.errors.append(f"Configuration check failed: {e}")

    def _check_plugin_manager(
        self, plugin_manager: PluginManager, report: SystemHealthReport
    ) -> None:
        """Check plugin manager health."""
        try:
            content_sources = len(plugin_manager.get_content_sources())
            content_fetchers = len(plugin_manager.get_content_fetchers())
            content_extractors = len(plugin_manager.get_content_extractors())

            report.components["plugin_manager"] = {
                "status": "healthy",
                "content_sources": content_sources,
                "content_fetchers": content_fetchers,
                "content_extractors": content_extractors,
                "cache_providers": len(plugin_manager.get_cache_providers()),
                "state_providers": len(plugin_manager.get_state_storage_providers()),
                "data_providers": len(plugin_manager.get_data_storage_providers()),
                "task_queue_providers": len(plugin_manager.get_task_queue_providers()),
            }

            report.metrics.update(
                {
                    "total_providers": (
                        content_sources
                        + content_fetchers
                        + content_extractors
                        + len(plugin_manager.get_cache_providers())
                        + len(plugin_manager.get_state_storage_providers())
                        + len(plugin_manager.get_data_storage_providers())
                        + len(plugin_manager.get_task_queue_providers())
                    )
                }
            )

        except Exception as e:
            report.components["plugin_manager"] = {
                "status": "unhealthy",
                "error": str(e),
            }
            report.errors.append(f"Plugin manager check failed: {e}")

    def _check_task_queue(
        self, task_queue: TaskQueue | None, report: SystemHealthReport
    ) -> None:
        """Check task queue health."""
        try:
            if task_queue is None:
                report.components["task_queue"] = {
                    "status": "disabled",
                    "type": "none",
                    "immediate": True,
                }
            else:
                # Check if it's a Huey instance
                queue_type = type(task_queue).__name__
                immediate = getattr(task_queue, "immediate", False)

                report.components["task_queue"] = {
                    "status": "healthy",
                    "type": queue_type,
                    "immediate": immediate,
                }

                # Additional metrics for Huey
                if hasattr(task_queue, "huey"):
                    huey = task_queue.huey
                    report.components["task_queue"]["huey_type"] = type(huey).__name__
                    queue_name = getattr(huey, "name", "unknown")
                    report.components["task_queue"]["queue_name"] = queue_name

        except Exception as e:
            report.components["task_queue"] = {"status": "unhealthy", "error": str(e)}
            report.errors.append(f"Task queue check failed: {e}")

    def _check_cache(self, cache: CacheManager, report: SystemHealthReport) -> None:
        """Check cache health."""
        try:
            cache_type = type(cache).__name__

            report.components["cache"] = {
                "status": "healthy",
                "type": cache_type,
            }

        except Exception as e:
            report.components["cache"] = {"status": "unhealthy", "error": str(e)}
            report.errors.append(f"Cache check failed: {e}")

    def _check_state_storage(
        self, state_storage: StateStorage, report: SystemHealthReport
    ) -> None:
        """Check state storage health."""
        try:
            storage_type = type(state_storage).__name__

            report.components["state_storage"] = {
                "status": "healthy",
                "type": storage_type,
            }

        except Exception as e:
            report.components["state_storage"] = {
                "status": "unhealthy",
                "error": str(e),
            }
            report.errors.append(f"State storage check failed: {e}")

    def _check_data_storage(
        self, data_storage: DataStorage, report: SystemHealthReport
    ) -> None:
        """Check data storage health."""
        try:
            storage_type = type(data_storage).__name__

            report.components["data_storage"] = {
                "status": "healthy",
                "type": storage_type,
            }

        except Exception as e:
            report.components["data_storage"] = {"status": "unhealthy", "error": str(e)}
            report.errors.append(f"Data storage check failed: {e}")

    def _determine_overall_status(self, report: SystemHealthReport) -> str:
        """Determine overall system status based on component health."""
        if report.errors:
            return "unhealthy"

        unhealthy_components = [
            name
            for name, component in report.components.items()
            if component.get("status") == "unhealthy"
        ]

        if unhealthy_components:
            return "unhealthy"

        degraded_components = [
            name
            for name, component in report.components.items()
            if component.get("status") in ("degraded", "disabled")
        ]

        if degraded_components:
            return "degraded"

        return "healthy"

    def format_health_report(
        self, report: SystemHealthReport, format_type: str = "text"
    ) -> str:
        """
        Format health report for display.

        Args:
            report: Health report to format
            format_type: Output format (text or json)

        Returns:
            Formatted health report
        """
        if format_type == "json":
            import json

            return json.dumps(
                {
                    "status": report.status,
                    "timestamp": report.timestamp,
                    "components": report.components,
                    "metrics": report.metrics,
                    "errors": report.errors,
                },
                indent=2,
            )

        # Text format
        timestamp_str = time.strftime(
            "%Y-%m-%d %H:%M:%S", time.localtime(report.timestamp)
        )
        lines = [
            "PAISE2 System Health Report",
            f"Status: {report.status.upper()}",
            f"Timestamp: {timestamp_str}",
            "",
        ]

        if report.errors:
            lines.extend(
                [
                    "ERRORS:",
                    *[f"  - {error}" for error in report.errors],
                    "",
                ]
            )

        lines.append("COMPONENTS:")
        for name, component in report.components.items():
            status = component.get("status", "unknown")
            lines.append(f"  {name}: {status.upper()}")

            for key, value in component.items():
                if key != "status":
                    lines.append(f"    {key}: {value}")

        if report.metrics:
            lines.extend(
                [
                    "",
                    "METRICS:",
                    *[f"  {key}: {value}" for key, value in report.metrics.items()],
                ]
            )

        return "\n".join(lines)
