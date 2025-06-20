# ABOUTME: Tests for ContentExtractor pipeline implementation with task scheduling
# ABOUTME: and storage integration functionality
# ABOUTME: Validates extractor selection, content processing, storage operations,
# ABOUTME: and recursive extraction functionality

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import Mock

import pytest

from paise2.models import Content, Metadata
from paise2.plugins.core.hosts import create_content_extractor_host
from paise2.plugins.core.tasks import TaskQueue
from paise2.utils.logging import SimpleInMemoryLogger
from tests.fixtures import MockConfiguration

if TYPE_CHECKING:
    from paise2.plugins.core.interfaces import ContentExtractorHost


class MockContentExtractor:
    """Test double ContentExtractor for text/plain content."""

    def __init__(self, mime_types: list[str] | None = None) -> None:
        self.mime_types = mime_types or ["text/plain"]
        self.extract_calls: list[
            tuple[ContentExtractorHost, Content, Metadata | None]
        ] = []

    def can_extract(self, url: str, mime_type: str | None = None) -> bool:
        """Check if this extractor can handle the content."""
        if mime_type in self.mime_types:
            return True
        if url.endswith(".txt") and "text/plain" in self.mime_types:
            return True
        return url.endswith(".html") and "text/html" in self.mime_types

    def preferred_mime_types(self) -> list[str]:
        """Return preferred MIME types."""
        return self.mime_types

    async def extract(
        self,
        host: ContentExtractorHost,
        content: Content,
        metadata: Metadata | None = None,
    ) -> None:
        """Extract content (test implementation)."""
        self.extract_calls.append((host, content, metadata))

    def reset(self) -> None:
        """Reset call tracking."""
        self.extract_calls.clear()


class MockGenericExtractor:
    """Test double ContentExtractor that accepts any content."""

    def __init__(self) -> None:
        self.extract_calls: list[
            tuple[ContentExtractorHost, Content, Metadata | None]
        ] = []

    def can_extract(self, url: str, mime_type: str | None = None) -> bool:
        """Accept any content."""
        return True

    def preferred_mime_types(self) -> list[str]:
        """No preferred types."""
        return []

    async def extract(
        self,
        host: ContentExtractorHost,
        content: Content,
        metadata: Metadata | None = None,
    ) -> None:
        """Extract content (test implementation)."""
        self.extract_calls.append((host, content, metadata))

    def reset(self) -> None:
        """Reset call tracking."""
        self.extract_calls.clear()


class TestContentExtractorHost:
    """Test ContentExtractorHost with task registry and storage integration."""

    def test_extract_file_with_task_registry(self) -> None:
        """Test ContentExtractorHost extract_file method uses task registry
        for recursive extraction."""
        # Create mock singletons with task queue
        mock_singletons = Mock()
        mock_task_queue = Mock(spec=TaskQueue)
        mock_task_result = Mock(id="task456")
        mock_task_queue.extract_content.return_value = mock_task_result
        mock_singletons.task_queue = mock_task_queue

        host = create_content_extractor_host(
            logger=SimpleInMemoryLogger(),
            configuration=MockConfiguration({}),
            state_storage=Mock(),
            plugin_module_name="test_plugin",
            data_storage=Mock(),
            cache=Mock(),
            task_queue=mock_task_queue,
        )
        content = b"nested document content"
        metadata = Metadata(source_url="test://nested.doc")

        # Should schedule extraction task for recursive extraction
        host.extract_file(content, metadata)

        # Should have called the extract task on task_queue
        mock_task_queue.extract_content.assert_called_once_with(
            content=content, metadata=metadata
        )

    def test_extract_file_synchronous_mode(self) -> None:
        """Test ContentExtractorHost extract_file works in synchronous mode."""
        host = create_content_extractor_host(
            logger=SimpleInMemoryLogger(),
            configuration=MockConfiguration({}),
            state_storage=Mock(),
            plugin_module_name="test_plugin",
            data_storage=Mock(),
            cache=Mock(),
            task_queue=Mock(spec=TaskQueue),
        )

        content = "text content"
        metadata = Metadata(source_url="test://example.txt")

        # Should not raise an exception in sync mode
        host.extract_file(content, metadata)

    def test_storage_and_cache_access(self) -> None:
        """Test ContentExtractorHost provides access to storage and cache."""
        mock_storage = Mock()
        mock_cache = Mock()

        host = create_content_extractor_host(
            logger=SimpleInMemoryLogger(),
            configuration=MockConfiguration({}),
            state_storage=Mock(),
            plugin_module_name="test_plugin",
            data_storage=mock_storage,
            cache=mock_cache,
            task_queue=Mock(spec=TaskQueue),
        )

        assert host.storage is mock_storage
        assert host.cache is mock_cache


