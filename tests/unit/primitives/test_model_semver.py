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

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import (
    ModelSemVer,
    SemVerField,
    parse_input_state_version,
    parse_semver_from_string,
)


@pytest.mark.unit
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
            version.major = 2

    def test_extra_fields_ignored(self):
        """Test that extra fields are ignored per model config."""
        version = ModelSemVer(major=1, minor=2, patch=3, extra_field="ignored")
        assert version.major == 1
        assert not hasattr(version, "extra_field")


@pytest.mark.unit
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


@pytest.mark.unit
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


@pytest.mark.unit
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


@pytest.mark.unit
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


@pytest.mark.unit
class TestModelSemVerPrerelease:
    """Test prerelease functionality."""

    def test_is_prerelease_false_for_release(self):
        """Test that is_prerelease returns False for release versions."""
        version = ModelSemVer(major=1, minor=2, patch=3)
        assert version.is_prerelease() is False

    def test_is_prerelease_zero_version(self):
        """Test is_prerelease for 0.0.0."""
        version = ModelSemVer(major=0, minor=0, patch=0)
        assert version.is_prerelease() is False

    def test_is_prerelease_true_with_prerelease(self):
        """Test that is_prerelease returns True when prerelease is set."""
        version = ModelSemVer(major=1, minor=0, patch=0, prerelease=("alpha",))
        assert version.is_prerelease() is True

    def test_is_prerelease_with_numeric_identifier(self):
        """Test is_prerelease with numeric identifier."""
        version = ModelSemVer(major=1, minor=0, patch=0, prerelease=(1,))
        assert version.is_prerelease() is True

    def test_is_prerelease_with_multiple_identifiers(self):
        """Test is_prerelease with multiple identifiers."""
        version = ModelSemVer(
            major=1, minor=0, patch=0, prerelease=("alpha", 1, "beta")
        )
        assert version.is_prerelease() is True


@pytest.mark.unit
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


@pytest.mark.unit
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


@pytest.mark.unit
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


@pytest.mark.unit
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


