"""Comprehensive test suite for semver.py module."""

import pytest
from semver import compare, parse


class TestParse:
    """Tests for the parse() function."""

    def test_parse_simple_version(self):
        """Test parsing a simple version without prerelease or build."""
        result = parse("1.2.3")
        assert result == {"major": 1, "minor": 2, "patch": 3, "prerelease": [], "build": ""}

    def test_parse_with_prerelease_and_build(self):
        """Test parsing version with prerelease and build metadata."""
        result = parse("1.2.3-alpha.1+build.123")
        assert result == {
            "major": 1,
            "minor": 2,
            "patch": 3,
            "prerelease": ["alpha", "1"],
            "build": "build.123",
        }

    def test_parse_with_prerelease_only(self):
        """Test parsing version with prerelease but no build."""
        result = parse("2.0.0-rc.1")
        assert result == {
            "major": 2,
            "minor": 0,
            "patch": 0,
            "prerelease": ["rc", "1"],
            "build": "",
        }

    def test_parse_with_build_only(self):
        """Test parsing version with build but no prerelease."""
        result = parse("1.0.0+20130313144700")
        assert result == {
            "major": 1,
            "minor": 0,
            "patch": 0,
            "prerelease": [],
            "build": "20130313144700",
        }

    def test_parse_complex_prerelease(self):
        """Test parsing version with complex prerelease identifiers."""
        result = parse("1.0.0-alpha.beta.1")
        assert result["prerelease"] == ["alpha", "beta", "1"]

    def test_parse_numeric_prerelease(self):
        """Test parsing version with numeric prerelease."""
        result = parse("1.0.0-1")
        assert result["prerelease"] == ["1"]

    def test_parse_zero_version(self):
        """Test parsing version with zeros."""
        result = parse("0.0.0")
        assert result == {"major": 0, "minor": 0, "patch": 0, "prerelease": [], "build": ""}

    def test_parse_large_numbers(self):
        """Test parsing version with large version numbers."""
        result = parse("999.888.777")
        assert result["major"] == 999
        assert result["minor"] == 888
        assert result["patch"] == 777

    def test_parse_prerelease_with_hyphens(self):
        """Test parsing prerelease with hyphens."""
        result = parse("1.0.0-alpha-beta")
        assert result["prerelease"] == ["alpha-beta"]

    def test_parse_build_with_dots_and_hyphens(self):
        """Test parsing build metadata with dots and hyphens."""
        result = parse("1.0.0+build.1-aef.1-its-okay")
        assert result["build"] == "build.1-aef.1-its-okay"


class TestParseInvalid:
    """Tests for invalid input to parse()."""

    def test_parse_non_numeric_major(self):
        """Test that non-numeric major version raises ValueError."""
        with pytest.raises(ValueError):
            parse("x.2.3")

    def test_parse_non_numeric_minor(self):
        """Test that non-numeric minor version raises ValueError."""
        with pytest.raises(ValueError):
            parse("1.x.3")

    def test_parse_non_numeric_patch(self):
        """Test that non-numeric patch version raises ValueError."""
        with pytest.raises(ValueError):
            parse("1.2.x")

    def test_parse_missing_patch(self):
        """Test that missing patch version raises ValueError."""
        with pytest.raises(ValueError):
            parse("1.2")

    def test_parse_missing_minor_and_patch(self):
        """Test that missing minor and patch raises ValueError."""
        with pytest.raises(ValueError):
            parse("1")

    def test_parse_empty_string(self):
        """Test that empty string raises ValueError."""
        with pytest.raises(ValueError):
            parse("")

    def test_parse_leading_zeros_major(self):
        """Test that leading zeros in major version are invalid."""
        with pytest.raises(ValueError):
            parse("01.2.3")

    def test_parse_leading_zeros_minor(self):
        """Test that leading zeros in minor version are invalid."""
        with pytest.raises(ValueError):
            parse("1.02.3")

    def test_parse_leading_zeros_patch(self):
        """Test that leading zeros in patch version are invalid."""
        with pytest.raises(ValueError):
            parse("1.2.03")

    def test_parse_invalid_characters(self):
        """Test that invalid characters raise ValueError."""
        with pytest.raises(ValueError):
            parse("1.2.3-alpha@beta")

    def test_parse_trailing_dot(self):
        """Test that trailing dot raises ValueError."""
        with pytest.raises(ValueError):
            parse("1.2.3.")

    def test_parse_leading_dot(self):
        """Test that leading dot raises ValueError."""
        with pytest.raises(ValueError):
            parse(".1.2.3")

    def test_parse_extra_dots(self):
        """Test that extra dots raise ValueError."""
        with pytest.raises(ValueError):
            parse("1.2.3.4")

    def test_parse_empty_prerelease_identifier(self):
        """Test that empty prerelease identifier raises ValueError."""
        with pytest.raises(ValueError):
            parse("1.2.3-alpha..beta")

    def test_parse_prerelease_leading_zero(self):
        """Test that numeric prerelease with leading zero is invalid."""
        with pytest.raises(ValueError):
            parse("1.2.3-01")


