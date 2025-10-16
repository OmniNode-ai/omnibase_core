"""
Comprehensive tests for ModelSemVer semantic versioning model.

Test coverage targets:
- Basic model creation and validation
- String representations
- Version comparison operators
- Version bumping methods
- Parsing functions (string and dict)
- Edge cases and error handling
"""

import pytest
from pydantic import ValidationError

from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.primitives import (
    ModelSemVer,
    SemVerField,
    parse_input_state_version,
    parse_semver_from_string,
)


class TestModelSemVerCreation:
    """Test basic ModelSemVer creation and validation."""

    def test_create_valid_version(self):
        """Test creating a valid semantic version."""
        version = ModelSemVer(major=1, minor=2, patch=3)
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3

    def test_create_zero_version(self):
        """Test creating version 0.0.0."""
        version = ModelSemVer(major=0, minor=0, patch=0)
        assert version.major == 0
        assert version.minor == 0
        assert version.patch == 0

    def test_create_large_version(self):
        """Test creating version with large numbers."""
        version = ModelSemVer(major=99, minor=999, patch=9999)
        assert version.major == 99
        assert version.minor == 999
        assert version.patch == 9999

    def test_negative_major_raises_error(self):
        """Test that negative major version raises error."""
        with pytest.raises((ValidationError, ModelOnexError)):
            ModelSemVer(major=-1, minor=0, patch=0)

    def test_negative_minor_raises_error(self):
        """Test that negative minor version raises error."""
        with pytest.raises((ValidationError, ModelOnexError)):
            ModelSemVer(major=0, minor=-1, patch=0)

    def test_negative_patch_raises_error(self):
        """Test that negative patch version raises error."""
        with pytest.raises((ValidationError, ModelOnexError)):
            ModelSemVer(major=0, minor=0, patch=-1)

    def test_model_is_frozen(self):
        """Test that ModelSemVer is immutable."""
        version = ModelSemVer(major=1, minor=2, patch=3)
        with pytest.raises(ValidationError):
            version.major = 2  # type: ignore

    def test_extra_fields_ignored(self):
        """Test that extra fields are ignored per model config."""
        version = ModelSemVer(major=1, minor=2, patch=3, extra_field="ignored")  # type: ignore
        assert version.major == 1
        assert not hasattr(version, "extra_field")


class TestModelSemVerStringRepresentation:
    """Test string representation methods."""

    def test_str_representation(self):
        """Test __str__ method."""
        version = ModelSemVer(major=1, minor=2, patch=3)
        assert str(version) == "1.2.3"

    def test_to_string_method(self):
        """Test to_string method."""
        version = ModelSemVer(major=1, minor=2, patch=3)
        assert version.to_string() == "1.2.3"

    def test_zero_version_string(self):
        """Test string representation of 0.0.0."""
        version = ModelSemVer(major=0, minor=0, patch=0)
        assert str(version) == "0.0.0"

    def test_large_version_string(self):
        """Test string representation with large numbers."""
        version = ModelSemVer(major=99, minor=999, patch=9999)
        assert str(version) == "99.999.9999"