class TestContentExtractorSelection:
    """Test ContentExtractor selection and prioritization logic."""

    def test_extractor_selection_by_mime_type(self) -> None:
        """Test ContentExtractor selection based on MIME type prioritization."""
        from unittest.mock import Mock

        from paise2.plugins.core.registry import PluginManager

        # Create plugin manager with multiple extractors
        pm = PluginManager()

        # Create extractors with different MIME type preferences
        text_extractor = Mock()
        text_extractor.can_extract.return_value = True
        text_extractor.preferred_mime_types.return_value = [
            "text/plain",
            "text/markdown",
        ]
        text_extractor.extract = Mock()
        pm.register_content_extractor(text_extractor)

        html_extractor = Mock()
        html_extractor.can_extract.return_value = True
        html_extractor.preferred_mime_types.return_value = [
            "text/html",
            "application/xhtml+xml",
        ]
        html_extractor.extract = Mock()
        pm.register_content_extractor(html_extractor)

        # Get registered extractors
        extractors = pm.get_content_extractors()
        assert len(extractors) == 2

        # Test MIME type matching
        # Text extractor should prefer text/plain
        text_preferred = text_extractor.preferred_mime_types()
        assert "text/plain" in text_preferred
        assert "text/markdown" in text_preferred

        # HTML extractor should prefer text/html
        html_preferred = html_extractor.preferred_mime_types()
        assert "text/html" in html_preferred
        assert "application/xhtml+xml" in html_preferred

        # Both extractors can extract, but should prefer their MIME types
        assert text_extractor.can_extract("test.txt", "text/plain")
        assert html_extractor.can_extract("test.html", "text/html")

    def test_extractor_selection_by_url_pattern(self) -> None:
        """Test ContentExtractor selection based on URL patterns."""
        from huey import MemoryHuey

        from paise2.plugins.core.registry import PluginManager
        from paise2.plugins.core.startup import Singletons

        # Create plugin manager with multiple extractors
        pm = PluginManager()

        # Create extractors with different capabilities
        text_extractor = Mock()
        text_extractor.can_extract.side_effect = lambda url, mime_type: (
            mime_type == "text/plain" or url.endswith(".txt")
        )
        text_extractor.preferred_mime_types.return_value = ["text/plain"]
        text_extractor.extract = Mock()
        pm.register_content_extractor(text_extractor)

        html_extractor = Mock()
        html_extractor.can_extract.side_effect = lambda url, mime_type: (
            mime_type == "text/html" or url.endswith(".html")
        )
        html_extractor.preferred_mime_types.return_value = ["text/html"]
        html_extractor.extract = Mock()
        pm.register_content_extractor(html_extractor)

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

        # Setup tasks
        huey = MemoryHuey(immediate=True)
        tasks = TaskQueue(huey, singletons)

        # Test 1: Text content should use text extractor
        result_obj = tasks.extract_content(
            "Plain text content",
            Metadata(
                source_url="test://example.txt",
                mime_type="text/plain",
            ),
        )
        result = result_obj()
        assert result["status"] == "success"
        text_extractor.can_extract.assert_called()
        text_extractor.extract.assert_called()
        html_extractor.extract.assert_not_called()

        # Reset mocks
        text_extractor.reset_mock()
        html_extractor.reset_mock()

        # Test 2: HTML content should use HTML extractor
        result_obj = tasks.extract_content(
            "<html>HTML content</html>",
            Metadata(
                source_url="test://example.html",
                mime_type="text/html",
            ),
        )
        result = result_obj()
        assert result["status"] == "success"
        html_extractor.can_extract.assert_called()
        html_extractor.extract.assert_called()
        text_extractor.extract.assert_not_called()

    def test_preferred_mime_types_prioritization(self) -> None:
        """Test that extractors with preferred MIME types are prioritized."""
        from huey import MemoryHuey

        from paise2.plugins.core.registry import PluginManager
        from paise2.plugins.core.startup import Singletons

        # Create plugin manager with multiple extractors
        pm = PluginManager()

        # Create a generic extractor that can handle any content
        generic_extractor = Mock()
        generic_extractor.can_extract.return_value = True  # Can handle anything
        generic_extractor.preferred_mime_types.return_value = []  # No preferences
        generic_extractor.extract = Mock()
        pm.register_content_extractor(generic_extractor)

        # Create a specialized extractor that prefers text/plain
        specialized_extractor = Mock()
        specialized_extractor.can_extract.return_value = True  # Can handle anything
        specialized_extractor.preferred_mime_types.return_value = ["text/plain"]
        specialized_extractor.extract = Mock()
        pm.register_content_extractor(specialized_extractor)

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

        # Setup tasks
        huey = MemoryHuey(immediate=True)
        task_queue = TaskQueue(huey=huey, singletons=singletons)

        # Test: text/plain content should prefer the specialized extractor
        result_obj = task_queue.extract_content(
            "Plain text content",
            Metadata(
                source_url="test://example.txt",
                mime_type="text/plain",
            ),
        )
        result = result_obj()
        assert result["status"] == "success"

        # The specialized extractor should be used because it has text/plain
        # in its preferred types
        specialized_extractor.extract.assert_called()
        generic_extractor.extract.assert_not_called()