class TestCompare:
    """Tests for the compare() function."""

    def test_compare_major_difference(self):
        """Test comparison with different major versions."""
        assert compare("1.0.0", "2.0.0") == -1
        assert compare("2.0.0", "1.0.0") == 1

    def test_compare_minor_difference(self):
        """Test comparison with different minor versions."""
        assert compare("1.1.0", "1.2.0") == -1
        assert compare("1.2.0", "1.1.0") == 1

    def test_compare_patch_difference(self):
        """Test comparison with different patch versions."""
        assert compare("1.0.1", "1.0.2") == -1
        assert compare("1.0.2", "1.0.1") == 1

    def test_compare_equal_versions(self):
        """Test comparison of equal versions."""
        assert compare("1.0.0", "1.0.0") == 0
        assert compare("1.2.3", "1.2.3") == 0

    def test_compare_prerelease_vs_no_prerelease(self):
        """Test that version without prerelease > version with prerelease."""
        assert compare("1.0.0", "1.0.0-alpha") == 1
        assert compare("1.0.0-alpha", "1.0.0") == -1

    def test_compare_prerelease_length(self):
        """Test that fewer prerelease fields < more fields."""
        assert compare("1.0.0-alpha", "1.0.0-alpha.1") == -1
        assert compare("1.0.0-alpha.1", "1.0.0-alpha") == 1

    def test_compare_numeric_vs_alphanumeric_prerelease(self):
        """Test that numeric prerelease < alphanumeric prerelease."""
        assert compare("1.0.0-alpha.1", "1.0.0-alpha.beta") == -1
        assert compare("1.0.0-alpha.beta", "1.0.0-alpha.1") == 1

    def test_compare_numeric_prerelease(self):
        """Test numeric comparison of prerelease identifiers."""
        assert compare("1.0.0-1", "1.0.0-2") == -1
        assert compare("1.0.0-2", "1.0.0-1") == 1
        assert compare("1.0.0-10", "1.0.0-2") == 1  # 10 > 2 numerically

    def test_compare_alphanumeric_prerelease(self):
        """Test lexical comparison of alphanumeric prerelease."""
        assert compare("1.0.0-alpha", "1.0.0-beta") == -1
        assert compare("1.0.0-beta", "1.0.0-alpha") == 1

    def test_compare_build_metadata_ignored(self):
        """Test that build metadata is ignored in comparison."""
        assert compare("1.0.0+build1", "1.0.0+build2") == 0
        assert compare("1.0.0-alpha+build1", "1.0.0-alpha+build2") == 0

    def test_compare_complex_prerelease(self):
        """Test comparison with complex prerelease identifiers."""
        assert compare("1.0.0-alpha.1", "1.0.0-alpha.2") == -1
        assert compare("1.0.0-alpha.beta", "1.0.0-beta") == -1
        assert compare("1.0.0-beta.2", "1.0.0-beta.11") == -1

    def test_compare_equal_with_prerelease(self):
        """Test equal versions with prerelease."""
        assert compare("1.0.0-alpha", "1.0.0-alpha") == 0
        assert compare("1.0.0-alpha.1", "1.0.0-alpha.1") == 0

    def test_compare_semver_spec_examples(self):
        """Test examples from SemVer 2.0.0 specification."""
        # From spec: precedence example
        versions = [
            "1.0.0-alpha",
            "1.0.0-alpha.1",
            "1.0.0-alpha.beta",
            "1.0.0-beta",
            "1.0.0-beta.2",
            "1.0.0-beta.11",
            "1.0.0-rc.1",
            "1.0.0",
        ]

        for i in range(len(versions) - 1):
            assert compare(versions[i], versions[i + 1]) == -1, (
                f"{versions[i]} should be < {versions[i + 1]}"
            )

    def test_compare_zero_versions(self):
        """Test comparison with zero versions."""
        assert compare("0.0.0", "0.0.1") == -1
        assert compare("0.1.0", "0.0.1") == 1

    def test_compare_mixed_numeric_alphanumeric(self):
        """Test comparison with mixed numeric and alphanumeric identifiers."""
        assert compare("1.0.0-1.alpha", "1.0.0-1.beta") == -1
        assert compare("1.0.0-1.alpha", "1.0.0-2.alpha") == -1
        assert compare("1.0.0-alpha.1", "1.0.0-alpha.2") == -1


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_single_digit_versions(self):
        """Test single digit versions."""
        result = parse("0.0.0")
        assert result["major"] == 0
        assert result["minor"] == 0
        assert result["patch"] == 0

    def test_very_long_prerelease(self):
        """Test version with many prerelease identifiers."""
        result = parse("1.0.0-a.b.c.d.e.f.g")
        assert len(result["prerelease"]) == 7

    def test_prerelease_with_numbers_and_letters(self):
        """Test prerelease identifiers with mixed alphanumeric."""
        result = parse("1.0.0-alpha1")
        assert result["prerelease"] == ["alpha1"]
        # This is alphanumeric, not numeric
        assert not result["prerelease"][0].isdigit()

    def test_compare_with_build_and_prerelease(self):
        """Test comparison ignores build even with prerelease."""
        assert compare("1.0.0-alpha+001", "1.0.0-alpha+002") == 0

    def test_numeric_identifier_zero(self):
        """Test numeric identifier that is zero."""
        result = parse("1.0.0-0")
        assert result["prerelease"] == ["0"]
        assert compare("1.0.0-0", "1.0.0-1") == -1

    def test_alphanumeric_starting_with_zero(self):
        """Test alphanumeric identifier starting with zero (valid)."""
        result = parse("1.0.0-0a")
        assert result["prerelease"] == ["0a"]
        # 0a is alphanumeric, so numeric < alphanumeric
        assert compare("1.0.0-0", "1.0.0-0a") == -1
