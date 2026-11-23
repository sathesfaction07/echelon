"""Comprehensive tests for record_codec module."""

import pytest
from kvstore.record_codec import decode, encode


class TestEncode:
    """Tests for the encode function."""

    def test_encode_normal_strings(self):
        """Test encoding normal key-value pairs."""
        result = encode("foo", "bar")
        # Expected: 4-byte length (7) + 'foo:bar' (7 bytes)
        assert result == b"\x07\x00\x00\x00foo:bar"
        assert len(result) == 11

    def test_encode_empty_key(self):
        """Test encoding with empty key."""
        result = encode("", "value")
        # ':value' is 6 bytes
        assert result == b"\x06\x00\x00\x00:value"

    def test_encode_empty_value(self):
        """Test encoding with empty value."""
        result = encode("key", "")
        # 'key:' is 4 bytes
        assert result == b"\x04\x00\x00\x00key:"

    def test_encode_both_empty(self):
        """Test encoding with both key and value empty."""
        result = encode("", "")
        # ':' is 1 byte
        assert result == b"\x01\x00\x00\x00:"

    def test_encode_value_with_colons(self):
        """Test encoding when value contains colons."""
        result = encode("key", "val:ue:with:colons")
        expected_string = "key:val:ue:with:colons"
        expected_length = len(expected_string)
        assert result[:4] == expected_length.to_bytes(4, "little")
        assert result[4:] == expected_string.encode("utf-8")

    def test_encode_special_characters(self):
        """Test encoding with special characters in key."""
        result = encode("key-with_special.chars", "value123")
        expected_string = "key-with_special.chars:value123"
        expected_length = len(expected_string)
        assert result[:4] == expected_length.to_bytes(4, "little")
        assert result[4:] == expected_string.encode("utf-8")

    def test_encode_unicode_characters(self):
        """Test encoding with Unicode characters."""
        result = encode("clé", "valeur")
        expected_string = "clé:valeur"
        expected_bytes = expected_string.encode("utf-8")
        expected_length = len(expected_bytes)
        assert result[:4] == expected_length.to_bytes(4, "little")
        assert result[4:] == expected_bytes

    def test_encode_long_strings(self):
        """Test encoding with long strings."""
        long_key = "k" * 1000
        long_value = "v" * 2000
        result = encode(long_key, long_value)
        expected_string = f"{long_key}:{long_value}"
        expected_length = len(expected_string)
        assert result[:4] == expected_length.to_bytes(4, "little")
        assert result[4:] == expected_string.encode("utf-8")


class TestDecode:
    """Tests for the decode function."""

    def test_decode_normal_strings(self):
        """Test decoding normal encoded data."""
        data = b"\x07\x00\x00\x00foo:bar"
        key, value = decode(data)
        assert key == "foo"
        assert value == "bar"

    def test_decode_empty_key(self):
        """Test decoding with empty key."""
        data = b"\x06\x00\x00\x00:value"
        key, value = decode(data)
        assert key == ""
        assert value == "value"

    def test_decode_empty_value(self):
        """Test decoding with empty value."""
        data = b"\x04\x00\x00\x00key:"
        key, value = decode(data)
        assert key == "key"
        assert value == ""

    def test_decode_both_empty(self):
        """Test decoding with both key and value empty."""
        data = b"\x01\x00\x00\x00:"
        key, value = decode(data)
        assert key == ""
        assert value == ""

    def test_decode_value_with_colons(self):
        """Test decoding when value contains colons (split on first colon only)."""
        data = b"\x16\x00\x00\x00key:val:ue:with:colons"
        key, value = decode(data)
        assert key == "key"
        assert value == "val:ue:with:colons"

    def test_decode_special_characters(self):
        """Test decoding with special characters."""
        data = encode("key-with_special.chars", "value123")
        key, value = decode(data)
        assert key == "key-with_special.chars"
        assert value == "value123"

    def test_decode_unicode_characters(self):
        """Test decoding with Unicode characters."""
        data = encode("clé", "valeur")
        key, value = decode(data)
        assert key == "clé"
        assert value == "valeur"

    def test_decode_data_too_short_for_prefix(self):
        """Test decode raises ValueError when data is shorter than 4 bytes."""
        with pytest.raises(ValueError, match="Data too short.*expected at least 4 bytes"):
            decode(b"\x01\x00\x00")

        with pytest.raises(ValueError, match="Data too short.*expected at least 4 bytes"):
            decode(b"")

        with pytest.raises(ValueError, match="Data too short.*expected at least 4 bytes"):
            decode(b"\x01")

    def test_decode_truncated_data(self):
        """Test decode raises ValueError when data is truncated."""
        # Length prefix says 10 bytes, but only 5 bytes of payload provided
        data = b"\x0a\x00\x00\x00foo:b"
        with pytest.raises(ValueError, match="Data truncated.*length prefix indicates 10 bytes"):
            decode(data)

    def test_decode_truncated_data_exact_prefix(self):
        """Test decode raises ValueError when only prefix is present."""
        # Length prefix says 5 bytes, but no payload
        data = b"\x05\x00\x00\x00"
        with pytest.raises(ValueError, match="Data truncated"):
            decode(data)

    def test_decode_invalid_utf8(self):
        """Test decode raises ValueError for invalid UTF-8 data."""
        # Length prefix says 3 bytes, followed by invalid UTF-8 sequence
        data = b"\x03\x00\x00\x00\xff\xfe\xfd"
        with pytest.raises(ValueError, match="Invalid UTF-8 data in payload"):
            decode(data)

    def test_decode_no_colon_separator(self):
        """Test decode raises ValueError when no colon separator is found."""
        # Valid UTF-8 but no colon
        data = b"\x06\x00\x00\x00foobar"
        with pytest.raises(ValueError, match="No colon separator found"):
            decode(data)

    def test_decode_key_with_colon(self):
        """Test that decode splits on FIRST colon only."""
        # Manually construct data where key would have colon if we split wrong
        # 'a:b:c:d:e' is 9 bytes
        data = b"\x09\x00\x00\x00a:b:c:d:e"
        key, value = decode(data)
        assert key == "a"
        assert value == "b:c:d:e"


