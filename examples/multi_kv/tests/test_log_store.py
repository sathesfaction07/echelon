"""Comprehensive tests for LogStore class."""

from kvstore.log_store import LogStore


class TestLogStoreBasics:
    """Basic functionality tests for LogStore."""

    def test_init_creates_new_file(self, tmp_path):
        """Test that __init__ creates a new file if it doesn't exist."""
        filepath = tmp_path / "test.log"
        assert not filepath.exists()

        store = LogStore(str(filepath))
        assert filepath.exists()
        store._file.close()

    def test_init_opens_existing_file(self, tmp_path):
        """Test that __init__ opens an existing file."""
        filepath = tmp_path / "test.log"

        # Create file first
        with open(filepath, "wb") as f:
            f.write(b"existing data")

        store = LogStore(str(filepath))
        assert filepath.exists()
        store._file.close()

    def test_append_returns_offset(self, tmp_path):
        """Test that append returns the correct file offset."""
        filepath = tmp_path / "test.log"
        store = LogStore(str(filepath))

        # First append should return offset 0
        offset1 = store.append("key1", "value1")
        assert offset1 == 0

        # Second append should return offset after first record
        offset2 = store.append("key2", "value2")
        assert offset2 > offset1
        assert offset2 == 15  # 4 bytes length + 11 bytes 'key1:value1'

        store._file.close()

    def test_append_writes_to_file(self, tmp_path):
        """Test that append actually writes data to file."""
        filepath = tmp_path / "test.log"
        store = LogStore(str(filepath))

        store.append("foo", "bar")
        store._file.close()

        # Verify file contains data
        with open(filepath, "rb") as f:
            data = f.read()
            assert len(data) > 0
            assert b"foo:bar" in data


class TestReadAll:
    """Tests for read_all method."""

    def test_read_all_empty_file(self, tmp_path):
        """Test read_all on empty file returns empty dict."""
        filepath = tmp_path / "test.log"
        store = LogStore(str(filepath))

        result = store.read_all()
        assert result == {}

        store._file.close()

    def test_read_all_single_record(self, tmp_path):
        """Test read_all with single record."""
        filepath = tmp_path / "test.log"
        store = LogStore(str(filepath))

        store.append("key1", "value1")
        result = store.read_all()

        assert result == {"key1": "value1"}

        store._file.close()

    def test_read_all_multiple_records(self, tmp_path):
        """Test read_all with multiple different keys."""
        filepath = tmp_path / "test.log"
        store = LogStore(str(filepath))

        store.append("key1", "value1")
        store.append("key2", "value2")
        store.append("key3", "value3")

        result = store.read_all()

        assert result == {"key1": "value1", "key2": "value2", "key3": "value3"}

        store._file.close()

    def test_read_all_overwrites_duplicate_keys(self, tmp_path):
        """Test that later records overwrite earlier ones for same key."""
        filepath = tmp_path / "test.log"
        store = LogStore(str(filepath))

        store.append("key1", "value1")
        store.append("key2", "value2")
        store.append("key1", "value1_updated")
        store.append("key2", "value2_updated")
        store.append("key1", "value1_final")

        result = store.read_all()

        # Should have latest values only
        assert result == {"key1": "value1_final", "key2": "value2_updated"}

        store._file.close()

    def test_read_all_with_empty_strings(self, tmp_path):
        """Test read_all with empty keys and values."""
        filepath = tmp_path / "test.log"
        store = LogStore(str(filepath))

        store.append("", "value")
        store.append("key", "")
        store.append("", "")

        result = store.read_all()

        # Empty key should be overwritten by later empty key
        assert result == {"": "", "key": ""}

        store._file.close()

    def test_read_all_with_special_characters(self, tmp_path):
        """Test read_all with special characters in keys and values."""
        filepath = tmp_path / "test.log"
        store = LogStore(str(filepath))

        store.append("key-with_special.chars", "value!@#$%")
        store.append("key", "value:with:colons")  # Colons in value are OK
        store.append("key\nwith\nnewlines", "value\twith\ttabs")

        result = store.read_all()

        assert result == {
            "key-with_special.chars": "value!@#$%",
            "key": "value:with:colons",
            "key\nwith\nnewlines": "value\twith\ttabs",
        }

        store._file.close()