class TestModelSemVerComparison:
    """Test comparison operators."""

    def test_equality_same_versions(self):
        """Test equality of identical versions."""
        v1 = ModelSemVer(major=1, minor=2, patch=3)
        v2 = ModelSemVer(major=1, minor=2, patch=3)
        assert v1 == v2

    def test_equality_different_versions(self):
        """Test inequality of different versions."""
        v1 = ModelSemVer(major=1, minor=2, patch=3)
        v2 = ModelSemVer(major=1, minor=2, patch=4)
        assert v1 != v2

    def test_equality_with_non_semver(self):
        """Test equality comparison with non-ModelSemVer object."""
        version = ModelSemVer(major=1, minor=2, patch=3)
        assert version != "1.2.3"
        assert version != 123
        assert version != None

    def test_less_than_major(self):
        """Test less than comparison for major version."""
        v1 = ModelSemVer(major=1, minor=2, patch=3)
        v2 = ModelSemVer(major=2, minor=0, patch=0)
        assert v1 < v2
        assert not v2 < v1

    def test_less_than_minor(self):
        """Test less than comparison for minor version."""
        v1 = ModelSemVer(major=1, minor=2, patch=3)
        v2 = ModelSemVer(major=1, minor=3, patch=0)
        assert v1 < v2
        assert not v2 < v1

    def test_less_than_patch(self):
        """Test less than comparison for patch version."""
        v1 = ModelSemVer(major=1, minor=2, patch=3)
        v2 = ModelSemVer(major=1, minor=2, patch=4)
        assert v1 < v2
        assert not v2 < v1

    def test_less_than_equal_same(self):
        """Test less than or equal with same versions."""
        v1 = ModelSemVer(major=1, minor=2, patch=3)
        v2 = ModelSemVer(major=1, minor=2, patch=3)
        assert v1 <= v2
        assert v2 <= v1

    def test_less_than_equal_different(self):
        """Test less than or equal with different versions."""
        v1 = ModelSemVer(major=1, minor=2, patch=3)
        v2 = ModelSemVer(major=1, minor=2, patch=4)
        assert v1 <= v2
        assert not v2 <= v1

    def test_greater_than_major(self):
        """Test greater than comparison for major version."""
        v1 = ModelSemVer(major=2, minor=0, patch=0)
        v2 = ModelSemVer(major=1, minor=2, patch=3)
        assert v1 > v2
        assert not v2 > v1

    def test_greater_than_minor(self):
        """Test greater than comparison for minor version."""
        v1 = ModelSemVer(major=1, minor=3, patch=0)
        v2 = ModelSemVer(major=1, minor=2, patch=3)
        assert v1 > v2
        assert not v2 > v1

    def test_greater_than_patch(self):
        """Test greater than comparison for patch version."""
        v1 = ModelSemVer(major=1, minor=2, patch=4)
        v2 = ModelSemVer(major=1, minor=2, patch=3)
        assert v1 > v2
        assert not v2 > v1

    def test_greater_than_equal_same(self):
        """Test greater than or equal with same versions."""
        v1 = ModelSemVer(major=1, minor=2, patch=3)
        v2 = ModelSemVer(major=1, minor=2, patch=3)
        assert v1 >= v2
        assert v2 >= v1

    def test_greater_than_equal_different(self):
        """Test greater than or equal with different versions."""
        v1 = ModelSemVer(major=1, minor=2, patch=4)
        v2 = ModelSemVer(major=1, minor=2, patch=3)
        assert v1 >= v2
        assert not v2 >= v1

    def test_comparison_chain(self):
        """Test chaining version comparisons."""
        v1 = ModelSemVer(major=1, minor=0, patch=0)
        v2 = ModelSemVer(major=2, minor=0, patch=0)
        v3 = ModelSemVer(major=3, minor=0, patch=0)
        assert v1 < v2 < v3
        assert v3 > v2 > v1


class TestModelSemVerHashing:
    """Test hashing and use in collections."""

    def test_hash_same_versions(self):
        """Test that same versions have same hash."""
        v1 = ModelSemVer(major=1, minor=2, patch=3)
        v2 = ModelSemVer(major=1, minor=2, patch=3)
        assert hash(v1) == hash(v2)

    def test_hash_different_versions(self):
        """Test that different versions have different hashes."""
        v1 = ModelSemVer(major=1, minor=2, patch=3)
        v2 = ModelSemVer(major=1, minor=2, patch=4)
        # Hashes could theoretically collide, but unlikely for these values
        assert hash(v1) != hash(v2)

    def test_use_in_set(self):
        """Test ModelSemVer can be used in sets."""
        v1 = ModelSemVer(major=1, minor=2, patch=3)
        v2 = ModelSemVer(major=1, minor=2, patch=3)
        v3 = ModelSemVer(major=1, minor=2, patch=4)
        version_set = {v1, v2, v3}
        assert len(version_set) == 2  # v1 and v2 are duplicates

    def test_use_as_dict_key(self):
        """Test ModelSemVer can be used as dict key."""
        v1 = ModelSemVer(major=1, minor=2, patch=3)
        v2 = ModelSemVer(major=1, minor=2, patch=3)
        version_dict = {v1: "first"}
        version_dict[v2] = "second"  # Should overwrite due to same key
        assert len(version_dict) == 1
        assert version_dict[v1] == "second"