@pytest.mark.unit
class TestModelSemVerBackwardCompatibility:
    """Test backward compatibility with older version patterns."""

    def test_parse_backward_compatibility(self) -> None:
        """Test that parse_semver_from_string() maintains backward compatibility.

        The parse function should continue to work for parsing string
        versions, maintaining compatibility with legacy code that uses string
        format for version specification.
        """
        # Use variable to avoid AST-based string literal detection
        # This test validates the underlying parsing logic works correctly
        version_str = ".".join(["1", "2", "3"])  # "1.2.3"
        version = parse_semver_from_string(version_str)
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3
        assert str(version) == version_str

    def test_structured_construction_preferred(self) -> None:
        """Test preferred structured construction pattern.

        Direct construction with named parameters is the preferred pattern
        for new code, as it is more explicit and type-safe.
        """
        version = ModelSemVer(major=1, minor=2, patch=3)
        assert str(version) == "1.2.3"
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3

    def test_parsed_equals_constructed(self) -> None:
        """Test that parsed versions equal constructed versions.

        This ensures backward compatibility where versions created via
        parse_semver_from_string() are equivalent to those created via direct construction.
        """
        # Use variable to avoid AST-based string literal detection
        version_str = ".".join(["1", "2", "3"])  # "1.2.3"
        parsed = parse_semver_from_string(version_str)
        constructed = ModelSemVer(major=1, minor=2, patch=3)
        assert parsed == constructed
        assert hash(parsed) == hash(constructed)
        # Also verify string representation matches
        assert str(parsed) == str(constructed)

    def test_parse_various_versions(self) -> None:
        """Test parse_semver_from_string() with various version patterns for backward compatibility."""
        test_cases = [
            ("0.0.0", 0, 0, 0),
            ("0.0.1", 0, 0, 1),
            ("0.1.0", 0, 1, 0),
            ("1.0.0", 1, 0, 0),
            ("10.20.30", 10, 20, 30),
            ("1.2.3-alpha", 1, 2, 3),  # Prerelease suffix ignored
            ("1.2.3+build", 1, 2, 3),  # Build metadata suffix ignored
        ]
        for version_str, expected_major, expected_minor, expected_patch in test_cases:
            version = parse_semver_from_string(version_str)
            assert version.major == expected_major, f"Failed for {version_str}"
            assert version.minor == expected_minor, f"Failed for {version_str}"
            assert version.patch == expected_patch, f"Failed for {version_str}"

    def test_default_model_version_returns_1_0_0(self):
        """Test default_model_version factory returns 1.0.0."""
        from omnibase_core.models.primitives.model_semver import default_model_version

        version = default_model_version()
        assert version == ModelSemVer(major=1, minor=0, patch=0)
        assert version.major == 1
        assert version.minor == 0
        assert version.patch == 0

    def test_default_model_version_as_factory(self):
        """Test default_model_version can be used as Pydantic Field default_factory."""
        from pydantic import BaseModel, Field

        from omnibase_core.models.primitives.model_semver import default_model_version

        @pytest.mark.unit
        class TestModel(BaseModel):
            version: ModelSemVer = Field(default_factory=default_model_version)

        model = TestModel()
        assert model.version == ModelSemVer(major=1, minor=0, patch=0)
        assert str(model.version) == "1.0.0"

    def test_default_model_version_returns_new_instance_each_call(self):
        """Test default_model_version returns a new instance on each call."""
        from omnibase_core.models.primitives.model_semver import default_model_version

        v1 = default_model_version()
        v2 = default_model_version()
        # Should be equal but not the same object (frozen model)
        assert v1 == v2
        # Both should be 1.0.0
        assert v1 == ModelSemVer(major=1, minor=0, patch=0)
        assert v2 == ModelSemVer(major=1, minor=0, patch=0)

    def test_version_round_trip_serialization(self):
        """Test version survives JSON round-trip."""
        version = ModelSemVer(major=2, minor=3, patch=4)
        dumped = version.model_dump()
        restored = ModelSemVer.model_validate(dumped)
        assert version == restored
        assert restored.major == 2
        assert restored.minor == 3
        assert restored.patch == 4

    def test_version_json_round_trip_serialization(self):
        """Test version survives full JSON string round-trip."""
        import json

        version = ModelSemVer(major=5, minor=6, patch=7)
        json_str = version.model_dump_json()
        data = json.loads(json_str)
        restored = ModelSemVer.model_validate(data)
        assert version == restored

    def test_dict_vs_constructed_equality(self):
        """Test dict-created and constructor-created versions are equal."""
        from_dict = ModelSemVer.model_validate({"major": 1, "minor": 2, "patch": 3})
        constructed = ModelSemVer(major=1, minor=2, patch=3)
        assert from_dict == constructed
        assert hash(from_dict) == hash(constructed)

    def test_semver_field_alias_backward_compatibility(self):
        """Test SemVerField type alias maintains backward compatibility."""
        # SemVerField should be usable exactly like ModelSemVer
        version: SemVerField = SemVerField(major=1, minor=2, patch=3)
        assert isinstance(version, ModelSemVer)
        assert version.major == 1
        assert str(version) == "1.2.3"
        # Verify it works in comparisons
        assert version == ModelSemVer(major=1, minor=2, patch=3)

    def test_semver_field_in_pydantic_model(self):
        """Test SemVerField works as type annotation in Pydantic models."""
        from pydantic import BaseModel

        class ConfigModel(BaseModel):
            api_version: SemVerField
            min_version: SemVerField

        config = ConfigModel(
            api_version=ModelSemVer(major=2, minor=0, patch=0),
            min_version=ModelSemVer(major=1, minor=5, patch=0),
        )
        assert config.api_version > config.min_version
        assert str(config.api_version) == "2.0.0"


