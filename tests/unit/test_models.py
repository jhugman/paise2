# ABOUTME: Unit tests for core data models
# ABOUTME: Tests the immutable data structures used throughout the PAISE2 system

from datetime import datetime

import pytest

from paise2.models import Metadata


class TestMetadata:
    """Test the Metadata dataclass with immutable operations."""

    def test_metadata_creation_with_defaults(self) -> None:
        """Test creating metadata with default values."""
        metadata = Metadata(source_url="https://example.com/doc.txt")

        assert metadata.source_url == "https://example.com/doc.txt"
        assert metadata.location is None
        assert metadata.title is None
        assert metadata.parent_id is None
        assert metadata.description is None
        assert metadata.processing_state == "pending"
        assert metadata.indexed_at is None
        assert metadata.created_at is None
        assert metadata.modified_at is None
        assert metadata.author is None
        assert metadata.tags == []
        assert metadata.mime_type is None
        assert metadata.extra == {}

    def test_metadata_creation_with_all_fields(self) -> None:
        """Test creating metadata with all fields specified."""
        now = datetime.now()
        tags = ["tag1", "tag2"]
        extra = {"custom": "value"}

        metadata = Metadata(
            source_url="https://example.com/doc.txt",
            location="/cache/item123",
            title="Test Document",
            parent_id="parent123",
            description="A test document",
            processing_state="completed",
            indexed_at=now,
            created_at=now,
            modified_at=now,
            author="Test Author",
            tags=tags,
            mime_type="text/plain",
            extra=extra,
        )

        assert metadata.source_url == "https://example.com/doc.txt"
        assert metadata.location == "/cache/item123"
        assert metadata.title == "Test Document"
        assert metadata.parent_id == "parent123"
        assert metadata.description == "A test document"
        assert metadata.processing_state == "completed"
        assert metadata.indexed_at == now
        assert metadata.created_at == now
        assert metadata.modified_at == now
        assert metadata.author == "Test Author"
        assert metadata.tags == tags
        assert metadata.mime_type == "text/plain"
        assert metadata.extra == extra

    def test_metadata_is_immutable(self) -> None:
        """Test that metadata is truly immutable."""
        metadata = Metadata(source_url="https://example.com/doc.txt")

        # Should not be able to modify fields
        with pytest.raises(AttributeError):
            metadata.title = "Modified Title"  # type: ignore[misc]

    def test_metadata_copy_with_changes(self) -> None:
        """Test creating a copy with specific changes."""
        original = Metadata(
            source_url="https://example.com/doc.txt",
            title="Original Title",
            tags=["tag1"],
            extra={"key1": "value1"},
        )

        modified = original.copy(
            title="Modified Title",
            processing_state="completed",
            tags=["tag2"],
        )

        # Original should be unchanged
        assert original.title == "Original Title"
        assert original.processing_state == "pending"
        assert original.tags == ["tag1"]

        # Modified should have changes
        assert modified.source_url == "https://example.com/doc.txt"  # Unchanged
        assert modified.title == "Modified Title"
        assert modified.processing_state == "completed"
        assert modified.tags == ["tag2"]
        assert modified.extra == {"key1": "value1"}  # Unchanged

    def test_metadata_merge_scalar_values(self) -> None:
        """Test merging metadata with scalar value overrides."""
        base = Metadata(
            source_url="https://example.com/doc.txt",
            title="Base Title",
            processing_state="pending",
            author="Base Author",
        )

        patch = Metadata(
            source_url="https://example.com/doc.txt",  # Same URL required
            title="Patch Title",
            processing_state="completed",
            description="Added description",
        )

        merged = base.merge(patch)

        assert merged.source_url == "https://example.com/doc.txt"
        assert merged.title == "Patch Title"  # Overridden
        assert merged.processing_state == "completed"  # Overridden
        assert merged.author == "Base Author"  # Unchanged
        assert merged.description == "Added description"  # Added

    def test_metadata_merge_list_concatenation(self) -> None:
        """Test that lists are concatenated when merging."""
        base = Metadata(
            source_url="https://example.com/doc.txt",
            tags=["tag1", "tag2"],
        )

        patch = Metadata(
            source_url="https://example.com/doc.txt",
            tags=["tag3", "tag4"],
        )

        merged = base.merge(patch)

        assert merged.tags == ["tag1", "tag2", "tag3", "tag4"]

    def test_metadata_merge_dict_recursive(self) -> None:
        """Test that dictionaries are merged recursively."""
        base = Metadata(
            source_url="https://example.com/doc.txt",
            extra={
                "key1": "value1",
                "nested": {"a": 1, "b": 2},
                "base_only": "stays",
            },
        )

        patch = Metadata(
            source_url="https://example.com/doc.txt",
            extra={
                "key1": "overridden",
                "nested": {"b": 3, "c": 4},
                "patch_only": "added",
            },
        )

        merged = base.merge(patch)

        expected_extra = {
            "key1": "overridden",
            "nested": {"a": 1, "b": 3, "c": 4},
            "base_only": "stays",
            "patch_only": "added",
        }
        assert merged.extra == expected_extra

    def test_metadata_merge_with_none_values(self) -> None:
        """Test that None values in patch don't override base values."""
        base = Metadata(
            source_url="https://example.com/doc.txt",
            title="Base Title",
            author="Base Author",
        )

        patch = Metadata(
            source_url="https://example.com/doc.txt",
            title=None,  # Should not override
            description="Added description",
        )

        merged = base.merge(patch)

        assert merged.title == "Base Title"  # Not overridden by None
        assert merged.author == "Base Author"  # Unchanged
        assert merged.description == "Added description"  # Added

    def test_metadata_merge_empty_lists_and_dicts(self) -> None:
        """Test merging with empty lists and dictionaries."""
        base = Metadata(
            source_url="https://example.com/doc.txt",
            tags=["tag1"],
            extra={"key1": "value1"},
        )

        patch = Metadata(
            source_url="https://example.com/doc.txt",
            tags=[],
            extra={},
        )

        merged = base.merge(patch)

        # Empty lists should still concatenate
        assert merged.tags == ["tag1"]
        # Empty dicts should merge (no change)
        assert merged.extra == {"key1": "value1"}
