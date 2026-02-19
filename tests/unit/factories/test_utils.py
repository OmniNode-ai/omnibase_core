# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for factory utility functions.

Tests for the internal utility functions used by the profile factory modules.
"""

import pytest

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors import OnexError
from omnibase_core.factories.profiles._utils import _parse_version
from omnibase_core.models.primitives.model_semver import ModelSemVer


@pytest.mark.unit
class TestParseVersion:
    """Tests for _parse_version utility function."""

    def test_parse_full_version(self) -> None:
        """Test parsing a complete major.minor.patch version string."""
        result = _parse_version("1.2.3")
        assert result == ModelSemVer(major=1, minor=2, patch=3)

    def test_parse_major_minor_only(self) -> None:
        """Test parsing version with only major.minor (patch defaults to 0)."""
        result = _parse_version("2.0")
        assert result == ModelSemVer(major=2, minor=0, patch=0)

    def test_parse_major_only(self) -> None:
        """Test parsing version with only major (minor and patch default to 0)."""
        result = _parse_version("5")
        assert result == ModelSemVer(major=5, minor=0, patch=0)

    def test_parse_large_version_numbers(self) -> None:
        """Test parsing version with large numbers."""
        result = _parse_version("100.200.300")
        assert result == ModelSemVer(major=100, minor=200, patch=300)

    def test_empty_string_raises_error(self) -> None:
        """Test that empty string raises OnexError with VALIDATION_ERROR."""
        with pytest.raises(OnexError) as exc_info:
            _parse_version("")

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "empty" in str(exc_info.value.message).lower()

    def test_whitespace_only_raises_error(self) -> None:
        """Test that whitespace-only string raises OnexError with VALIDATION_ERROR."""
        with pytest.raises(OnexError) as exc_info:
            _parse_version("   ")

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "empty" in str(exc_info.value.message).lower()

    def test_non_numeric_major_raises_error(self) -> None:
        """Test that non-numeric major version raises OnexError."""
        with pytest.raises(OnexError) as exc_info:
            _parse_version("abc.1.2")

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "abc.1.2" in str(exc_info.value.message)
        assert "numeric" in str(exc_info.value.message).lower()

    def test_non_numeric_minor_raises_error(self) -> None:
        """Test that non-numeric minor version raises OnexError."""
        with pytest.raises(OnexError) as exc_info:
            _parse_version("1.abc.2")

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "1.abc.2" in str(exc_info.value.message)

    def test_non_numeric_patch_raises_error(self) -> None:
        """Test that non-numeric patch version raises OnexError."""
        with pytest.raises(OnexError) as exc_info:
            _parse_version("1.2.abc")

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "1.2.abc" in str(exc_info.value.message)

    def test_completely_invalid_string_raises_error(self) -> None:
        """Test that completely invalid strings raise OnexError."""
        with pytest.raises(OnexError) as exc_info:
            _parse_version("not-a-version")

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_error_chains_original_exception(self) -> None:
        """Test that OnexError chains the original ValueError."""
        with pytest.raises(OnexError) as exc_info:
            _parse_version("abc.def.ghi")

        # The original ValueError should be chained via 'from e'
        assert exc_info.value.__cause__ is not None
        assert isinstance(exc_info.value.__cause__, ValueError)

    def test_zero_version(self) -> None:
        """Test parsing version with zeros."""
        result = _parse_version("0.0.0")
        assert result == ModelSemVer(major=0, minor=0, patch=0)

    def test_extra_components_ignored(self) -> None:
        """Test that extra version components beyond patch are ignored."""
        result = _parse_version("1.2.3.4.5")
        assert result == ModelSemVer(major=1, minor=2, patch=3)
