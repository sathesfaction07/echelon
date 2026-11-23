"""SemVer 2.0.0 parser and comparator.

This module provides functions to parse and compare semantic version strings
according to the SemVer 2.0.0 specification.
"""

import re


def parse(version_str):
    """Parse a SemVer 2.0.0 version string.

    Args:
        version_str: A semantic version string (e.g., '1.2.3-alpha.1+build')

    Returns:
        dict with keys:
            - major: int
            - minor: int
            - patch: int
            - prerelease: list[str] (empty if no prerelease)
            - build: str (empty string if no build metadata)

    Raises:
        ValueError: If the version string violates SemVer 2.0.0 format
    """
    if not version_str or not isinstance(version_str, str):
        raise ValueError("Version must be a non-empty string")

    # SemVer 2.0.0 regex pattern
    # Format: MAJOR.MINOR.PATCH[-PRERELEASE][+BUILD]
    pattern = r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"

    match = re.match(pattern, version_str)

    if not match:
        raise ValueError(f"Invalid SemVer format: {version_str}")

    major_str, minor_str, patch_str, prerelease_str, build_str = match.groups()

    # Parse major, minor, patch as integers
    major = int(major_str)
    minor = int(minor_str)
    patch = int(patch_str)

    # Parse prerelease identifiers
    prerelease = []
    if prerelease_str:
        prerelease = prerelease_str.split(".")

    # Parse build metadata
    build = build_str if build_str else ""

    return {
        "major": major,
        "minor": minor,
        "patch": patch,
        "prerelease": prerelease,
        "build": build,
    }


def compare(a_str, b_str):
    """Compare two SemVer version strings.

    Args:
        a_str: First version string
        b_str: Second version string

    Returns:
        -1 if a < b
         0 if a == b
         1 if a > b

    Comparison follows SemVer 2.0.0 precedence rules:
    1. Compare major.minor.patch numerically
    2. Version without prerelease > version with prerelease
    3. Compare prerelease identifiers left-to-right:
       - Numeric identifiers compared as integers
       - Alphanumeric compared lexically as ASCII strings
       - Numeric < alphanumeric
    4. Build metadata is ignored
    """
    a = parse(a_str)
    b = parse(b_str)

    # Compare major.minor.patch
    for key in ["major", "minor", "patch"]:
        if a[key] < b[key]:
            return -1
        elif a[key] > b[key]:
            return 1

    # If major.minor.patch are equal, compare prerelease
    a_pre = a["prerelease"]
    b_pre = b["prerelease"]

    # Version without prerelease > version with prerelease
    if not a_pre and not b_pre:
        return 0
    elif not a_pre and b_pre:
        return 1
    elif a_pre and not b_pre:
        return -1

    # Both have prerelease, compare identifiers
    for i in range(min(len(a_pre), len(b_pre))):
        a_id = a_pre[i]
        b_id = b_pre[i]

        # Check if identifiers are numeric
        a_is_num = _is_numeric(a_id)
        b_is_num = _is_numeric(b_id)

        if a_is_num and b_is_num:
            # Both numeric: compare as integers
            a_val = int(a_id)
            b_val = int(b_id)
            if a_val < b_val:
                return -1
            elif a_val > b_val:
                return 1
        elif a_is_num and not b_is_num:
            # Numeric < alphanumeric
            return -1
        elif not a_is_num and b_is_num:
            # Alphanumeric > numeric
            return 1
        else:
            # Both alphanumeric: compare lexically
            if a_id < b_id:
                return -1
            elif a_id > b_id:
                return 1

    # All compared identifiers are equal
    # Fewer identifiers < more identifiers
    if len(a_pre) < len(b_pre):
        return -1
    elif len(a_pre) > len(b_pre):
        return 1

    return 0


def _is_numeric(identifier):
    """Check if a prerelease identifier is purely numeric.

    Args:
        identifier: A prerelease identifier string

    Returns:
        True if the identifier contains only digits, False otherwise
    """
    return identifier.isdigit()