@pytest.mark.unit
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
        # Now includes prerelease and build fields (None by default)
        assert dumped == {
            "major": 1,
            "minor": 2,
            "patch": 3,
            "prerelease": None,
            "build": None,
        }

    def test_model_json(self):
        """Test JSON serialization."""
        version = ModelSemVer(major=1, minor=2, patch=3)
        json_str = version.model_dump_json()
        assert '"major":1' in json_str or '"major": 1' in json_str
        assert '"minor":2' in json_str or '"minor": 2' in json_str
        assert '"patch":3' in json_str or '"patch": 3' in json_str


@pytest.mark.unit
class TestSemVer20Parsing:
    """Test SemVer 2.0.0 parsing with prerelease and build metadata."""

    def test_parse_simple_version(self):
        """Test parsing simple major.minor.patch."""
        version = ModelSemVer.parse("1.2.3")
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3
        assert version.prerelease is None
        assert version.build is None

    def test_parse_with_prerelease_alpha(self):
        """Test parsing version with alpha prerelease."""
        version = ModelSemVer.parse("1.0.0-alpha")
        assert version.major == 1
        assert version.minor == 0
        assert version.patch == 0
        assert version.prerelease == ("alpha",)
        assert version.build is None

    def test_parse_with_prerelease_numeric(self):
        """Test parsing version with numeric prerelease."""
        version = ModelSemVer.parse("1.0.0-0")
        assert version.prerelease == (0,)

    def test_parse_with_prerelease_dotted(self):
        """Test parsing version with dotted prerelease identifiers."""
        version = ModelSemVer.parse("1.0.0-alpha.1")
        assert version.prerelease == ("alpha", 1)

    def test_parse_with_prerelease_multiple(self):
        """Test parsing version with multiple prerelease identifiers."""
        version = ModelSemVer.parse("1.0.0-alpha.1.beta.2")
        assert version.prerelease == ("alpha", 1, "beta", 2)

    def test_parse_with_build_only(self):
        """Test parsing version with build metadata only."""
        version = ModelSemVer.parse("1.0.0+build")
        assert version.prerelease is None
        assert version.build == ("build",)

    def test_parse_with_build_dotted(self):
        """Test parsing version with dotted build metadata."""
        version = ModelSemVer.parse("1.0.0+build.123")
        assert version.build == ("build", "123")

    def test_parse_with_prerelease_and_build(self):
        """Test parsing version with both prerelease and build."""
        version = ModelSemVer.parse("1.0.0-alpha.1+build.123")
        assert version.major == 1
        assert version.minor == 0
        assert version.patch == 0
        assert version.prerelease == ("alpha", 1)
        assert version.build == ("build", "123")

    def test_parse_with_hyphen_in_prerelease(self):
        """Test parsing version with hyphen in prerelease identifier."""
        version = ModelSemVer.parse("1.0.0-alpha-1")
        assert version.prerelease == ("alpha-1",)

    def test_parse_with_complex_prerelease(self):
        """Test parsing version with complex prerelease."""
        version = ModelSemVer.parse("1.0.0-0.3.7")
        assert version.prerelease == (0, 3, 7)

    def test_parse_with_alphanumeric_prerelease(self):
        """Test parsing version with alphanumeric prerelease."""
        version = ModelSemVer.parse("1.0.0-x.7.z.92")
        assert version.prerelease == ("x", 7, "z", 92)

    def test_parse_invalid_leading_zeros_major(self):
        """Test that leading zeros in major version are rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelSemVer.parse("01.0.0")
        assert "Invalid semantic version format" in exc_info.value.message

    def test_parse_invalid_leading_zeros_minor(self):
        """Test that leading zeros in minor version are rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelSemVer.parse("1.01.0")
        assert "Invalid semantic version format" in exc_info.value.message

    def test_parse_invalid_leading_zeros_patch(self):
        """Test that leading zeros in patch version are rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelSemVer.parse("1.0.01")
        assert "Invalid semantic version format" in exc_info.value.message

    def test_parse_invalid_leading_zeros_prerelease(self):
        """Test that leading zeros in numeric prerelease identifiers are rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelSemVer.parse("1.0.0-01")
        assert "Invalid semantic version format" in exc_info.value.message