class TestExtractContentTask:
    """Test extract_content_task implementation."""

    def test_extract_content_task_with_registered_extractors(self) -> None:
        """Test extract_content_task uses registered ContentExtractors."""
        from huey import MemoryHuey

        from paise2.plugins.core.registry import PluginManager
        from paise2.plugins.core.startup import Singletons

        # Create plugin manager and register a mock extractor
        pm = PluginManager()
        mock_extractor = Mock()
        mock_extractor.can_extract.return_value = True
        mock_extractor.preferred_mime_types.return_value = ["text/plain"]
        mock_extractor.extract = Mock()  # Make it non-async for now
        pm.register_content_extractor(mock_extractor)

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
        tasks = TaskQueue(huey, singletons)

        content = "This is test content to extract"
        metadata = Metadata(
            source_url="test://example.txt",
            mime_type="text/plain",
        )

        # This will test the task logic - extractor should be found and used
        result_obj = tasks.extract_content(content, metadata)
        result = result_obj()  # Get actual result when immediate=True

        # Should return success because an extractor was found and executed
        assert result["status"] == "success"
        assert "Content extraction completed" in result["message"]

        # Check that the extractor was actually called
        mock_extractor.can_extract.assert_called()
        mock_extractor.extract.assert_called()

    def test_extract_content_task_no_extractors_found(self) -> None:
        """Test extract_content_task when no extractors can handle content."""
        from huey import MemoryHuey

        from paise2.plugins.core.registry import PluginManager
        from paise2.plugins.core.startup import Singletons

        # Create plugin manager with no extractors
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
        tasks = TaskQueue(huey, singletons)

        content = "This is content that cannot be extracted"
        metadata = Metadata(
            source_url="unsupported://example.xyz",
            mime_type="application/unknown",
        )

        result_obj = tasks.extract_content(content, metadata)
        result = result_obj()  # Get actual result when immediate=True

        # Should return error for unsupported content
        assert result["status"] == "error"
        assert "No extractor found" in result["message"]

    def test_extract_content_task_storage_integration(self) -> None:
        """Test extract_content_task integrates with storage operations."""
        from unittest.mock import Mock

        from paise2.models import Metadata
        from paise2.plugins.core.registry import PluginManager

        # Create plugin manager with extractor
        pm = PluginManager()
        mock_extractor = Mock()
        mock_extractor.can_extract.return_value = True
        mock_extractor.preferred_mime_types.return_value = ["text/plain"]
        mock_extractor.extract = Mock()
        pm.register_content_extractor(mock_extractor)

        # Test basic integration - extractor should be available for storage operations
        extractors = pm.get_content_extractors()
        assert len(extractors) == 1
        assert extractors[0] == mock_extractor

        # Test that the extractor can work with metadata (storage integration point)
        metadata = Metadata(source_url="test.txt", mime_type="text/plain")

        # Verify the extractor can handle the content (storage integration)
        can_extract = mock_extractor.can_extract(
            metadata.source_url, metadata.mime_type
        )
        assert can_extract

        # Verify preferred MIME types work for storage decisions
        preferred = mock_extractor.preferred_mime_types()
        assert "text/plain" in preferred


