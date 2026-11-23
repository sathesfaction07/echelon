"""Binary serialization codec for key-value string pairs.

This module provides functions to encode and decode key-value pairs into a
length-prefixed binary format.
"""

import struct


def encode(key: str, value: str) -> bytes:
    """Encode a key-value pair into length-prefixed binary format.

    The format consists of:
    - 4-byte little-endian unsigned integer: length of 'key:value' string
    - UTF-8 encoded 'key:value' string

    Args:
        key: The key string
        value: The value string

    Returns:
        Encoded bytes with length prefix and UTF-8 encoded 'key:value' string

    Example:
        >>> encode('foo', 'bar')
        b'\\x07\\x00\\x00\\x00foo:bar'
    """
    # Construct the key:value string
    kv_string = f"{key}:{value}"

    # Encode to UTF-8
    kv_bytes = kv_string.encode("utf-8")

    # Get the length
    length = len(kv_bytes)

    # Pack the length as 4-byte little-endian unsigned integer
    length_prefix = struct.pack("<I", length)

    # Concatenate and return
    return length_prefix + kv_bytes


def decode(data: bytes) -> tuple[str, str]:
    """Decode length-prefixed binary data back into a key-value pair.

    Reads the 4-byte length prefix, extracts exactly that many bytes,
    decodes as UTF-8, and splits on the first colon character.

    Args:
        data: Encoded bytes with length prefix

    Returns:
        Tuple of (key, value) strings

    Raises:
        ValueError: If data is shorter than 4 bytes, if data is truncated
                   (fewer bytes than length prefix indicates), if payload
                   is not valid UTF-8, or if no colon separator is found

    Example:
        >>> decode(b'\\x07\\x00\\x00\\x00foo:bar')
        ('foo', 'bar')
    """
    # Check if we have at least 4 bytes for the length prefix
    if len(data) < 4:
        raise ValueError(
            f"Data too short: expected at least 4 bytes for length prefix, got {len(data)} bytes"
        )

    # Unpack the length prefix (4-byte little-endian unsigned integer)
    length = struct.unpack("<I", data[:4])[0]

    # Check if we have enough bytes for the payload
    if len(data) < 4 + length:
        raise ValueError(
            f"Data truncated: length prefix indicates {length} bytes, "
            f"but only {len(data) - 4} bytes available"
        )

    # Extract the payload
    payload_bytes = data[4 : 4 + length]

    # Decode from UTF-8
    try:
        payload_string = payload_bytes.decode("utf-8")
    except UnicodeDecodeError as e:
        raise ValueError(f"Invalid UTF-8 data in payload: {e}")

    # Split on the first colon
    if ":" not in payload_string:
        raise ValueError(f"No colon separator found in decoded string: {repr(payload_string)}")

    # Split on first colon only
    key, _, value = payload_string.partition(":")

    return (key, value)