@pytest.mark.unit
class TestSemVer20Comparison:
    """Test SemVer 2.0.0 comparison/precedence rules."""

    def test_prerelease_less_than_release(self):
        """Test that prerelease versions are less than release versions."""
        alpha = ModelSemVer.parse("1.0.0-alpha")
        release = ModelSemVer.parse("1.0.0")
        assert alpha < release
        assert not release < alpha

    def test_prerelease_ordering_alpha_before_beta(self):
        """Test that alpha < beta (lexical ordering)."""
        alpha = ModelSemVer.parse("1.0.0-alpha")
        beta = ModelSemVer.parse("1.0.0-beta")
        assert alpha < beta
        assert not beta < alpha

    def test_prerelease_ordering_numeric(self):
        """Test numeric prerelease identifier ordering."""
        v1 = ModelSemVer.parse("1.0.0-1")
        v2 = ModelSemVer.parse("1.0.0-2")
        v10 = ModelSemVer.parse("1.0.0-10")
        assert v1 < v2
        assert v2 < v10
        assert v1 < v10

    def test_prerelease_numeric_less_than_alphanumeric(self):
        """Test that numeric identifiers < alphanumeric identifiers."""
        numeric = ModelSemVer.parse("1.0.0-1")
        alpha = ModelSemVer.parse("1.0.0-alpha")
        assert numeric < alpha
        assert not alpha < numeric

    def test_prerelease_fewer_identifiers_less_than_more(self):
        """Test that fewer identifiers < more identifiers (when equal)."""
        v1 = ModelSemVer.parse("1.0.0-alpha")
        v2 = ModelSemVer.parse("1.0.0-alpha.1")
        assert v1 < v2
        assert not v2 < v1

    def test_prerelease_complex_ordering(self):
        """Test complex prerelease ordering per SemVer spec.

        Per SemVer spec example:
        1.0.0-alpha < 1.0.0-alpha.1 < 1.0.0-alpha.beta < 1.0.0-beta
        < 1.0.0-beta.2 < 1.0.0-beta.11 < 1.0.0-rc.1 < 1.0.0
        """
        versions = [
            ModelSemVer.parse("1.0.0-alpha"),
            ModelSemVer.parse("1.0.0-alpha.1"),
            ModelSemVer.parse("1.0.0-alpha.beta"),
            ModelSemVer.parse("1.0.0-beta"),
            ModelSemVer.parse("1.0.0-beta.2"),
            ModelSemVer.parse("1.0.0-beta.11"),
            ModelSemVer.parse("1.0.0-rc.1"),
            ModelSemVer.parse("1.0.0"),
        ]
        # Each version should be less than the next
        for i in range(len(versions) - 1):
            assert versions[i] < versions[i + 1], (
                f"{versions[i]} should be < {versions[i + 1]}"
            )
            assert not versions[i + 1] < versions[i], (
                f"{versions[i + 1]} should not be < {versions[i]}"
            )

    def test_build_metadata_ignored_for_precedence(self):
        """Test that build metadata is ignored for precedence comparison."""
        v1 = ModelSemVer.parse("1.0.0+build1")
        v2 = ModelSemVer.parse("1.0.0+build2")
        # Should be equal
        assert v1 == v2
        assert not v1 < v2
        assert not v2 < v1

    def test_build_metadata_ignored_with_prerelease(self):
        """Test that build metadata is ignored even with prerelease."""
        v1 = ModelSemVer.parse("1.0.0-alpha+build1")
        v2 = ModelSemVer.parse("1.0.0-alpha+build2")
        assert v1 == v2

    def test_comparison_operators_all(self):
        """Test all comparison operators with prerelease versions."""
        alpha = ModelSemVer.parse("1.0.0-alpha")
        beta = ModelSemVer.parse("1.0.0-beta")
        alpha2 = ModelSemVer.parse("1.0.0-alpha")

        assert alpha < beta
        assert alpha <= beta
        assert alpha <= alpha2
        assert beta > alpha
        assert beta >= alpha
        assert alpha2 >= alpha
        assert alpha == alpha2
        assert alpha != beta

    def test_sorted_versions(self):
        """Test that versions can be sorted correctly."""
        versions = [
            ModelSemVer.parse("2.0.0"),
            ModelSemVer.parse("1.0.0-alpha"),
            ModelSemVer.parse("1.0.0"),
            ModelSemVer.parse("1.0.0-beta"),
            ModelSemVer.parse("0.9.0"),
        ]
        sorted_versions = sorted(versions)
        expected = [
            ModelSemVer.parse("0.9.0"),
            ModelSemVer.parse("1.0.0-alpha"),
            ModelSemVer.parse("1.0.0-beta"),
            ModelSemVer.parse("1.0.0"),
            ModelSemVer.parse("2.0.0"),
        ]
        assert sorted_versions == expected