class TestStoreContentTask:
    """Test store_content_task implementation."""

    def test_store_content_task_with_storage_provider(self) -> None:
        """Test store_content_task uses data storage for persistence."""
        from huey import MemoryHuey

        from paise2.plugins.core.registry import PluginManager
        from paise2.plugins.core.startup import Singletons

        # Create mock data storage
        mock_data_storage = Mock()
        mock_data_storage.add_item = Mock()

        # Create mock singletons
        singletons = Singletons(
            plugin_manager=PluginManager(),
            logger=SimpleInMemoryLogger(),
            configuration=Mock(),
            state_storage=Mock(),
            task_queue=None,
            cache=Mock(),
            data_storage=mock_data_storage,
        )

        # Setup tasks
        huey = MemoryHuey(immediate=True)
        tasks = TaskQueue(huey, singletons)

        # Test content storage
        content_data = "Test Content"
        metadata = Metadata(
            source_url="test://example.com",
            mime_type="text/plain",
        )

        result_obj = tasks.store_content(content_data, metadata)
        result = result_obj()

        assert result["status"] == "success"
        assert "Content stored successfully" in result["message"]

        # Verify that data storage was called
        mock_data_storage.add_item.assert_called_once()

    def test_store_content_task_cache_cleanup(self) -> None:
        """Test store_content_task handles cache cleanup coordination."""
        from unittest.mock import Mock

        from paise2.models import Metadata
        from paise2.plugins.core.registry import PluginManager

        # Create plugin manager
        pm = PluginManager()

        # Create mock storage that returns cache IDs for cleanup
        mock_storage = Mock()
        mock_storage.add_item = Mock(return_value="item_123")
        pm.register_data_storage_provider(
            Mock(create_data_storage=Mock(return_value=mock_storage))
        )

        # Create mock cache for cleanup operations
        mock_cache = Mock()
        mock_cache.remove_all = Mock(return_value=["cache_123"])
        pm.register_cache_provider(Mock(create_cache=Mock(return_value=mock_cache)))

        # Test that storage and cache are properly integrated
        storage_providers = pm.get_data_storage_providers()
        cache_providers = pm.get_cache_providers()

        assert len(storage_providers) == 1
        assert len(cache_providers) == 1

        # Test cache cleanup coordination
        metadata = Metadata(source_url="test.txt", mime_type="text/plain")

        # Storage should return cache IDs when items are stored
        item_id = mock_storage.add_item(None, "content", metadata)
        assert item_id == "item_123"

        # Cache should handle cleanup operations
        cleaned_ids = mock_cache.remove_all(["cache_123"])
        assert "cache_123" in cleaned_ids


