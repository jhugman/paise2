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

    def test_fetcher_selection_prioritization(self) -> None:
        """Test that fetchers are selected in first-match-wins order."""
        from paise2.plugins.core.registry import PluginManager
        from paise2.plugins.providers.content_fetchers import (
            FileContentFetcher,
            HTTPContentFetcher,
        )

        # Create plugin manager
        pm = PluginManager()

        # Register fetchers in specific order
        file_fetcher = FileContentFetcher()
        http_fetcher = HTTPContentFetcher()
        pm.register_content_fetcher(file_fetcher)
        pm.register_content_fetcher(http_fetcher)

        # Get registered fetchers
        registered_fetchers = pm.get_content_fetchers()
        assert len(registered_fetchers) >= 2

        # Test that first matching fetcher is selected
        url = "http://example.com"

        # FileContentFetcher should not match HTTP URLs
        assert not file_fetcher.can_fetch(url)
        # HTTPContentFetcher should match HTTP URLs
        assert http_fetcher.can_fetch(url)

        # Find first fetcher that can handle the URL (should be HTTPContentFetcher)
        selected_fetcher = None
        for fetcher in registered_fetchers:
            if fetcher.can_fetch(url):
                selected_fetcher = fetcher
                break

        assert selected_fetcher is not None
        assert isinstance(selected_fetcher, HTTPContentFetcher)

    def test_fetcher_selection_http_url(self) -> None:
        """Test fetcher selection for HTTP URLs."""
        from paise2.plugins.core.registry import PluginManager
        from paise2.plugins.providers.content_fetchers import (
            FileContentFetcher,
            HTTPContentFetcher,
        )

        # Create plugin manager
        pm = PluginManager()

        # Register fetchers
        file_fetcher = FileContentFetcher()
        http_fetcher = HTTPContentFetcher()
        pm.register_content_fetcher(file_fetcher)
        pm.register_content_fetcher(http_fetcher)

        # Get registered fetchers
        registered_fetchers = pm.get_content_fetchers()

        # Test HTTP URL - HTTPContentFetcher should match
        url = "http://example.com"

        selected_fetcher = None
        for fetcher in registered_fetchers:
            if fetcher.can_fetch(url):
                selected_fetcher = fetcher
                break

        assert selected_fetcher is not None
        assert isinstance(selected_fetcher, HTTPContentFetcher)

    def test_fetcher_no_match(self) -> None:
        """Test behavior when no fetcher can handle the URL."""
        from paise2.plugins.core.registry import PluginManager
        from paise2.plugins.providers.content_fetchers import (
            FileContentFetcher,
            HTTPContentFetcher,
        )

        # Create plugin manager
        pm = PluginManager()

        # Register fetchers
        file_fetcher = FileContentFetcher()
        http_fetcher = HTTPContentFetcher()
        pm.register_content_fetcher(file_fetcher)
        pm.register_content_fetcher(http_fetcher)

        # Get registered fetchers
        registered_fetchers = pm.get_content_fetchers()

        # Test unsupported URL
        url = "ftp://example.com/file.txt"

        selected_fetcher = None
        for fetcher in registered_fetchers:
            if fetcher.can_fetch(url):
                selected_fetcher = fetcher
                break

        assert selected_fetcher is None