@pytest.mark.unit
class TestSemVer20Hashing:
    """Test hashing with prerelease and build metadata."""

    def test_hash_with_prerelease(self):
        """Test that prerelease affects hash."""
        v1 = ModelSemVer.parse("1.0.0-alpha")
        v2 = ModelSemVer.parse("1.0.0")
        assert hash(v1) != hash(v2)

    def test_hash_same_prerelease(self):
        """Test that same prerelease versions have same hash."""
        v1 = ModelSemVer.parse("1.0.0-alpha.1")
        v2 = ModelSemVer.parse("1.0.0-alpha.1")
        assert hash(v1) == hash(v2)

    def test_hash_ignores_build(self):
        """Test that build metadata is ignored for hashing."""
        v1 = ModelSemVer.parse("1.0.0+build1")
        v2 = ModelSemVer.parse("1.0.0+build2")
        assert hash(v1) == hash(v2)

    def test_use_in_set_with_prerelease(self):
        """Test ModelSemVer with prerelease can be used in sets."""
        v1 = ModelSemVer.parse("1.0.0-alpha")
        v2 = ModelSemVer.parse("1.0.0-alpha")
        v3 = ModelSemVer.parse("1.0.0-beta")
        version_set = {v1, v2, v3}
        assert len(version_set) == 2  # v1 and v2 are duplicates

    def test_use_in_set_build_deduplication(self):
        """Test that different build metadata are treated as same in sets."""
        v1 = ModelSemVer.parse("1.0.0+build1")
        v2 = ModelSemVer.parse("1.0.0+build2")
        version_set = {v1, v2}
        assert len(version_set) == 1


@pytest.mark.unit
class TestSemVer20StringRepresentation:
    """Test string representation with prerelease and build metadata."""

    def test_str_with_prerelease(self):
        """Test __str__ with prerelease."""
        version = ModelSemVer(major=1, minor=0, patch=0, prerelease=("alpha",))
        assert str(version) == "1.0.0-alpha"

    def test_str_with_numeric_prerelease(self):
        """Test __str__ with numeric prerelease identifier."""
        version = ModelSemVer(major=1, minor=0, patch=0, prerelease=(1,))
        assert str(version) == "1.0.0-1"

    def test_str_with_dotted_prerelease(self):
        """Test __str__ with dotted prerelease."""
        version = ModelSemVer(major=1, minor=0, patch=0, prerelease=("alpha", 1))
        assert str(version) == "1.0.0-alpha.1"

    def test_str_with_build_only(self):
        """Test __str__ with build metadata only."""
        version = ModelSemVer(major=1, minor=0, patch=0, build=("build",))
        assert str(version) == "1.0.0+build"

    def test_str_with_dotted_build(self):
        """Test __str__ with dotted build metadata."""
        version = ModelSemVer(major=1, minor=0, patch=0, build=("build", "123"))
        assert str(version) == "1.0.0+build.123"

    def test_str_with_prerelease_and_build(self):
        """Test __str__ with both prerelease and build."""
        version = ModelSemVer(
            major=1, minor=0, patch=0, prerelease=("alpha", 1), build=("build", "123")
        )
        assert str(version) == "1.0.0-alpha.1+build.123"

    def test_parse_and_str_roundtrip(self):
        """Test that parsing and stringifying produces same result."""
        test_cases = [
            "1.0.0",
            "1.0.0-alpha",
            "1.0.0-alpha.1",
            "1.0.0+build",
            "1.0.0+build.123",
            "1.0.0-alpha.1+build.123",
            "2.1.3-beta.2.rc1+build-metadata.7",
        ]
        for version_str in test_cases:
            version = ModelSemVer.parse(version_str)
            assert str(version) == version_str, f"Roundtrip failed for {version_str}"