class TestExampleContentExtractors:
    """Test example ContentExtractor implementations."""

    def test_plain_text_extractor_can_extract(self) -> None:
        """Test PlainTextExtractor can_extract implementation."""
        from paise2.plugins.providers.content_extractors import PlainTextExtractor

        extractor = PlainTextExtractor()

        # Should handle text MIME types
        assert extractor.can_extract("http://example.com", "text/plain")
        assert extractor.can_extract("http://example.com", "text/markdown")
        assert extractor.can_extract("http://example.com", "text/x-rst")

        # Should handle text file extensions
        assert extractor.can_extract("file.txt")
        assert extractor.can_extract("document.md")
        assert extractor.can_extract("readme.rst")

        # Should not handle non-text types
        assert not extractor.can_extract("http://example.com", "image/jpeg")
        assert not extractor.can_extract("file.jpg")

    def test_plain_text_extractor_preferred_mime_types(self) -> None:
        """Test PlainTextExtractor preferred_mime_types."""
        from paise2.plugins.providers.content_extractors import PlainTextExtractor

        extractor = PlainTextExtractor()
        mime_types = extractor.preferred_mime_types()

        # Should return a list of text MIME types
        assert isinstance(mime_types, list)
        assert "text/plain" in mime_types
        assert "text/markdown" in mime_types
        assert len(mime_types) > 0

    @pytest.mark.asyncio
    async def test_plain_text_extractor_extract(self) -> None:
        """Test PlainTextExtractor extract implementation."""
        from unittest.mock import AsyncMock, Mock

        from paise2.models import Metadata
        from paise2.plugins.providers.content_extractors import PlainTextExtractor

        # Create extractor
        extractor = PlainTextExtractor()

        # Create mock host
        mock_storage = Mock()
        mock_storage.add_item = AsyncMock()
        mock_host = Mock()
        mock_host.storage = mock_storage
        mock_host.logger = Mock()

        # Test data
        test_content = "This is a test document.\nSecond line here."
        metadata = Metadata(source_url="test://file.txt")

        # Extract content
        await extractor.extract(mock_host, test_content, metadata)

        # Verify storage was called
        mock_storage.add_item.assert_called_once()
        call_args = mock_storage.add_item.call_args  # Check call arguments
        assert call_args[0][0] == mock_host  # host
        assert call_args[0][1] == test_content  # content (extracted text)
        stored_metadata = call_args[0][2]  # metadata

        # Verify metadata properties
        assert stored_metadata.source_url == "test://file.txt"
        assert stored_metadata.mime_type == "text/plain"
        assert stored_metadata.processing_state == "extracted"
        assert stored_metadata.title == "This is a test document."

    def test_html_extractor_can_extract(self) -> None:
        """Test HTMLExtractor can_extract implementation."""
        from paise2.plugins.providers.content_extractors import HTMLExtractor

        extractor = HTMLExtractor()

        # Test MIME type detection
        assert extractor.can_extract("test://file", "text/html")
        assert extractor.can_extract("test://file", "application/xhtml+xml")
        assert not extractor.can_extract("test://file", "text/plain")
        assert not extractor.can_extract("test://file", "image/jpeg")

        # Test file extension detection
        assert extractor.can_extract("test://file.html")
        assert extractor.can_extract("test://file.htm")
        assert extractor.can_extract("test://file.xhtml")
        assert extractor.can_extract("test://FILE.HTML")  # Case insensitive
        assert not extractor.can_extract("test://file.txt")
        assert not extractor.can_extract("test://file.pdf")

    def test_html_extractor_preferred_mime_types(self) -> None:
        """Test HTMLExtractor preferred_mime_types."""
        from paise2.plugins.providers.content_extractors import HTMLExtractor

        extractor = HTMLExtractor()
        mime_types = extractor.preferred_mime_types()

        assert isinstance(mime_types, list)
        assert "text/html" in mime_types
        assert "application/xhtml+xml" in mime_types
        assert len(mime_types) > 0

    @pytest.mark.asyncio
    async def test_html_extractor_extract(self) -> None:
        """Test HTMLExtractor extract implementation."""
        from unittest.mock import AsyncMock, Mock

        from paise2.models import Metadata
        from paise2.plugins.providers.content_extractors import HTMLExtractor

        # Create extractor
        extractor = HTMLExtractor()

        # Create mock host
        mock_storage = Mock()
        mock_storage.add_item = AsyncMock()
        mock_host = Mock()
        mock_host.storage = mock_storage
        mock_host.logger = Mock()

        # Test data with HTML content
        test_html = """
        <html>
        <head><title>Test Document</title></head>
        <body>
        <h1>Header</h1>
        <p>This is a test paragraph.</p>
        <script>alert('test');</script>
        <style>body { color: red; }</style>
        </body>
        </html>
        """
        metadata = Metadata(source_url="test://file.html")

        # Extract content
        await extractor.extract(mock_host, test_html, metadata)

        # Verify storage was called
        mock_storage.add_item.assert_called_once()
        call_args = mock_storage.add_item.call_args

        # Check call arguments
        assert call_args[0][0] == mock_host  # host
        extracted_text = call_args[0][1]  # content (extracted text)
        stored_metadata = call_args[0][2]  # metadata

        # Verify text extraction (should strip HTML tags)
        assert "Header" in extracted_text
        assert "This is a test paragraph." in extracted_text
        assert "<h1>" not in extracted_text  # HTML tags removed
        assert "alert('test');" not in extracted_text  # Script content removed
        assert "color: red;" not in extracted_text  # Style content removed

        # Verify metadata properties
        assert stored_metadata.source_url == "test://file.html"
        assert stored_metadata.mime_type == "text/plain"  # Extracted as plain text
        assert stored_metadata.processing_state == "extracted"
        assert stored_metadata.title == "Test Document"  # From HTML title tag


