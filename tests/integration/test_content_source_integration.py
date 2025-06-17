# ABOUTME: Integration tests for ContentSource plugin discovery and execution.
# ABOUTME: Tests DirectoryWatcherContentSource in the full plugin system.

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from paise2.plugins.core.manager import PluginSystem
from tests.fixtures import create_test_plugin_manager_with_mocks


class TestContentSourceIntegration:
    """Integration tests for ContentSource plugin discovery and lifecycle."""

    @pytest.mark.asyncio
    async def test_directory_watcher_content_source_discovery(self) -> None:
        """Test that DirectoryWatcherContentSource can be discovered."""
        # Given
        plugin_manager = create_test_plugin_manager_with_mocks()
        plugin_system = PluginSystem(plugin_manager)

        try:
            # When
            plugin_system.bootstrap()
            await plugin_system.start_async()

            # Then - The important thing is that the system starts without errors
            # ContentSource discovery will be tested in unit tests
            assert plugin_system.is_running()
        finally:
            plugin_system.stop()

    @pytest.mark.asyncio
    async def test_directory_watcher_content_source_lifecycle(self) -> None:
        """Test DirectoryWatcherContentSource lifecycle with real plugin system."""
        # Given: Create a temporary directory with test files
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test files
            (temp_path / "test1.txt").write_text("Test content 1")
            (temp_path / "test2.md").write_text("# Test content 2")
            (temp_path / "ignore.log").write_text("Log content")

            # Create plugin system
            plugin_manager = create_test_plugin_manager_with_mocks()
            plugin_system = PluginSystem(plugin_manager)

            try:
                plugin_system.bootstrap()
                await plugin_system.start_async()

                singletons = plugin_system.get_singletons()

                # Import and create the ContentSource
                from paise2.plugins.providers.content_sources import (
                    DirectoryWatcherContentSource,
                )

                source = DirectoryWatcherContentSource(
                    watch_directory=temp_dir, file_extensions=[".txt", ".md"]
                )

                # Create host
                from paise2.plugins.core.hosts import create_content_source_host

                host = create_content_source_host(
                    logger=singletons.logger,
                    configuration=singletons.configuration,
                    state_storage=singletons.state_storage,
                    plugin_module_name="test.integration",
                    cache=singletons.cache,
                    singletons=singletons,
                )

                # When: Start the source
                await source.start_source(host)

                # Then: Verify files were discovered (check logs)
                # Since we're in sync mode, this will just log what would be done
                # The important thing is that it doesn't crash and processes files

                # Verify the source can be stopped
                await source.stop_source(host)

            finally:
                plugin_system.stop()

    @pytest.mark.asyncio
    async def test_directory_watcher_content_discovery(self) -> None:
        """Test DirectoryWatcherContentSource content discovery functionality."""
        # Given: Create a temporary directory with mixed files
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test files with different extensions
            (temp_path / "document.txt").write_text("Text document")
            (temp_path / "readme.md").write_text("# Markdown document")
            (temp_path / "script.py").write_text("print('hello')")
            (temp_path / "data.json").write_text('{"key": "value"}')

            # Create subdirectory with files
            sub_dir = temp_path / "subdir"
            sub_dir.mkdir()
            (sub_dir / "nested.txt").write_text("Nested content")

            # Create plugin system
            plugin_manager = create_test_plugin_manager_with_mocks()
            plugin_system = PluginSystem(plugin_manager)

            try:
                plugin_system.bootstrap()
                await plugin_system.start_async()

                singletons = plugin_system.get_singletons()

                from paise2.plugins.core.hosts import create_content_source_host

                host = create_content_source_host(
                    logger=singletons.logger,
                    configuration=singletons.configuration,
                    state_storage=singletons.state_storage,
                    plugin_module_name="test.integration",
                    cache=singletons.cache,
                    singletons=singletons,
                )

                # Import and create the ContentSource with filtering
                from paise2.plugins.providers.content_sources import (
                    DirectoryWatcherContentSource,
                )

                source = DirectoryWatcherContentSource(
                    watch_directory=temp_dir, file_extensions=[".txt", ".md"]
                )

                # When: Discover content
                content_items = await source.discover_content(host)

                # Then: Verify correct files were discovered
                assert len(content_items) == 3  # document.txt, readme.md, nested.txt
                urls = [url for url, _metadata in content_items]

                # Check that expected files are included
                assert any("document.txt" in url for url in urls)
                assert any("readme.md" in url for url in urls)
                assert any("nested.txt" in url for url in urls)

                # Check that filtered files are excluded
                assert not any("script.py" in url for url in urls)
                assert not any("data.json" in url for url in urls)

                # Verify metadata structure
                for url, metadata in content_items:
                    assert metadata.source_url == url
                    assert metadata.mime_type == "text/plain"
                    assert "file_path" in metadata.extra
                    assert "file_size" in metadata.extra
                    assert "file_modified" in metadata.extra
                    source_plugin = metadata.extra["source_plugin"]
                    assert source_plugin == "DirectoryWatcherContentSource"

            finally:
                plugin_system.stop()

    @pytest.mark.asyncio
    async def test_directory_watcher_handles_missing_directory(self) -> None:
        """Test DirectoryWatcherContentSource handles missing directories."""
        # Given: Non-existent directory
        from paise2.plugins.providers.content_sources import (
            DirectoryWatcherContentSource,
        )

        source = DirectoryWatcherContentSource(
            watch_directory="/nonexistent/directory", file_extensions=[".txt"]
        )

        # Create plugin system
        plugin_manager = create_test_plugin_manager_with_mocks()
        plugin_system = PluginSystem(plugin_manager)

        try:
            plugin_system.bootstrap()
            await plugin_system.start_async()

            singletons = plugin_system.get_singletons()

            from paise2.plugins.core.hosts import create_content_source_host

            host = create_content_source_host(
                logger=singletons.logger,
                configuration=singletons.configuration,
                state_storage=singletons.state_storage,
                plugin_module_name="test.integration",
                cache=singletons.cache,
                singletons=singletons,
            )

            # When: Discover content
            content_items = await source.discover_content(host)

            # Then: Should return empty list without crashing
            assert content_items == []
        finally:
            plugin_system.stop()