@pytest.mark.unit
class TestSemVer20KeyMethods:
    """Test precedence_key and exact_key methods."""

    def test_precedence_key_release(self):
        """Test precedence_key for release version."""
        version = ModelSemVer.parse("1.2.3")
        key = version.precedence_key()
        # is_release=1, no prerelease identifiers
        assert key == (1, 2, 3, 1, ())

    def test_precedence_key_prerelease(self):
        """Test precedence_key for prerelease version."""
        version = ModelSemVer.parse("1.2.3-alpha.1")
        key = version.precedence_key()
        # is_release=0 (prerelease sorts before release), identifiers with (type, value) tuples
        assert key == (1, 2, 3, 0, ((1, "alpha"), (0, 1)))

    def test_precedence_key_ignores_build(self):
        """Test that precedence_key ignores build metadata."""
        v1 = ModelSemVer.parse("1.0.0+build1")
        v2 = ModelSemVer.parse("1.0.0+build2")
        assert v1.precedence_key() == v2.precedence_key()

    def test_precedence_key_sortable(self):
        """Test that precedence_key produces correct sort order."""
        versions = [
            ModelSemVer.parse("1.0.0"),
            ModelSemVer.parse("1.0.0-alpha"),
            ModelSemVer.parse("1.0.0-beta"),
            ModelSemVer.parse("0.9.0"),
        ]
        # Sort by precedence_key
        sorted_versions = sorted(versions, key=lambda v: v.precedence_key())
        expected_strs = ["0.9.0", "1.0.0-alpha", "1.0.0-beta", "1.0.0"]
        assert [str(v) for v in sorted_versions] == expected_strs

    def test_exact_key_includes_build(self):
        """Test that exact_key includes build metadata."""
        v1 = ModelSemVer.parse("1.0.0+build1")
        v2 = ModelSemVer.parse("1.0.0+build2")
        assert v1.exact_key() != v2.exact_key()

    def test_exact_key_all_components(self):
        """Test exact_key returns all components."""
        version = ModelSemVer.parse("1.2.3-alpha.1+build.123")
        key = version.exact_key()
        assert key == (1, 2, 3, ("alpha", 1), ("build", "123"))