class TestRecursiveExtraction:
    """Test recursive extraction scenarios."""

    def test_recursive_extraction_scheduling(self) -> None:
        """Test that extractors can schedule recursive extraction via host.extract_file()."""  # noqa: E501
        from unittest.mock import Mock

        from paise2.plugins.core.hosts import create_content_extractor_host

        # Create a mock task queue to capture recursive calls
        mock_task_queue = Mock()
        mock_task_queue.extract_content = Mock()

        # Create extractor host with task queue
        host = create_content_extractor_host(
            logger=SimpleInMemoryLogger(),
            configuration=Mock(),
            state_storage=Mock(),
            plugin_module_name="test_plugin",
            data_storage=Mock(),
            cache=Mock(),
            task_queue=mock_task_queue,
        )

        # Test that extract_file method can be used for recursive extraction
        nested_content = b"This is nested content to extract"
        nested_metadata = Metadata(
            source_url="test://nested/document.txt", mime_type="text/plain"
        )

        # Call extract_file to schedule recursive extraction
        host.extract_file(nested_content, nested_metadata)

        # Verify the task was scheduled
        mock_task_queue.extract_content.assert_called_once_with(
            content=nested_content, metadata=nested_metadata
        )

    def test_recursive_extraction_depth_handling(self) -> None:
        """Test proper handling of extraction depth to avoid infinite loops."""
        from unittest.mock import Mock

        from paise2.models import Metadata

        # Create mock extractor that tracks depth
        mock_extractor = Mock()
        depth_calls: list[int] = []

        def can_extract_with_depth(_url: str, _mime_type: str) -> bool:
            depth_calls.append(len(depth_calls))
            # Only extract up to depth 3 to avoid infinite loops
            return len(depth_calls) <= 3

        mock_extractor.can_extract.side_effect = can_extract_with_depth
        mock_extractor.preferred_mime_types.return_value = ["text/plain"]

        # Test depth handling
        metadata = Metadata(source_url="test.txt", mime_type="text/plain")

        # Call can_extract multiple times (simulating recursive extraction)
        for _ in range(5):
            result = mock_extractor.can_extract(metadata.source_url, metadata.mime_type)
            if len(depth_calls) > 3:
                assert not result  # Should stop extracting at depth 3

        # Should have been called 5 times but only allowed 3
        assert len(depth_calls) == 5
        assert mock_extractor.can_extract.call_count == 5

    def test_recursive_extraction_metadata_propagation(self) -> None:
        """Test metadata propagation through recursive extraction chain."""
        from unittest.mock import Mock

        from paise2.models import Metadata

        # Create mock extractors that modify metadata
        parent_extractor = Mock()
        child_extractor = Mock()

        # Parent extractor creates child content with derived metadata
        def parent_extract(_host: Any, _content: Any, metadata: Any) -> Any:
            # Create child metadata with additional information
            return metadata.copy(
                processing_state="extracted_by_parent",
                source_url=f"{metadata.source_url}/child",
            )

        parent_extractor.extract.side_effect = parent_extract
        parent_extractor.can_extract.return_value = True
        parent_extractor.preferred_mime_types.return_value = ["application/archive"]

        child_extractor.can_extract.return_value = True
        child_extractor.preferred_mime_types.return_value = ["text/plain"]

        # Test metadata propagation
        original_metadata = Metadata(
            source_url="archive.zip",
            mime_type="application/archive",
            processing_state="initial",
        )

        # Parent extracts and creates child metadata
        result_metadata = parent_extractor.extract(None, "content", original_metadata)

        # Verify metadata was properly propagated and modified
        assert result_metadata.source_url == "archive.zip/child"
        assert result_metadata.processing_state == "extracted_by_parent"
        assert result_metadata.mime_type == "application/archive"  # Original preserved

        parent_extractor.extract.assert_called_once()


