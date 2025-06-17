# ABOUTME: Unit tests for DirectoryWatcherContentSource behavior
# ABOUTME: Tests file discovery and metadata creation functionality

from __future__ import annotations

import tempfile
from pathlib import Path

from paise2.plugins.providers.content_sources import DirectoryWatcherContentSource
from tests.fixtures.mock_plugins import MockLogger


class TestDirectoryWatcherContentSource:
    """Test DirectoryWatcherContentSource behavior."""

    async def test_discover_content_finds_files(self) -> None:
        """Test that DirectoryWatcherContentSource discovers files correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test files
            (temp_path / "file1.txt").write_text("Content 1")
            (temp_path / "file2.txt").write_text("Content 2")

            content_source = DirectoryWatcherContentSource(str(temp_path))

            # Create minimal host for testing
            class MockHost:
                def __init__(self) -> None:
                    self.logger = MockLogger()

            host = MockHost()

            # When: Discovering content
            content_items = await content_source.discover_content(host)  # type: ignore[arg-type]

            # Then: Should find both files
            assert len(content_items) == 2
            urls = [url for url, _ in content_items]
            assert any("file1.txt" in url for url in urls)
            assert any("file2.txt" in url for url in urls)
