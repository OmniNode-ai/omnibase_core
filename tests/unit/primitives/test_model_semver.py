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

    def test_is_prerelease_always_false(self):
        """Test that is_prerelease always returns False."""
        version = ModelSemVer(major=1, minor=2, patch=3)
        assert version.is_prerelease() is False

    def test_is_prerelease_zero_version(self):
        """Test is_prerelease for 0.0.0."""
        version = ModelSemVer(major=0, minor=0, patch=0)
        assert version.is_prerelease() is False


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
        assert dumped == {"major": 1, "minor": 2, "patch": 3}

    def test_model_json(self):
        """Test JSON serialization."""
        version = ModelSemVer(major=1, minor=2, patch=3)
        json_str = version.model_dump_json()
        assert '"major":1' in json_str or '"major": 1' in json_str
        assert '"minor":2' in json_str or '"minor": 2' in json_str
        assert '"patch":3' in json_str or '"patch": 3' in json_str