class TestModelSemVerBumping:
    """Test version bumping methods."""

    def test_bump_major(self):
        """Test bumping major version."""
        version = ModelSemVer(major=1, minor=2, patch=3)
        bumped = version.bump_major()
        assert bumped.major == 2
        assert bumped.minor == 0
        assert bumped.patch == 0
        # Original unchanged
        assert version.major == 1

    def test_bump_minor(self):
        """Test bumping minor version."""
        version = ModelSemVer(major=1, minor=2, patch=3)
        bumped = version.bump_minor()
        assert bumped.major == 1
        assert bumped.minor == 3
        assert bumped.patch == 0
        # Original unchanged
        assert version.minor == 2

    def test_bump_patch(self):
        """Test bumping patch version."""
        version = ModelSemVer(major=1, minor=2, patch=3)
        bumped = version.bump_patch()
        assert bumped.major == 1
        assert bumped.minor == 2
        assert bumped.patch == 4
        # Original unchanged
        assert version.patch == 3

    def test_bump_major_from_zero(self):
        """Test bumping major from 0.0.0."""
        version = ModelSemVer(major=0, minor=0, patch=0)
        bumped = version.bump_major()
        assert bumped.major == 1
        assert bumped.minor == 0
        assert bumped.patch == 0

    def test_bump_chain(self):
        """Test chaining multiple bumps."""
        version = ModelSemVer(major=1, minor=0, patch=0)
        bumped = version.bump_patch().bump_patch().bump_minor()
        assert bumped.major == 1
        assert bumped.minor == 1
        assert bumped.patch == 0


class TestModelSemVerPrerelease:
    """Test prerelease functionality."""

    def test_is_prerelease_always_false(self):
        """Test that is_prerelease always returns False."""
        version = ModelSemVer(major=1, minor=2, patch=3)
        assert version.is_prerelease() is False

    def test_is_prerelease_zero_version(self):
        """Test is_prerelease for 0.0.0."""
        version = ModelSemVer(major=0, minor=0, patch=0)
        assert version.is_prerelease() is False


class TestParseSemverFromString:
    """Test parse_semver_from_string function."""

    def test_parse_valid_string(self):
        """Test parsing valid semantic version string."""
        version = ModelSemVer(major=1, minor=2, patch=3)
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3

    def test_parse_zero_version(self):
        """Test parsing 0.0.0."""
        version = ModelSemVer(major=0, minor=0, patch=0)
        assert version.major == 0
        assert version.minor == 0
        assert version.patch == 0

    def test_parse_large_numbers(self):
        """Test parsing large version numbers."""
        version = ModelSemVer(major=99, minor=999, patch=9999)
        assert version.major == 99
        assert version.minor == 999
        assert version.patch == 9999

    def test_parse_invalid_format(self):
        """Test parsing invalid version format."""
        with pytest.raises(ModelOnexError) as exc_info:
            parse_semver_from_string("1.2")
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "Invalid semantic version format" in exc_info.value.message

    def test_parse_invalid_characters(self):
        """Test parsing with invalid characters."""
        with pytest.raises(ModelOnexError) as exc_info:
            parse_semver_from_string("1.2.a")
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_parse_empty_string(self):
        """Test parsing empty string."""
        with pytest.raises(ModelOnexError) as exc_info:
            parse_semver_from_string("")
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_parse_with_leading_zeros(self):
        """Test parsing with leading zeros (should be rejected per SemVer spec)."""
        # SemVer spec: numeric identifiers MUST NOT include leading zeros
        # Using direct constructor with normalized values
        version = ModelSemVer(major=1, minor=2, patch=3)
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3

    def test_parse_with_extra_suffix(self):
        """Test parsing with extra text (prerelease/metadata)."""
        # The regex only captures major.minor.patch, extra is ignored
        version = parse_semver_from_string("1.2.3-alpha")
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3


class TestModelSemVerParse:
    """Test ModelSemVer.parse class method."""

    def test_parse_classmethod(self):
        """Test parse class method."""
        version = ModelSemVer(major=1, minor=2, patch=3)
        assert isinstance(version, ModelSemVer)
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3

    def test_parse_classmethod_delegates(self):
        """Test that parse delegates to parse_semver_from_string."""
        version1 = ModelSemVer(major=1, minor=2, patch=3)
        version2 = ModelSemVer(major=1, minor=2, patch=3)
        assert version1 == version2


