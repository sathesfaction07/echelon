"""Append-only log-based key-value store.

This module provides a LogStore class that persists key-value pairs to an
append-only binary file using the record_codec format.
"""

from typing import BinaryIO

from kvstore import record_codec


class LogStore:
    """Append-only log-based key-value store.

    Stores key-value pairs in an append-only binary file. Each record is
    encoded using record_codec. When reading, later records for the same
    key overwrite earlier ones.

    Attributes:
        filepath: Path to the log file
        _file: Binary file handle opened in append+read mode
    """

    def __init__(self, filepath: str):
        """Initialize LogStore with the given file path.

        Opens or creates the file in binary append+read mode ('ab+').

        Args:
            filepath: Path to the log file
        """
        self.filepath = filepath
        self._file: BinaryIO = open(filepath, "ab+")

    def append(self, key: str, value: str) -> int:
        """Append a key-value pair to the log.

        Encodes the key-value pair using record_codec.encode and writes
        it to the file. Flushes to ensure data is written to disk.

        Args:
            key: The key string
            value: The value string

        Returns:
            The file offset before the write (position where record starts)
        """
        # Get current position before write
        offset = self._file.tell()

        # Encode the record
        encoded = record_codec.encode(key, value)

        # Write to file
        self._file.write(encoded)

        # Flush to ensure data is written
        self._file.flush()

        return offset

    def read_all(self) -> dict[str, str]:
        """Read all records and build index with latest value per key.

        Seeks to the start of the file and reads all records sequentially.
        When the same key appears multiple times, later records overwrite
        earlier ones in the returned dictionary.

        Returns:
            Dictionary mapping each key to its most recent value
        """
        # Seek to start of file
        self._file.seek(0)

        # Build dictionary with latest value per key
        result = {}

        while True:
            # Try to read the 4-byte length prefix
            length_bytes = self._file.read(4)

            # If we can't read 4 bytes, we've reached EOF
            if len(length_bytes) < 4:
                break

            # Decode the length
            import struct

            length = struct.unpack("<I", length_bytes)[0]

            # Read the payload
            payload_bytes = self._file.read(length)

            # If we can't read the full payload, the file is corrupted
            if len(payload_bytes) < length:
                break

            # Reconstruct the full record (length prefix + payload)
            full_record = length_bytes + payload_bytes

            # Decode the record
            key, value = record_codec.decode(full_record)

            # Store in dictionary (overwrites earlier values for same key)
            result[key] = value

        return result

    def __enter__(self):
        """Enter context manager.

        Returns:
            self for use in 'with' statement
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager and close file handle.

        Args:
            exc_type: Exception type if an exception occurred
            exc_val: Exception value if an exception occurred
            exc_tb: Exception traceback if an exception occurred

        Returns:
            None (does not suppress exceptions)
        """
        self._file.close()
        return None