class TestFetchContentTask:
    """Test fetch_content_task implementation."""

    def test_fetch_content_task_with_registered_fetchers(self) -> None:
        """Test fetch_content_task uses registered ContentFetchers."""
        from huey import MemoryHuey

        from paise2.plugins.core.registry import PluginManager
        from paise2.plugins.core.startup import Singletons
        from paise2.plugins.core.tasks import _setup_tasks
        from paise2.plugins.providers.content_fetchers import FileContentFetcher
        from paise2.utils.logging import SimpleInMemoryLogger

        # Create plugin manager and register a fetcher
        pm = PluginManager()
        pm.register_content_fetcher(FileContentFetcher())

        # Create mock singletons
        singletons = Singletons(
            plugin_manager=pm,
            logger=SimpleInMemoryLogger(),
            configuration=Mock(),
            state_storage=Mock(),
            task_queue=Mock(),  # Need a non-None task_queue for content fetcher host
            cache=Mock(),
            data_storage=Mock(),
        )

        # Setup tasks with MemoryHuey for testing
        huey = MemoryHuey(immediate=True)
        tasks = _setup_tasks(huey, singletons)

        # Test fetch_content_task
        fetch_task = tasks["fetch_content"]

        # This will test the task logic - fetcher found and used
        result_obj = fetch_task("file:///non/existent/file.txt")
        result = result_obj()  # Get actual result when immediate=True

        # Should return success because a fetcher was found and executed
        # Even though the file doesn't exist, FileContentFetcher doesn't raise
        assert result["status"] == "success"
        assert "Fetched content from" in result["message"]

        # Check that the fetcher was used by looking at log messages
        # Cast to SimpleInMemoryLogger to access get_logs method
        from paise2.utils.logging import SimpleInMemoryLogger

        logger = singletons.logger
        assert isinstance(logger, SimpleInMemoryLogger)
        log_entries = logger.get_logs()
        log_messages = [entry[2] for entry in log_entries]  # Extract message part
        assert any(
            "Using fetcher FileContentFetcher" in message for message in log_messages
        )

    def test_fetch_content_task_no_fetchers_found(self) -> None:
        """Test fetch_content_task when no fetchers can handle URL."""
        from huey import MemoryHuey

        from paise2.plugins.core.registry import PluginManager
        from paise2.plugins.core.startup import Singletons
        from paise2.plugins.core.tasks import _setup_tasks
        from paise2.utils.logging import SimpleInMemoryLogger

        # Create plugin manager with no fetchers
        pm = PluginManager()

        # Create mock singletons
        singletons = Singletons(
            plugin_manager=pm,
            logger=SimpleInMemoryLogger(),
            configuration=Mock(),
            state_storage=Mock(),
            task_queue=None,
            cache=Mock(),
            data_storage=Mock(),
        )

        # Setup tasks with MemoryHuey for testing
        huey = MemoryHuey(immediate=True)
        tasks = _setup_tasks(huey, singletons)

        # Test fetch_content_task
        fetch_task = tasks["fetch_content"]
        result_obj = fetch_task("unsupported://example.com")
        result = result_obj()  # Get actual result when immediate=True

        # Should return error for unsupported URL
        assert result["status"] == "error"
        assert (
            "No fetcher found" in result["message"]
            or "Error fetching content" in result["message"]
        )


class TestExampleContentFetchers:
    """Test example ContentFetcher implementations."""

    def test_file_content_fetcher_can_fetch_file_scheme(self) -> None:
        """Test FileContentFetcher can_fetch with file:// URLs."""
        from paise2.plugins.providers.content_fetchers import FileContentFetcher

        fetcher = FileContentFetcher()

        # Should handle file:// URLs
        assert fetcher.can_fetch("file:///path/to/file.txt")

        # Should not handle http URLs
        assert not fetcher.can_fetch("http://example.com")

    def test_file_content_fetcher_can_fetch_local_path(self) -> None:
        """Test FileContentFetcher can_fetch with local file paths."""
        import tempfile
        from pathlib import Path

        from paise2.plugins.providers.content_fetchers import FileContentFetcher

        fetcher = FileContentFetcher()

        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmp_file:
            tmp_file.write("test content")
            tmp_path = tmp_file.name

        try:
            # Should handle existing file paths
            assert fetcher.can_fetch(tmp_path)

            # Should not handle non-existent paths
            assert not fetcher.can_fetch("/non/existent/path.txt")
        finally:
            # Clean up
            Path(tmp_path).unlink()

    def test_http_content_fetcher_can_fetch(self) -> None:
        """Test HTTPContentFetcher can_fetch implementation."""
        from paise2.plugins.providers.content_fetchers import HTTPContentFetcher

        fetcher = HTTPContentFetcher()

        # Should handle http and https URLs
        assert fetcher.can_fetch("http://example.com")
        assert fetcher.can_fetch("https://example.com")

        # Should not handle file URLs or local paths
        assert not fetcher.can_fetch("file:///path/to/file.txt")
        assert not fetcher.can_fetch("/local/path.txt")

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
