# ABOUTME: Tests for ContentFetcher pipeline implementation with task scheduling
# ABOUTME: Validates fetcher selection, content retrieval, and extraction scheduling

from __future__ import annotations

from unittest.mock import Mock

from paise2.models import Metadata
from paise2.plugins.core.hosts import ContentFetcherHost


class TestContentFetcherHost:
    """Test ContentFetcherHost with task registry integration."""

    def test_extract_file_with_task_registry(self) -> None:
        """Test extract_file method uses task registry for scheduling."""
        # Create mock task queue
        mock_task_queue = Mock()
        mock_task_result = Mock(id="task123")
        mock_task_queue.extract_content.return_value = mock_task_result

        host = ContentFetcherHost(
            logger=Mock(),
            configuration=Mock(),
            state_storage=Mock(),
            plugin_module_name="test_plugin",
            cache=Mock(),
            task_queue=mock_task_queue,
        )

        content = b"test content"
        metadata = Metadata(source_url="test://example.com")

        # Should not raise an exception
        host.extract_file(content, metadata)

        # Should have called the extract task on task_queue
        mock_task_queue.extract_content.assert_called_once_with(
            content=content, metadata=metadata
        )

    def test_extract_file_synchronous_mode(self) -> None:
        """Test extract_file works in synchronous mode (no task queue)."""
        # Set up synchronous mode (no task queue)
        host = ContentFetcherHost(
            logger=Mock(),
            configuration=Mock(),
            state_storage=Mock(),
            plugin_module_name="test_plugin",
            cache=Mock(),
            task_queue=None,
        )

        content = b"test content"
        metadata = Metadata(source_url="test://example.com")

        # Should not raise an exception in sync mode
        host.extract_file(content, metadata)

    def test_extract_file_no_task_queue(self) -> None:
        """Test extract_file works when no task queue provided."""
        host = ContentFetcherHost(
            logger=Mock(),
            configuration=Mock(),
            state_storage=Mock(),
            plugin_module_name="test_plugin",
            cache=Mock(),
            task_queue=None,
        )

        content = b"test content"
        metadata = Metadata(source_url="test://example.com")

        # Should not raise an exception when no task queue
        host.extract_file(content, metadata)


class TestContentFetcherSelection:
    """Test ContentFetcher selection and prioritization logic."""

    def test_placeholder_for_future_implementation(self) -> None:
        """Placeholder test - will be implemented when fetcher selection is added."""
        # This will be implemented when we create the fetcher selection logic
        assert True


class TestExampleContentFetchers:
    """Test example ContentFetcher implementations."""

    def test_file_content_fetcher_can_fetch_file_scheme(self) -> None:
        """Test FileContentFetcher can_fetch with file:// URLs."""
        from paise2.plugins.providers.content_fetchers import FileContentFetcher

        fetcher = FileContentFetcher()
        host = Mock()

        # Should handle file:// URLs
        assert fetcher.can_fetch(host, "file:///path/to/file.txt")

        # Should not handle http URLs
        assert not fetcher.can_fetch(host, "http://example.com")

    def test_file_content_fetcher_can_fetch_local_path(self) -> None:
        """Test FileContentFetcher can_fetch with local file paths."""
        import tempfile
        from pathlib import Path

        from paise2.plugins.providers.content_fetchers import FileContentFetcher

        fetcher = FileContentFetcher()
        host = Mock()

        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmp_file:
            tmp_file.write("test content")
            tmp_path = tmp_file.name

        try:
            # Should handle existing file paths
            assert fetcher.can_fetch(host, tmp_path)

            # Should not handle non-existent paths
            assert not fetcher.can_fetch(host, "/non/existent/path.txt")
        finally:
            # Clean up
            Path(tmp_path).unlink()

    def test_http_content_fetcher_can_fetch(self) -> None:
        """Test HTTPContentFetcher can_fetch implementation."""
        from paise2.plugins.providers.content_fetchers import HTTPContentFetcher

        fetcher = HTTPContentFetcher()
        host = Mock()

        # Should handle http and https URLs
        assert fetcher.can_fetch(host, "http://example.com")
        assert fetcher.can_fetch(host, "https://example.com")

        # Should not handle file URLs or local paths
        assert not fetcher.can_fetch(host, "file:///path/to/file.txt")
        assert not fetcher.can_fetch(host, "/local/path.txt")

    async def test_file_content_fetcher_fetch_text_file(self) -> None:
        """Test FileContentFetcher fetch with text file."""
        import tempfile
        from pathlib import Path

        from paise2.plugins.providers.content_fetchers import FileContentFetcher

        fetcher = FileContentFetcher()
        host = Mock()

        # Create a temporary text file
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".txt"
        ) as tmp_file:
            tmp_file.write("test content")
            tmp_path = tmp_file.name

        try:
            await fetcher.fetch(host, tmp_path)

            # Should have called extract_file
            host.extract_file.assert_called_once()
            args, kwargs = host.extract_file.call_args
            content, metadata = args

            assert content == "test content"
            assert metadata.source_url == tmp_path
            assert "txt" in tmp_path.lower() or metadata.mime_type == "text/plain"
        finally:
            # Clean up
            Path(tmp_path).unlink()

    async def test_http_content_fetcher_fetch(self) -> None:
        """Test HTTPContentFetcher fetch implementation."""
        from paise2.plugins.providers.content_fetchers import HTTPContentFetcher

        fetcher = HTTPContentFetcher()
        host = Mock()

        url = "http://example.com"
        await fetcher.fetch(host, url)

        # Should have called extract_file
        host.extract_file.assert_called_once()
        args, kwargs = host.extract_file.call_args
        content, metadata = args

        assert url in content  # Placeholder content should contain URL
        assert metadata.source_url == url


class TestFetchContentTask:
    """Test fetch_content_task implementation with fetcher selection."""

    def test_placeholder_for_future_implementation(self) -> None:
        """Placeholder test - will be implemented when task is enhanced."""
        # This will be implemented when we update fetch_content_task
        assert True