class TestRoundTrip:
    """Tests for encode/decode round-trip consistency."""

    def test_roundtrip_normal(self):
        """Test that decode(encode(k, v)) == (k, v) for normal strings."""
        key, value = "foo", "bar"
        assert decode(encode(key, value)) == (key, value)

    def test_roundtrip_empty_key(self):
        """Test round-trip with empty key."""
        key, value = "", "value"
        assert decode(encode(key, value)) == (key, value)

    def test_roundtrip_empty_value(self):
        """Test round-trip with empty value."""
        key, value = "key", ""
        assert decode(encode(key, value)) == (key, value)

    def test_roundtrip_both_empty(self):
        """Test round-trip with both empty."""
        key, value = "", ""
        assert decode(encode(key, value)) == (key, value)

    def test_roundtrip_value_with_colons(self):
        """Test round-trip when value contains colons."""
        key, value = "key", "val:ue:with:colons"
        assert decode(encode(key, value)) == (key, value)

    def test_roundtrip_special_characters(self):
        """Test round-trip with special characters."""
        key, value = "key-with_special.chars!@#", "value$%^&*()"
        assert decode(encode(key, value)) == (key, value)

    def test_roundtrip_unicode(self):
        """Test round-trip with Unicode characters."""
        key, value = "键", "值"
        assert decode(encode(key, value)) == (key, value)

    def test_roundtrip_long_strings(self):
        """Test round-trip with long strings."""
        key, value = "k" * 1000, "v" * 2000
        assert decode(encode(key, value)) == (key, value)

    def test_roundtrip_newlines_and_tabs(self):
        """Test round-trip with newlines and tabs."""
        key, value = "key\nwith\nnewlines", "value\twith\ttabs"
        assert decode(encode(key, value)) == (key, value)


class TestEdgeCases:
    """Additional edge case tests."""

    def test_encode_result_structure(self):
        """Verify the exact structure of encoded output."""
        result = encode("foo", "bar")
        # First 4 bytes should be length in little-endian
        assert result[0] == 7  # Length = 7
        assert result[1] == 0
        assert result[2] == 0
        assert result[3] == 0
        # Remaining bytes should be 'foo:bar'
        assert result[4:] == b"foo:bar"

    def test_decode_with_extra_data(self):
        """Test that decode only reads the specified length."""
        # Encode 'foo:bar' (7 bytes) but append extra data
        data = b"\x07\x00\x00\x00foo:bar" + b"extra_data_ignored"
        key, value = decode(data)
        assert key == "foo"
        assert value == "bar"

    def test_zero_length_payload_no_colon(self):
        """Test decode with zero-length payload."""
        data = b"\x00\x00\x00\x00"
        with pytest.raises(ValueError, match="No colon separator found"):
            decode(data)

    def test_large_length_prefix(self):
        """Test decode with length prefix larger than available data."""
        # Length prefix says 1000000 bytes, but only 10 bytes total
        data = b"\x40\x42\x0f\x00" + b"foo:ba"
        with pytest.raises(ValueError, match="Data truncated"):
            decode(data)
