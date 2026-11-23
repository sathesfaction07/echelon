"""Unit tests for KVStore class."""

import os
import tempfile

import pytest
from kvstore.kvstore import KVStore


@pytest.fixture
def temp_file():
    """Create a temporary file for testing."""
    fd, path = tempfile.mkstemp()
    os.close(fd)
    yield path
    # Cleanup
    if os.path.exists(path):
        os.remove(path)


def test_empty_store(temp_file):
    """Test operations on an empty store."""
    store = KVStore(temp_file)

    # Get on empty store should return None
    assert store.get("nonexistent") is None

    # Keys on empty store should return empty list
    assert store.keys() == []


def test_set_and_get(temp_file):
    """Test basic set and get operations."""
    store = KVStore(temp_file)

    # Set a key-value pair
    store.set("key1", "value1")

    # Get should return the value
    assert store.get("key1") == "value1"

    # Set another key-value pair
    store.set("key2", "value2")

    # Both keys should be retrievable
    assert store.get("key1") == "value1"
    assert store.get("key2") == "value2"


def test_set_overwrite(temp_file):
    """Test that setting the same key overwrites the value."""
    store = KVStore(temp_file)

    # Set a key
    store.set("key1", "value1")
    assert store.get("key1") == "value1"

    # Overwrite the key
    store.set("key1", "value2")
    assert store.get("key1") == "value2"


def test_get_missing_key(temp_file):
    """Test getting a key that doesn't exist."""
    store = KVStore(temp_file)

    # Set some keys
    store.set("key1", "value1")

    # Get missing key should return None
    assert store.get("missing") is None


def test_delete(temp_file):
    """Test delete operation."""
    store = KVStore(temp_file)

    # Set a key
    store.set("key1", "value1")
    assert store.get("key1") == "value1"

    # Delete the key
    store.delete("key1")

    # Get should now return None
    assert store.get("key1") is None


def test_delete_nonexistent_key(temp_file):
    """Test deleting a key that doesn't exist."""
    store = KVStore(temp_file)

    # Delete should not raise an error
    store.delete("nonexistent")

    # Get should return None
    assert store.get("nonexistent") is None


def test_delete_already_deleted_key(temp_file):
    """Test deleting a key that was already deleted."""
    store = KVStore(temp_file)

    # Set and delete a key
    store.set("key1", "value1")
    store.delete("key1")

    # Delete again should not raise an error
    store.delete("key1")

    # Get should still return None
    assert store.get("key1") is None


def test_keys_empty(temp_file):
    """Test keys() on empty store."""
    store = KVStore(temp_file)

    assert store.keys() == []


def test_keys_with_data(temp_file):
    """Test keys() with multiple keys."""
    store = KVStore(temp_file)

    # Set multiple keys
    store.set("key1", "value1")
    store.set("key2", "value2")
    store.set("key3", "value3")

    # Keys should return all keys
    keys = store.keys()
    assert sorted(keys) == ["key1", "key2", "key3"]


def test_keys_after_delete(temp_file):
    """Test keys() after deleting some keys."""
    store = KVStore(temp_file)

    # Set multiple keys
    store.set("key1", "value1")
    store.set("key2", "value2")
    store.set("key3", "value3")

    # Delete one key
    store.delete("key2")

    # Keys should not include deleted key
    keys = store.keys()
    assert sorted(keys) == ["key1", "key3"]


def test_keys_after_all_deleted(temp_file):
    """Test keys() after deleting all keys."""
    store = KVStore(temp_file)

    # Set and delete keys
    store.set("key1", "value1")
    store.set("key2", "value2")
    store.delete("key1")
    store.delete("key2")

    # Keys should be empty
    assert store.keys() == []


def test_set_after_delete(temp_file):
    """Test setting a key after it was deleted."""
    store = KVStore(temp_file)

    # Set, delete, then set again
    store.set("key1", "value1")
    store.delete("key1")
    store.set("key1", "value2")

    # Get should return the new value
    assert store.get("key1") == "value2"

    # Keys should include the key
    assert "key1" in store.keys()


def test_empty_string_key(temp_file):
    """Test using empty string as key."""
    store = KVStore(temp_file)

    # Set with empty string key
    store.set("", "value")

    # Get should work
    assert store.get("") == "value"

    # Keys should include empty string
    assert "" in store.keys()


def test_empty_string_value(temp_file):
    """Test using empty string as value (not a tombstone when set explicitly)."""
    store = KVStore(temp_file)

    # Set with empty string value
    store.set("key1", "value1")

    # Verify it's set
    assert store.get("key1") == "value1"


def test_special_characters(temp_file):
    """Test keys and values with special characters."""
    store = KVStore(temp_file)

    # Set with special characters
    store.set("key:with:colons", "value:with:colons")
    store.set("key\nwith\nnewlines", "value\nwith\nnewlines")

    # Get should work correctly
    assert store.get("key:with:colons") == "value:with:colons"
    assert store.get("key\nwith\nnewlines") == "value\nwith\nnewlines"