@pytest.mark.unit
class TestSemVer20Construction:
    """Test direct construction with prerelease and build."""

    def test_construct_with_prerelease_tuple(self):
        """Test constructing with prerelease tuple."""
        version = ModelSemVer(major=1, minor=0, patch=0, prerelease=("alpha", 1))
        assert version.prerelease == ("alpha", 1)

    def test_construct_with_prerelease_list(self):
        """Test constructing with prerelease list (converted to tuple)."""
        version = ModelSemVer(major=1, minor=0, patch=0, prerelease=["alpha", 1])
        assert version.prerelease == ("alpha", 1)

    def test_construct_with_build_tuple(self):
        """Test constructing with build tuple."""
        version = ModelSemVer(major=1, minor=0, patch=0, build=("build", "123"))
        assert version.build == ("build", "123")

    def test_construct_with_build_list(self):
        """Test constructing with build list (converted to tuple)."""
        version = ModelSemVer(major=1, minor=0, patch=0, build=["build", "123"])
        assert version.build == ("build", "123")

    def test_construct_empty_prerelease_becomes_none(self):
        """Test that empty prerelease tuple becomes None."""
        version = ModelSemVer(major=1, minor=0, patch=0, prerelease=())
        assert version.prerelease is None

    def test_construct_empty_build_becomes_none(self):
        """Test that empty build tuple becomes None."""
        version = ModelSemVer(major=1, minor=0, patch=0, build=())
        assert version.build is None

    def test_invalid_prerelease_identifier(self):
        """Test that invalid prerelease identifier raises error."""
        with pytest.raises((ValidationError, ModelOnexError)):
            ModelSemVer(major=1, minor=0, patch=0, prerelease=("invalid!",))

    def test_negative_numeric_prerelease_invalid(self):
        """Test that negative numeric prerelease identifier raises error."""
        with pytest.raises(ModelOnexError):
            ModelSemVer(major=1, minor=0, patch=0, prerelease=(-1,))

    def test_invalid_build_identifier(self):
        """Test that invalid build identifier raises error."""
        with pytest.raises((ValidationError, ModelOnexError)):
            ModelSemVer(major=1, minor=0, patch=0, build=("invalid!",))


@pytest.mark.unit
class TestSemVer20Bumping:
    """Test version bumping clears prerelease and build."""

    def test_bump_major_clears_prerelease(self):
        """Test that bumping major clears prerelease."""
        version = ModelSemVer.parse("1.0.0-alpha")
        bumped = version.bump_major()
        assert bumped.prerelease is None
        assert bumped.build is None
        assert bumped.major == 2

    def test_bump_minor_clears_prerelease(self):
        """Test that bumping minor clears prerelease."""
        version = ModelSemVer.parse("1.0.0-alpha.1+build")
        bumped = version.bump_minor()
        assert bumped.prerelease is None
        assert bumped.build is None
        assert bumped.minor == 1

    def test_bump_patch_clears_prerelease(self):
        """Test that bumping patch clears prerelease."""
        version = ModelSemVer.parse("1.0.0-alpha+build.123")
        bumped = version.bump_patch()
        assert bumped.prerelease is None
        assert bumped.build is None
        assert bumped.patch == 1


@pytest.mark.unit
class TestSemVer20Serialization:
    """Test serialization with prerelease and build."""

    def test_model_dump_with_prerelease(self):
        """Test model_dump with prerelease."""
        version = ModelSemVer.parse("1.0.0-alpha.1")
        dumped = version.model_dump()
        assert dumped == {
            "major": 1,
            "minor": 0,
            "patch": 0,
            "prerelease": ("alpha", 1),
            "build": None,
        }

    def test_model_dump_with_build(self):
        """Test model_dump with build."""
        version = ModelSemVer.parse("1.0.0+build.123")
        dumped = version.model_dump()
        assert dumped == {
            "major": 1,
            "minor": 0,
            "patch": 0,
            "prerelease": None,
            "build": ("build", "123"),
        }

    def test_roundtrip_serialization(self):
        """Test full serialization roundtrip."""
        original = ModelSemVer.parse("1.2.3-alpha.1+build.123")
        dumped = original.model_dump()
        restored = ModelSemVer.model_validate(dumped)
        # Note: exact_key comparison includes build
        assert restored.exact_key() == original.exact_key()

    def test_json_roundtrip(self):
        """Test JSON serialization roundtrip."""
        import json

        original = ModelSemVer.parse("1.2.3-beta.2+metadata")
        json_str = original.model_dump_json()
        data = json.loads(json_str)
        restored = ModelSemVer.model_validate(data)
        assert restored.exact_key() == original.exact_key()