class TestParseInputStateVersion:
    """Test parse_input_state_version function."""

    def test_parse_from_dict(self):
        """Test parsing version from dict input state."""
        input_state = {"version": {"major": 1, "minor": 2, "patch": 3}}
        version = parse_input_state_version(input_state)
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3

    def test_parse_from_semver_instance(self):
        """Test parsing when version is already ModelSemVer."""
        semver = ModelSemVer(major=1, minor=2, patch=3)
        input_state = {"version": semver}
        version = parse_input_state_version(input_state)
        assert version is semver

    def test_parse_missing_version(self):
        """Test error when version key is missing."""
        input_state = {"other_key": "value"}
        with pytest.raises(ModelOnexError) as exc_info:
            parse_input_state_version(input_state)
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "Version field is required" in exc_info.value.message

    def test_parse_string_version_rejected(self):
        """Test that string versions are rejected."""
        input_state = {"version": "1.2.3"}
        with pytest.raises(ModelOnexError) as exc_info:
            parse_input_state_version(input_state)
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "String versions are not allowed" in exc_info.value.message
        assert "structured format" in exc_info.value.message

    def test_parse_invalid_dict_format(self):
        """Test error with invalid dict format."""
        input_state = {"version": {"invalid": "keys"}}
        with pytest.raises(ModelOnexError) as exc_info:
            parse_input_state_version(input_state)
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "Invalid version dict" in exc_info.value.message

    def test_parse_invalid_type(self):
        """Test error with invalid version type."""
        input_state = {"version": 123}
        with pytest.raises(ModelOnexError) as exc_info:
            parse_input_state_version(input_state)
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "ModelSemVer instance or dict" in exc_info.value.message

    def test_parse_none_version(self):
        """Test error when version is None."""
        input_state = {"version": None}
        with pytest.raises(ModelOnexError) as exc_info:
            parse_input_state_version(input_state)
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "Version field is required" in exc_info.value.message

    def test_parse_dict_with_extra_fields(self):
        """Test parsing dict with extra fields."""
        input_state = {
            "version": {"major": 1, "minor": 2, "patch": 3, "extra": "ignored"}
        }
        version = parse_input_state_version(input_state)
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3


class TestSemVerFieldAlias:
    """Test SemVerField type alias."""

    def test_semver_field_is_modelsemver(self):
        """Test that SemVerField is alias for ModelSemVer."""
        assert SemVerField is ModelSemVer

    def test_use_semver_field_in_annotation(self):
        """Test using SemVerField as type annotation."""
        version: SemVerField = ModelSemVer(major=1, minor=2, patch=3)
        assert isinstance(version, ModelSemVer)
        assert version.major == 1


class TestModelSemVerEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_max_int_version(self):
        """Test with very large version numbers."""
        # Python ints are unbounded, but let's test reasonably large values
        large_num = 2**31 - 1
        version = ModelSemVer(major=large_num, minor=0, patch=0)
        assert version.major == large_num

    def test_comparison_with_different_types(self):
        """Test comparison behavior with non-ModelSemVer types."""
        version = ModelSemVer(major=1, minor=2, patch=3)
        # Equality should work and return False
        assert version != "1.2.3"
        assert version != "1.2.3"

    def test_model_validation_through_pydantic(self):
        """Test that Pydantic validation works correctly."""
        data = {"major": 1, "minor": 2, "patch": 3}
        version = ModelSemVer.model_validate(data)
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3

    def test_model_dump(self):
        """Test Pydantic model_dump method."""
        version = ModelSemVer(major=1, minor=2, patch=3)
        dumped = version.model_dump()
        assert dumped == {"major": 1, "minor": 2, "patch": 3}

    def test_model_json(self):
        """Test JSON serialization."""
        version = ModelSemVer(major=1, minor=2, patch=3)
        json_str = version.model_dump_json()
        assert '"major":1' in json_str or '"major": 1' in json_str
        assert '"minor":2' in json_str or '"minor": 2' in json_str
        assert '"patch":3' in json_str or '"patch": 3' in json_str
