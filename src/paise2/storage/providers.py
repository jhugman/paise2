# ABOUTME: Data storage provider implementations for content storage and retrieval.
# ABOUTME: Provides memory and SQLite-based storage with deduplication support.

from __future__ import annotations

import hashlib
import sqlite3
import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from paise2.config.models import Configuration
    from paise2.models import CacheId, Content, ItemId, Metadata
    from paise2.plugins.core.interfaces import DataStorage, DataStorageHost


class MemoryDataStorage:
    """
    In-memory data storage implementation.

    Provides metadata storage for development and testing.
    For compatibility with the rest of the system, we still store content in memory,
    but in a production implementation we would only store content hashes.

    Data is lost when the process exits.
    """

    def __init__(self) -> None:
        """Initialize memory storage with empty storage dictionary."""
        self._items: dict[ItemId, tuple[Content, Metadata]] = {}
        self._next_id = 1

    async def add_item(
        self,
        host: DataStorageHost,  # noqa: ARG002
        content: Content,
        metadata: Metadata,
    ) -> ItemId:
        """Add a new item to storage."""
        item_id = f"item_{self._next_id}"
        self._next_id += 1
        self._items[item_id] = (content, metadata)
        return item_id

    async def update_item(
        self,
        host: DataStorageHost,  # noqa: ARG002
        item_id: ItemId,
        content: Content,
    ) -> None:
        """Update the content of an existing item."""
        if item_id in self._items:
            _, metadata = self._items[item_id]
            self._items[item_id] = (content, metadata)

    async def update_metadata(
        self,
        host: DataStorageHost,  # noqa: ARG002
        item_id: ItemId,
        metadata: Metadata,
    ) -> None:
        """Update the metadata of an existing item."""
        if item_id in self._items:
            content, _ = self._items[item_id]
            self._items[item_id] = (content, metadata)

    async def find_item_id(
        self,
        host: DataStorageHost,  # noqa: ARG002
        metadata: Metadata,
    ) -> ItemId | None:
        """Find an item by its metadata."""
        for item_id, (_, stored_metadata) in self._items.items():
            if stored_metadata.source_url == metadata.source_url:
                return item_id
        return None

    async def find_item(self, item_id: ItemId) -> Metadata | None:
        """Retrieve metadata for an item by its ID."""
        if item_id in self._items:
            _, metadata = self._items[item_id]
            return metadata
        return None

    async def remove_item(
        self,
        host: DataStorageHost,  # noqa: ARG002
        item_id: ItemId,
    ) -> CacheId | None:
        """Remove an item from storage."""
        if item_id in self._items:
            del self._items[item_id]
            return f"cache_{item_id}"  # Return cache ID for cleanup
        return None

    async def remove_items_by_metadata(
        self,
        host: DataStorageHost,  # noqa: ARG002
        metadata: Metadata,
    ) -> list[CacheId]:
        """Remove all items matching the given metadata."""
        to_remove = []
        cache_ids = []
        for item_id, (_, stored_metadata) in self._items.items():
            if stored_metadata.source_url == metadata.source_url:
                to_remove.append(item_id)
                cache_ids.append(f"cache_{item_id}")

        for item_id in to_remove:
            del self._items[item_id]

        return cache_ids

    async def remove_items_by_url(
        self, host: DataStorageHost, url: str
    ) -> list[CacheId]:
        """Remove all items associated with a given URL."""
        from paise2.models import Metadata

        metadata = Metadata(source_url=url)
        return await self.remove_items_by_metadata(host, metadata)


class MemoryDataStorageProvider:
    """
    Memory data storage provider.

    Creates in-memory data storage instances for development and testing.
    """

    def create_data_storage(self, configuration: Configuration) -> DataStorage:  # noqa: ARG002
        """Create a memory-based data storage instance."""
        return MemoryDataStorage()


