"""Persistent key-value store with in-memory indexing backed by LogStore.

This module provides a KVStore class that maintains an in-memory index of
key-value pairs while persisting all operations to an append-only log.
"""

from kvstore.log_store import LogStore


class KVStore:
    """Persistent key-value store with in-memory indexing.

    Maintains an in-memory dictionary index while persisting all operations
    to an append-only log via LogStore. Supports set, get, delete, and keys
    operations. Deleted keys are represented as tombstones (empty string values)
    in the log.

    Attributes:
        _log_store: LogStore instance for persistence
        _index: In-memory dictionary mapping keys to values
    """

    def __init__(self, filepath: str):
        """Initialize KVStore with the given file path.

        Creates a LogStore instance and rebuilds the in-memory index by
        replaying all records from the log. Empty string values are treated
        as tombstones that remove keys from the index.

        Args:
            filepath: Path to the log file
        """
        self._log_store = LogStore(filepath)
        self._index: dict[str, str] = {}

        # Rebuild index from log
        all_records = self._log_store.read_all()
        for key, value in all_records.items():
            if value == "":
                # Tombstone: remove key from index if present
                self._index.pop(key, None)
            else:
                # Regular record: add to index
                self._index[key] = value

    def set(self, key: str, value: str) -> None:
        """Set a key-value pair in the store.

        Appends the record to the log and updates the in-memory index.

        Args:
            key: The key string
            value: The value string
        """
        # Append to log
        self._log_store.append(key, value)

        # Update in-memory index
        self._index[key] = value

    def get(self, key: str) -> str | None:
        """Get the value for a key from the store.

        Returns the value from the in-memory index, or None if the key
        is missing or has been deleted.

        Args:
            key: The key string

        Returns:
            The value string if key exists, None otherwise
        """
        return self._index.get(key)

    def delete(self, key: str) -> None:
        """Delete a key from the store.

        Appends a tombstone record (key with empty string value) to the log
        and removes the key from the in-memory index.

        Args:
            key: The key string
        """
        # Append tombstone to log
        self._log_store.append(key, "")

        # Remove from in-memory index
        self._index.pop(key, None)

    def keys(self) -> list[str]:
        """Get all current non-deleted keys from the store.

        Returns:
            List of all keys present in the in-memory index
        """
        return list(self._index.keys())
