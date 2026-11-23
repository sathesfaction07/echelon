"""Integration tests for KVStore persistence and recovery."""

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


def test_persistence_and_recovery(temp_file):
    """Test that KVStore correctly persists and recovers data.

    Creates a KVStore, sets multiple keys, deletes at least one key,
    closes/reopens the store, and verifies the index is correctly rebuilt
    with the deleted key absent and non-deleted keys present.
    """
    # Create initial store and populate it
    store1 = KVStore(temp_file)

    # Set multiple keys
    store1.set("key1", "value1")
    store1.set("key2", "value2")
    store1.set("key3", "value3")
    store1.set("key4", "value4")

    # Verify all keys are present
    assert store1.get("key1") == "value1"
    assert store1.get("key2") == "value2"
    assert store1.get("key3") == "value3"
    assert store1.get("key4") == "value4"
    assert sorted(store1.keys()) == ["key1", "key2", "key3", "key4"]

    # Delete some keys
    store1.delete("key2")
    store1.delete("key4")

    # Verify deleted keys are gone
    assert store1.get("key2") is None
    assert store1.get("key4") is None
    assert sorted(store1.keys()) == ["key1", "key3"]

    # Close the store (Python will handle cleanup, but we're done with store1)
    del store1

    # Reopen the store with the same filepath
    store2 = KVStore(temp_file)

    # Verify non-deleted keys are present
    assert store2.get("key1") == "value1"
    assert store2.get("key3") == "value3"

    # Verify deleted keys are absent
    assert store2.get("key2") is None
    assert store2.get("key4") is None

    # Verify keys() returns only non-deleted keys
    assert sorted(store2.keys()) == ["key1", "key3"]


def test_recovery_with_overwrites(temp_file):
    """Test recovery when keys have been overwritten."""
    # Create initial store
    store1 = KVStore(temp_file)

    # Set and overwrite keys
    store1.set("key1", "value1")
    store1.set("key1", "value1_updated")
    store1.set("key2", "value2")
    store1.set("key2", "value2_updated")

    # Verify current values
    assert store1.get("key1") == "value1_updated"
    assert store1.get("key2") == "value2_updated"

    del store1

    # Reopen and verify latest values are recovered
    store2 = KVStore(temp_file)
    assert store2.get("key1") == "value1_updated"
    assert store2.get("key2") == "value2_updated"


def test_recovery_with_delete_and_reset(temp_file):
    """Test recovery when a key is deleted and then set again."""
    # Create initial store
    store1 = KVStore(temp_file)

    # Set, delete, then set again
    store1.set("key1", "value1")
    store1.delete("key1")
    store1.set("key1", "value1_new")

    # Verify key is present with new value
    assert store1.get("key1") == "value1_new"
    assert "key1" in store1.keys()

    del store1

    # Reopen and verify key is present with new value
    store2 = KVStore(temp_file)
    assert store2.get("key1") == "value1_new"
    assert "key1" in store2.keys()


def test_recovery_from_empty_log(temp_file):
    """Test recovery from an empty log file."""
    # Create store with empty log
    store1 = KVStore(temp_file)

    # Verify it's empty
    assert store1.keys() == []
    assert store1.get("any_key") is None

    del store1

    # Reopen and verify still empty
    store2 = KVStore(temp_file)
    assert store2.keys() == []
    assert store2.get("any_key") is None


def test_recovery_with_only_tombstones(temp_file):
    """Test recovery when log contains only tombstones."""
    # Create initial store
    store1 = KVStore(temp_file)

    # Set and delete all keys
    store1.set("key1", "value1")
    store1.set("key2", "value2")
    store1.delete("key1")
    store1.delete("key2")

    # Verify all keys are deleted
    assert store1.keys() == []

    del store1

    # Reopen and verify all keys are still deleted
    store2 = KVStore(temp_file)
    assert store2.keys() == []
    assert store2.get("key1") is None
    assert store2.get("key2") is None


def test_multiple_recovery_cycles(temp_file):
    """Test multiple open/close/reopen cycles."""
    # First cycle: create and populate
    store1 = KVStore(temp_file)
    store1.set("key1", "value1")
    store1.set("key2", "value2")
    del store1

    # Second cycle: add more data
    store2 = KVStore(temp_file)
    assert store2.get("key1") == "value1"
    store2.set("key3", "value3")
    store2.delete("key1")
    del store2

    # Third cycle: verify state
    store3 = KVStore(temp_file)
    assert store3.get("key1") is None
    assert store3.get("key2") == "value2"
    assert store3.get("key3") == "value3"
    assert sorted(store3.keys()) == ["key2", "key3"]