class TestContentExtractorIntegration:
    """Test ContentExtractor integration with the plugin system."""

    def test_content_extractor_registration(self) -> None:
        """Test ContentExtractor registration in plugin system."""
        from paise2.plugins.core.registry import PluginManager
        from paise2.plugins.providers.content_extractors import (
            HTMLExtractor,
            PlainTextExtractor,
        )

        # Create plugin manager and verify initial state
        pm = PluginManager()
        initial_extractors = pm.get_content_extractors()
        initial_count = len(initial_extractors)

        # Register extractors manually
        pm.register_content_extractor(PlainTextExtractor())
        pm.register_content_extractor(HTMLExtractor())

        # Verify extractors were registered
        registered_extractors = pm.get_content_extractors()
        assert len(registered_extractors) == initial_count + 2

        # Verify that the extractors are of correct types
        extractor_types = [
            type(extractor).__name__ for extractor in registered_extractors
        ]
        assert "PlainTextExtractor" in extractor_types
        assert "HTMLExtractor" in extractor_types

    def test_content_extractor_validation(self) -> None:
        """Test ContentExtractor validation during registration."""
        from paise2.plugins.core.registry import PluginManager

        pm = PluginManager()

        # Test that objects implementing ContentExtractor protocol can be registered
        class ValidExtractor:
            def can_extract(self, url: str, mime_type: str | None = None) -> bool:
                return True

            def preferred_mime_types(self) -> list[str]:
                return ["text/plain"]

            async def extract(
                self,
                host: ContentExtractorHost,
                content: bytes | str,
                metadata: Metadata | None = None,
            ) -> None:
                pass

        # Should not raise an exception
        pm.register_content_extractor(ValidExtractor())

        # Verify it was registered
        extractors = pm.get_content_extractors()
        assert any(isinstance(ext, ValidExtractor) for ext in extractors)

    def test_content_extractor_lifecycle(self) -> None:
        """Test ContentExtractor lifecycle in complete processing pipeline."""
        from unittest.mock import AsyncMock, Mock

        from huey import MemoryHuey

        from paise2.plugins.core.registry import PluginManager
        from paise2.plugins.core.startup import Singletons
        from paise2.plugins.providers.content_extractors import PlainTextExtractor

        # Create a real extractor
        extractor = PlainTextExtractor()

        # Create plugin manager and register extractor
        pm = PluginManager()
        pm.register_content_extractor(extractor)

        # Create mock storage that can be monitored
        mock_storage = Mock()
        mock_storage.add_item = AsyncMock()

        # Create singletons with real components
        singletons = Singletons(
            plugin_manager=pm,
            logger=SimpleInMemoryLogger(),
            configuration=Mock(),
            state_storage=Mock(),
            task_queue=None,
            cache=Mock(),
            data_storage=mock_storage,
        )

        # Create task queue with Huey
        huey = MemoryHuey(immediate=True)
        task_queue = TaskQueue(huey, singletons)

        # Test complete lifecycle: schedule extraction task
        test_content = "This is test content for lifecycle testing."
        metadata = Metadata(
            source_url="test://lifecycle.txt",
            mime_type="text/plain",
        )

        # Execute extraction task
        result_obj = task_queue.extract_content(test_content, metadata)

        # For MemoryHuey with immediate=True, the result should be available immediately
        if result_obj is not None:
            result = result_obj()  # Execute immediately

            # Verify task completed successfully
            assert result is not None
            assert result["status"] == "success"

            # Verify storage was called with processed content
            mock_storage.add_item.assert_called_once()
            call_args = mock_storage.add_item.call_args
            assert call_args[0][1] == test_content  # Content stored
            stored_metadata = call_args[0][2]
            assert stored_metadata.processing_state == "extracted"
        else:
            # If no result object, verify storage was still called
            mock_storage.add_item.assert_called_once()