class TestPersistence:
    """Tests for file persistence across multiple LogStore instances."""

    def test_persistence_single_write_single_read(self, tmp_path):
        """Test that data persists when creating new LogStore instance."""
        filepath = tmp_path / "test.log"

        # Write with first instance
        with LogStore(str(filepath)) as store1:
            store1.append("key1", "value1")
            store1.append("key2", "value2")

        # Read with second instance
        with LogStore(str(filepath)) as store2:
            result = store2.read_all()
            assert result == {"key1": "value1", "key2": "value2"}

    def test_persistence_multiple_appends(self, tmp_path):
        """Test that appends persist across multiple instances."""
        filepath = tmp_path / "test.log"

        # First instance writes some data
        with LogStore(str(filepath)) as store1:
            store1.append("key1", "value1")

        # Second instance appends more data
        with LogStore(str(filepath)) as store2:
            store2.append("key2", "value2")

        # Third instance reads all
        with LogStore(str(filepath)) as store3:
            result = store3.read_all()
            assert result == {"key1": "value1", "key2": "value2"}

    def test_persistence_overwrite_across_instances(self, tmp_path):
        """Test that key overwrites work across instances."""
        filepath = tmp_path / "test.log"

        # First instance writes initial value
        with LogStore(str(filepath)) as store1:
            store1.append("key1", "value1")

        # Second instance overwrites with new value
        with LogStore(str(filepath)) as store2:
            store2.append("key1", "value1_updated")

        # Third instance reads and should get latest value
        with LogStore(str(filepath)) as store3:
            result = store3.read_all()
            assert result == {"key1": "value1_updated"}

    def test_persistence_many_records(self, tmp_path):
        """Test persistence with many records."""
        filepath = tmp_path / "test.log"

        # Write many records
        with LogStore(str(filepath)) as store1:
            for i in range(100):
                store1.append(f"key{i}", f"value{i}")

        # Read back
        with LogStore(str(filepath)) as store2:
            result = store2.read_all()
            assert len(result) == 100
            for i in range(100):
                assert result[f"key{i}"] == f"value{i}"


class TestContextManager:
    """Tests for context manager protocol."""

    def test_context_manager_basic(self, tmp_path):
        """Test that LogStore works as context manager."""
        filepath = tmp_path / "test.log"

        with LogStore(str(filepath)) as store:
            store.append("key1", "value1")
            assert store._file is not None
            assert not store._file.closed

        # File should be closed after exiting context
        assert store._file.closed

    def test_context_manager_closes_on_exception(self, tmp_path):
        """Test that file is closed even when exception occurs."""
        filepath = tmp_path / "test.log"

        try:
            with LogStore(str(filepath)) as store:
                store.append("key1", "value1")
                raise ValueError("Test exception")
        except ValueError:
            pass

        # File should still be closed
        assert store._file.closed

    def test_context_manager_enter_returns_self(self, tmp_path):
        """Test that __enter__ returns self."""
        filepath = tmp_path / "test.log"

        store = LogStore(str(filepath))
        result = store.__enter__()
        assert result is store
        store.__exit__(None, None, None)

    def test_manual_close_without_context_manager(self, tmp_path):
        """Test that file can be manually closed without context manager."""
        filepath = tmp_path / "test.log"

        store = LogStore(str(filepath))
        store.append("key1", "value1")
        assert not store._file.closed

        store._file.close()
        assert store._file.closed


class TestAppendOffsets:
    """Tests for append offset tracking."""

    def test_append_offset_sequence(self, tmp_path):
        """Test that append offsets form a proper sequence."""
        filepath = tmp_path / "test.log"
        store = LogStore(str(filepath))

        offsets = []
        offsets.append(store.append("a", "b"))
        offsets.append(store.append("c", "d"))
        offsets.append(store.append("e", "f"))

        # First offset should be 0
        assert offsets[0] == 0

        # Each subsequent offset should be greater
        assert offsets[1] > offsets[0]
        assert offsets[2] > offsets[1]

        store._file.close()

    def test_append_offset_after_read_all(self, tmp_path):
        """Test that append works correctly after read_all."""
        filepath = tmp_path / "test.log"
        store = LogStore(str(filepath))

        # Append some data
        store.append("key1", "value1")
        store.append("key2", "value2")

        # Read all (which seeks to start)
        result = store.read_all()
        assert len(result) == 2

        # Append more data - should append to end, not overwrite
        offset = store.append("key3", "value3")
        assert offset > 0

        # Read again to verify all data is there
        result = store.read_all()
        assert result == {"key1": "value1", "key2": "value2", "key3": "value3"}

        store._file.close()


class TestEdgeCases:
    """Edge case tests."""

    def test_unicode_keys_and_values(self, tmp_path):
        """Test with Unicode characters."""
        filepath = tmp_path / "test.log"

        with LogStore(str(filepath)) as store:
            store.append("键", "值")
            store.append("clé", "valeur")

            result = store.read_all()
            assert result == {"键": "值", "clé": "valeur"}

    def test_long_keys_and_values(self, tmp_path):
        """Test with very long keys and values."""
        filepath = tmp_path / "test.log"

        long_key = "k" * 1000
        long_value = "v" * 2000

        with LogStore(str(filepath)) as store:
            store.append(long_key, long_value)

            result = store.read_all()
            assert result == {long_key: long_value}

    def test_many_overwrites_same_key(self, tmp_path):
        """Test many overwrites of the same key."""
        filepath = tmp_path / "test.log"

        with LogStore(str(filepath)) as store:
            for i in range(100):
                store.append("key", f"value{i}")

            result = store.read_all()
            assert result == {"key": "value99"}

    def test_interleaved_read_and_write(self, tmp_path):
        """Test interleaving read_all and append operations."""
        filepath = tmp_path / "test.log"

        with LogStore(str(filepath)) as store:
            store.append("key1", "value1")

            result1 = store.read_all()
            assert result1 == {"key1": "value1"}

            store.append("key2", "value2")

            result2 = store.read_all()
            assert result2 == {"key1": "value1", "key2": "value2"}

            store.append("key1", "value1_updated")

            result3 = store.read_all()
            assert result3 == {"key1": "value1_updated", "key2": "value2"}