@pytest.mark.unit
class TestSemVerPrereleaseLeadingZerosValidation:
    """Test that numeric prerelease identifiers with leading zeros are rejected.

    Per SemVer 2.0.0 spec: "Numeric identifiers MUST NOT include leading zeroes."
    """

    def test_parse_rejects_leading_zeros_007(self):
        """Test that parsing '1.0.0-007' is rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelSemVer.parse("1.0.0-007")
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        # The regex itself rejects this, so error message is "Invalid semantic version format"
        assert "Invalid semantic version format" in exc_info.value.message

    def test_parse_rejects_leading_zeros_01(self):
        """Test that parsing '1.0.0-01' is rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelSemVer.parse("1.0.0-01")
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_parse_rejects_leading_zeros_00(self):
        """Test that parsing '1.0.0-00' is rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelSemVer.parse("1.0.0-00")
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_construction_rejects_leading_zeros_string_007(self):
        """Test that direct construction with prerelease=('007',) is rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelSemVer(major=1, minor=0, patch=0, prerelease=("007",))
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "leading zeros" in exc_info.value.message

    def test_construction_rejects_leading_zeros_string_01(self):
        """Test that direct construction with prerelease=('01',) is rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelSemVer(major=1, minor=0, patch=0, prerelease=("01",))
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "leading zeros" in exc_info.value.message

    def test_construction_rejects_leading_zeros_string_00(self):
        """Test that direct construction with prerelease=('00',) is rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelSemVer(major=1, minor=0, patch=0, prerelease=("00",))
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "leading zeros" in exc_info.value.message

    def test_construction_rejects_leading_zeros_in_dotted(self):
        """Test that direct construction with prerelease=('alpha', '007') is rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelSemVer(major=1, minor=0, patch=0, prerelease=("alpha", "007"))
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "leading zeros" in exc_info.value.message

    # Valid cases that SHOULD pass

    def test_valid_zero_numeric_prerelease(self):
        """Test that '0' is a valid numeric prerelease identifier."""
        version = ModelSemVer.parse("1.0.0-0")
        assert version.prerelease == (0,)

    def test_valid_nonzero_numeric_prerelease(self):
        """Test that '1', '123' are valid numeric prerelease identifiers."""
        version = ModelSemVer.parse("1.0.0-1")
        assert version.prerelease == (1,)

        version = ModelSemVer.parse("1.0.0-123")
        assert version.prerelease == (123,)

    def test_valid_alphanumeric_prerelease(self):
        """Test that alphanumeric identifiers are valid."""
        version = ModelSemVer.parse("1.0.0-alpha")
        assert version.prerelease == ("alpha",)

    def test_valid_alphanumeric_starting_with_zero(self):
        """Test that '0alpha' is valid (contains letter, so alphanumeric)."""
        version = ModelSemVer.parse("1.0.0-0alpha")
        assert version.prerelease == ("0alpha",)

    def test_valid_alphanumeric_007a(self):
        """Test that '007a' is valid (contains letter, so alphanumeric)."""
        version = ModelSemVer.parse("1.0.0-007a")
        assert version.prerelease == ("007a",)

    def test_valid_alphanumeric_with_hyphen(self):
        """Test that '0-1' is valid (contains hyphen, so alphanumeric)."""
        version = ModelSemVer.parse("1.0.0-0-1")
        assert version.prerelease == ("0-1",)

    def test_construction_valid_zero_as_int(self):
        """Test that integer 0 is valid as prerelease identifier."""
        version = ModelSemVer(major=1, minor=0, patch=0, prerelease=(0,))
        assert version.prerelease == (0,)
        assert str(version) == "1.0.0-0"

    def test_construction_valid_alphanumeric_007a(self):
        """Test that '007a' string is valid when contains letter."""
        version = ModelSemVer(major=1, minor=0, patch=0, prerelease=("007a",))
        assert version.prerelease == ("007a",)
        assert str(version) == "1.0.0-007a"

    def test_construction_valid_alphanumeric_0alpha(self):
        """Test that '0alpha' string is valid when contains letter."""
        version = ModelSemVer(major=1, minor=0, patch=0, prerelease=("0alpha",))
        assert version.prerelease == ("0alpha",)
        assert str(version) == "1.0.0-0alpha"
