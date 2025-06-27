"""ABOUTME: State storage provider implementations for plugin state persistence.
ABOUTME: Provides memory and file-based storage with automatic partitioning."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING, Any

from paise2.constants import get_default_state_db_path

if TYPE_CHECKING:
    from paise2.config.models import Configuration
    from paise2.plugins.core.interfaces import StateStorage


class MemoryStateStorage:
    """
    In-memory state storage implementation.

    Provides state storage for development and testing.
    Data is lost when the process exits.
    """

    def __init__(self) -> None:
        """Initialize memory storage with empty state dictionary."""
        self._state: dict[str, dict[str, tuple[Any, int]]] = {}

    def store(self, partition_key: str, key: str, value: Any, version: int = 1) -> None:
        """Store a value with versioning support."""
        if partition_key not in self._state:
            self._state[partition_key] = {}

        self._state[partition_key][key] = (value, version)

    def get(self, partition_key: str, key: str, default: Any = None) -> Any:
        """Retrieve a stored value."""
        if partition_key in self._state and key in self._state[partition_key]:
            value, _ = self._state[partition_key][key]
            return value
        return default

    def get_versioned_state(
        self, partition_key: str, older_than_version: int
    ) -> list[tuple[str, Any, int]]:
        """Get all state entries older than a specific version."""
        if partition_key not in self._state:
            return []

        result = []
        for key, (value, version) in self._state[partition_key].items():
            if version < older_than_version:
                result.append((key, value, version))

        return result

    def get_all_keys_with_value(self, partition_key: str, value: Any) -> list[str]:
        """Find all keys that have a specific value."""
        if partition_key not in self._state:
            return []

        result = []
        for key, (stored_value, _) in self._state[partition_key].items():
            if stored_value == value:
                result.append(key)

        return result


class MemoryStateStorageProvider:
    """
    Memory state storage provider.

    Creates in-memory state storage instances for development and testing.
    """

    def create_state_storage(self, configuration: Configuration) -> StateStorage:  # noqa: ARG002
        """Create a memory-based state storage instance."""
        return MemoryStateStorage()


class FileStateStorage:
    """
    File-based state storage implementation using SQLite.

    Provides persistent state storage with automatic partitioning and versioning.
    Uses SQLite for reliable transactions and data integrity.
    """

    def __init__(self, db_path: Path | None) -> None:
        self.db_path = db_path
        self._init_database()

    def _connection(self) -> sqlite3.Connection:
        if self.db_path is not None:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(self.db_path or ":memory:")

    def _init_database(self) -> None:
        """Initialize the SQLite database schema."""
        # Ensure parent directory exists
        with self._connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS state_entries (
                    partition_key TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    version INTEGER NOT NULL DEFAULT 1,
                    PRIMARY KEY (partition_key, key)
                )
            """)

            # Create index for versioning queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_partition_version
                ON state_entries (partition_key, version)
            """)

            # Create index for value queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_partition_value
                ON state_entries (partition_key, value)
            """)

            conn.commit()

    def store(self, partition_key: str, key: str, value: Any, version: int = 1) -> None:
        """Store a value with versioning support."""
        # Serialize value to JSON for storage
        value_json = json.dumps(value)

        with self._connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO state_entries
                (partition_key, key, value, version)
                VALUES (?, ?, ?, ?)
            """,
                (partition_key, key, value_json, version),
            )
            conn.commit()

    def get(self, partition_key: str, key: str, default: Any = None) -> Any:
        """Retrieve a stored value."""
        with self._connection() as conn:
            cursor = conn.execute(
                """
                SELECT value FROM state_entries
                WHERE partition_key = ? AND key = ?
            """,
                (partition_key, key),
            )

            result = cursor.fetchone()
            if result:
                # Deserialize value from JSON
                return json.loads(result[0])
            return default

    def get_versioned_state(
        self, partition_key: str, older_than_version: int
    ) -> list[tuple[str, Any, int]]:
        """Get all state entries older than a specific version."""
        with self._connection() as conn:
            cursor = conn.execute(
                """
                SELECT key, value, version FROM state_entries
                WHERE partition_key = ? AND version < ?
                ORDER BY version ASC
            """,
                (partition_key, older_than_version),
            )

            result = []
            for row in cursor.fetchall():
                key, value_json, version = row
                value = json.loads(value_json)
                result.append((key, value, version))

            return result

    def get_all_keys_with_value(self, partition_key: str, value: Any) -> list[str]:
        """Find all keys that have a specific value."""
        value_json = json.dumps(value)

        with self._connection() as conn:
            cursor = conn.execute(
                """
                SELECT key FROM state_entries
                WHERE partition_key = ? AND value = ?
            """,
                (partition_key, value_json),
            )

            return [row[0] for row in cursor.fetchall()]


class FileStateStorageProvider:
    """
    File-based state storage provider.

    Creates SQLite-based state storage instances for production use.
    """

    def create_state_storage(self, configuration: Configuration) -> StateStorage:
        """Create a file-based state storage instance."""
        # If a specific path is provided in configuration, use it exactly
        path_from_config = configuration.get(
            "state_storage.file_path", get_default_state_db_path()
        )
        if path_from_config == ":memory:":
            return FileStateStorage(None)

        db_path = Path(path_from_config).expanduser().resolve()
        # Ensure parent directory exists
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return FileStateStorage(db_path)
