"""Tests for ModelMixinVersion.

This module tests semantic version validation and parsing for mixin metadata.
"""

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.core.model_mixin_version import ModelMixinVersion
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class TestModelMixinVersionBasics:
    """Test basic ModelMixinVersion functionality."""

    def test_create_valid_version(self) -> None:
        """Test creating a version with valid non-negative integers."""
        version = ModelMixinVersion(major=1, minor=2, patch=3)
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3

    def test_create_zero_version(self) -> None:
        """Test creating version 0.0.0."""
        version = ModelMixinVersion(major=0, minor=0, patch=0)
        assert version.major == 0
        assert version.minor == 0
        assert version.patch == 0

    def test_str_representation(self) -> None:
        """Test string representation of version."""
        version = ModelMixinVersion(major=1, minor=2, patch=3)
        assert str(version) == "1.2.3"

    def test_str_representation_zero(self) -> None:
        """Test string representation of zero version."""
        version = ModelMixinVersion(major=0, minor=0, patch=0)
        assert str(version) == "0.0.0"


class TestModelMixinVersionNegativeNumbers:
    """Test validation of negative version numbers."""

    def test_negative_major_raises_validation_error(self) -> None:
        """Test that negative major version raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelMixinVersion(major=-1, minor=0, patch=0)
        # Verify it's a validation error about the constraint
        assert "greater than or equal to 0" in str(exc_info.value)

    def test_negative_minor_raises_validation_error(self) -> None:
        """Test that negative minor version raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelMixinVersion(major=0, minor=-1, patch=0)
        assert "greater than or equal to 0" in str(exc_info.value)

    def test_negative_patch_raises_validation_error(self) -> None:
        """Test that negative patch version raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelMixinVersion(major=0, minor=0, patch=-1)
        assert "greater than or equal to 0" in str(exc_info.value)

    def test_all_negative_raises_validation_error(self) -> None:
        """Test that all negative versions raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelMixinVersion(major=-1, minor=-2, patch=-3)
        assert "greater than or equal to 0" in str(exc_info.value)


class TestModelMixinVersionFromString:
    """Test parsing version strings."""

    def test_from_string_valid(self) -> None:
        """Test parsing valid version string."""
        version = ModelMixinVersion.from_string("1.2.3")
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3

    def test_from_string_zero_version(self) -> None:
        """Test parsing zero version string."""
        version = ModelMixinVersion.from_string("0.0.0")
        assert version.major == 0
        assert version.minor == 0
        assert version.patch == 0

    def test_from_string_large_numbers(self) -> None:
        """Test parsing version with large numbers."""
        version = ModelMixinVersion.from_string("100.200.300")
        assert version.major == 100
        assert version.minor == 200
        assert version.patch == 300

    def test_from_string_invalid_format_too_few_parts(self) -> None:
        """Test that version string with too few parts raises ModelOnexError."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelMixinVersion.from_string("1.2")
        assert "Invalid version format" in str(exc_info.value)
        assert "Expected 'major.minor.patch'" in str(exc_info.value)
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_FAILED

    def test_from_string_invalid_format_too_many_parts(self) -> None:
        """Test that version string with too many parts raises ModelOnexError."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelMixinVersion.from_string("1.2.3.4")
        assert "Invalid version format" in str(exc_info.value)
        assert "Expected 'major.minor.patch'" in str(exc_info.value)
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_FAILED

    def test_from_string_invalid_format_empty(self) -> None:
        """Test that empty version string raises ModelOnexError."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelMixinVersion.from_string("")
        assert "Invalid version format" in str(exc_info.value)
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_FAILED

    def test_from_string_non_integer_parts(self) -> None:
        """Test that non-integer parts raise ModelOnexError."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelMixinVersion.from_string("1.2.abc")
        assert "Invalid version string" in str(exc_info.value)
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_FAILED

    def test_from_string_float_parts(self) -> None:
        """Test that float parts raise ModelOnexError."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelMixinVersion.from_string("1.2.3.5")
        # This will fail format check first (too many parts)
        assert "Invalid version format" in str(exc_info.value)
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_FAILED


class TestModelMixinVersionFromStringNegative:
    """Test parsing version strings with negative numbers."""

    def test_from_string_negative_major(self) -> None:
        """Test that negative major version in string raises ModelOnexError with clear message."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelMixinVersion.from_string("-1.0.0")
        assert "Invalid version string" in str(exc_info.value)
        assert "Version numbers must be non-negative" in str(exc_info.value)
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_FAILED

    def test_from_string_negative_minor(self) -> None:
        """Test that negative minor version in string raises ModelOnexError with clear message."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelMixinVersion.from_string("0.-1.0")
        assert "Invalid version string" in str(exc_info.value)
        assert "Version numbers must be non-negative" in str(exc_info.value)
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_FAILED

    def test_from_string_negative_patch(self) -> None:
        """Test that negative patch version in string raises ModelOnexError with clear message."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelMixinVersion.from_string("0.0.-1")
        assert "Invalid version string" in str(exc_info.value)
        assert "Version numbers must be non-negative" in str(exc_info.value)
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_FAILED

    def test_from_string_all_negative(self) -> None:
        """Test that all negative versions in string raise ModelOnexError with clear message."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelMixinVersion.from_string("-1.-2.-3")
        assert "Invalid version string" in str(exc_info.value)
        assert "Version numbers must be non-negative" in str(exc_info.value)
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_FAILED

    def test_from_string_mixed_negative(self) -> None:
        """Test that mixed negative/positive versions in string raise ModelOnexError."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelMixinVersion.from_string("-1.2.3")
        assert "Invalid version string" in str(exc_info.value)
        assert "Version numbers must be non-negative" in str(exc_info.value)
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_FAILED


class TestModelMixinVersionEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_version_with_leading_zeros(self) -> None:
        """Test parsing version with leading zeros."""
        # Python int() handles leading zeros correctly (they're just ignored)
        version = ModelMixinVersion.from_string("01.02.03")
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3

    def test_version_with_whitespace_succeeds(self) -> None:
        """Test that version with whitespace succeeds (int() strips whitespace)."""
        # Python's int() automatically strips leading/trailing whitespace
        version = ModelMixinVersion.from_string(" 1.2.3 ")
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3

    def test_version_with_extra_dots(self) -> None:
        """Test that version with extra dots raises error."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelMixinVersion.from_string("1..2.3")
        # This has 4 parts after split, so format check catches it first
        assert "Invalid version format" in str(exc_info.value)
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_FAILED
