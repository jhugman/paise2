# ABOUTME: Tests for system health monitoring and observability
# ABOUTME: Validates health reporting for all system components

from __future__ import annotations

import pytest

from paise2.monitoring import SystemHealthMonitor
from paise2.plugins.core.manager import PluginSystem
from tests.fixtures import create_test_plugin_manager_with_mocks


class TestSystemHealthMonitoring:
    """Tests for system health monitoring capabilities."""

    @pytest.mark.asyncio
    async def test_system_health_monitoring_basic(self) -> None:
        """Test basic system health monitoring functionality."""
        plugin_manager = create_test_plugin_manager_with_mocks()
        plugin_system = PluginSystem(plugin_manager)

        try:
            plugin_system.bootstrap()
            await plugin_system.start_async()
            singletons = plugin_system.get_singletons()

            # Create health monitor and check system health
            health_monitor = SystemHealthMonitor()
            health_report = health_monitor.check_system_health(singletons)

            # Verify overall health status
            assert health_report.status in ["healthy", "degraded", "unhealthy"]
            assert health_report.timestamp > 0

            # Verify all major components are checked
            expected_components = [
                "configuration",
                "plugin_manager",
                "task_queue",
                "cache",
                "state_storage",
                "data_storage",
            ]

            for component in expected_components:
                assert component in health_report.components
                assert "status" in health_report.components[component]

            # Verify plugin manager metrics
            plugin_manager_info = health_report.components["plugin_manager"]
            assert "content_sources" in plugin_manager_info
            assert "content_fetchers" in plugin_manager_info
            assert "content_extractors" in plugin_manager_info
            assert plugin_manager_info["content_sources"] >= 0
            assert plugin_manager_info["content_fetchers"] >= 0
            assert plugin_manager_info["content_extractors"] >= 0

            # Verify metrics are collected
            assert "total_providers" in health_report.metrics
            assert health_report.metrics["total_providers"] >= 0

        finally:
            await plugin_system.stop_async()

    @pytest.mark.asyncio
    async def test_health_report_formatting(self) -> None:
        """Test health report formatting in different formats."""
        plugin_manager = create_test_plugin_manager_with_mocks()
        plugin_system = PluginSystem(plugin_manager)

        try:
            plugin_system.bootstrap()
            await plugin_system.start_async()
            singletons = plugin_system.get_singletons()

            health_monitor = SystemHealthMonitor()
            health_report = health_monitor.check_system_health(singletons)

            # Test text format
            text_report = health_monitor.format_health_report(health_report, "text")
            assert "PAISE2 System Health Report" in text_report
            assert "Status:" in text_report
            assert "COMPONENTS:" in text_report

            # Test JSON format
            json_report = health_monitor.format_health_report(health_report, "json")
            assert '"status":' in json_report
            assert '"components":' in json_report
            assert '"timestamp":' in json_report

            # Verify JSON is valid
            import json

            parsed_json = json.loads(json_report)
            assert "status" in parsed_json
            assert "components" in parsed_json
            assert "timestamp" in parsed_json

        finally:
            await plugin_system.stop_async()

    @pytest.mark.asyncio
    async def test_task_queue_health_monitoring(self) -> None:
        """Test task queue specific health monitoring."""
        plugin_manager = create_test_plugin_manager_with_mocks()
        plugin_system = PluginSystem(plugin_manager)

        try:
            plugin_system.bootstrap()
            await plugin_system.start_async()
            singletons = plugin_system.get_singletons()

            health_monitor = SystemHealthMonitor()
            health_report = health_monitor.check_system_health(singletons)

            # Check task queue status
            task_queue_info = health_report.components["task_queue"]

            if singletons.task_queue is None:
                # Test profile uses no task queue
                assert task_queue_info["status"] == "disabled"
                assert task_queue_info["type"] == "none"
            else:
                # Task queue is available
                assert task_queue_info["status"] in ["healthy", "degraded"]
                assert "type" in task_queue_info
                assert "immediate" in task_queue_info

        finally:
            await plugin_system.stop_async()