class SQLiteDataStorage:
    """
    SQLite-based data storage implementation.

    Provides persistent metadata storage using SQLite database.
    Content is NOT stored in the database - only metadata and content hashes
    are stored to minimize disk usage and avoid duplication.

    The actual content is intended to be stored elsewhere (in cache or
    original location).
    """

    def __init__(self, db_path: Path | None) -> None:
        """Initialize SQLite storage with database file."""
        self.db_path = db_path
        self._init_database()

    def _connection(self) -> sqlite3.Connection:
        """Create a database connection."""
        if self.db_path is not None:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path or ":memory:")
        conn.row_factory = sqlite3.Row

        # Enable foreign key constraints
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_database(self) -> None:
        """Initialize the database schema for metadata storage with content hashes."""
        with self._connection() as conn:
            # Create items table with content hash but no actual content
            conn.execute("""
                CREATE TABLE IF NOT EXISTS items (
                    item_id TEXT PRIMARY KEY,
                    content_hash TEXT NOT NULL,
                        -- Hash of content for deduplication and lookups
                    content_type
                        TEXT CHECK(content_type IN ('string', 'blob')) NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indexes for efficient querying
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_items_content_hash ON items(content_hash)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_items_metadata ON items(metadata_json)
            """)

    def _compute_content_hash(self, content: Content) -> str:
        """
        Compute a hash for content deduplication and lookup.

        Args:
            content: Content to hash (string or bytes)

        Returns:
            Hex-encoded SHA-256 hash of content
        """
        if isinstance(content, str):
            # For strings, encode to UTF-8 before hashing
            return hashlib.sha256(content.encode("utf-8")).hexdigest()

        # For binary content, hash directly
        return hashlib.sha256(content).hexdigest()

    async def add_item(
        self,
        host: DataStorageHost,  # noqa: ARG002
        content: Content,
        metadata: Metadata,
    ) -> ItemId:
        """
        Add a new item to storage with content hash for deduplication.

        Note: Content is not stored, only its hash for deduplication and lookup.
        """
        import json

        item_id = str(uuid.uuid4())
        content_hash = self._compute_content_hash(content)
        metadata_json = json.dumps(metadata.__dict__, default=str)
        content_type = "string" if isinstance(content, str) else "blob"

        with self._connection() as conn:
            # Store item metadata and content hash
            conn.execute(
                """
                INSERT INTO items (item_id, content_hash, content_type, metadata_json)
                VALUES (?, ?, ?, ?)
            """,
                (item_id, content_hash, content_type, metadata_json),
            )

        return item_id

    async def update_item(
        self,
        host: DataStorageHost,  # noqa: ARG002
        item_id: ItemId,
        content: Content,
    ) -> None:
        """
        Update content-derived data for an existing item.

        Only updates the content hash and type, not the content itself.
        """
        content_hash = self._compute_content_hash(content)
        content_type = "string" if isinstance(content, str) else "blob"

        with self._connection() as conn:
            # Update item with new content hash and type
            conn.execute(
                """
                UPDATE items SET content_hash = ?, content_type = ? WHERE item_id = ?
            """,
                (content_hash, content_type, item_id),
            )

    async def update_metadata(
        self,
        host: DataStorageHost,  # noqa: ARG002
        item_id: ItemId,
        metadata: Metadata,
    ) -> None:
        """Update the metadata of an existing item."""
        import json

        metadata_json = json.dumps(metadata.__dict__, default=str)

        with self._connection() as conn:
            conn.execute(
                """
                UPDATE items SET metadata_json = ? WHERE item_id = ?
            """,
                (metadata_json, item_id),
            )

    async def find_item_id(
        self,
        host: DataStorageHost,  # noqa: ARG002
        metadata: Metadata,
    ) -> ItemId | None:
        """Find an item by its metadata."""
        with self._connection() as conn:
            cursor = conn.execute("""
                SELECT item_id, metadata_json FROM items
            """)

            for row in cursor:
                import json

                stored_metadata_dict = json.loads(row["metadata_json"])
                if stored_metadata_dict.get("source_url") == metadata.source_url:
                    return str(row["item_id"])

        return None

    async def find_item(self, item_id: ItemId) -> Metadata | None:
        """Retrieve metadata for an item by its ID."""
        with self._connection() as conn:
            cursor = conn.execute(
                """
                SELECT metadata_json FROM items WHERE item_id = ?
            """,
                (item_id,),
            )

            row = cursor.fetchone()
            if row:
                import json

                from paise2.models import Metadata

                metadata_dict = json.loads(row["metadata_json"])
                # Convert dict back to Metadata object
                return Metadata(
                    **{k: v for k, v in metadata_dict.items() if v is not None}
                )

        return None

    # Note: No retrieve_content method as we're not storing content

    async def remove_item(
        self,
        host: DataStorageHost,  # noqa: ARG002
        item_id: ItemId,
    ) -> CacheId | None:
        """Remove an item from storage."""
        with self._connection() as conn:
            cursor = conn.execute(
                """
                SELECT content_hash FROM items WHERE item_id = ?
            """,
                (item_id,),
            )

            row = cursor.fetchone()
            if row:
                conn.execute(
                    """
                    DELETE FROM items WHERE item_id = ?
                """,
                    (item_id,),
                )

                # Return cache ID for cleanup
                return f"cache_{item_id}"

        return None

    async def remove_items_by_metadata(
        self,
        host: DataStorageHost,  # noqa: ARG002
        metadata: Metadata,
    ) -> list[CacheId]:
        """Remove all items matching the given metadata."""
        cache_ids = []

        with self._connection() as conn:
            cursor = conn.execute("""
                SELECT item_id, metadata_json FROM items
            """)

            to_remove = []
            for row in cursor:
                import json

                stored_metadata_dict = json.loads(row["metadata_json"])
                if stored_metadata_dict.get("source_url") == metadata.source_url:
                    to_remove.append(row["item_id"])
                    cache_ids.append(f"cache_{row['item_id']}")

            for item_id in to_remove:
                conn.execute(
                    """
                    DELETE FROM items WHERE item_id = ?
                """,
                    (item_id,),
                )

        return cache_ids

    async def remove_items_by_url(
        self, host: DataStorageHost, url: str
    ) -> list[CacheId]:
        """Remove all items associated with a given URL."""
        from paise2.models import Metadata

        metadata = Metadata(source_url=url)
        return await self.remove_items_by_metadata(host, metadata)


class SQLiteDataStorageProvider:
    """
    SQLite data storage provider.

    Creates SQLite-based data storage instances for production use.
    """

    def create_data_storage(self, configuration: Configuration) -> DataStorage:
        """Create a SQLite-based data storage instance."""
        from pathlib import Path

        # Get storage path from configuration or use default
        storage_path = configuration.get("data_storage.file_path")

        if storage_path is None:
            # Use default path
            storage_path = Path.home() / ".paise2" / "storage.db"
        else:
            storage_path = Path(storage_path).expanduser()

        return SQLiteDataStorage(storage_path)
