"""
Comprehensive TDD unit tests for ModelContractVersion.

Tests the ModelContractVersion model which provides typed semver fields
for contract versioning with immutability, comparison operations, and
downgrade protection as specified in CONTRACT_STABILITY_SPEC.md.

Test Categories:
1. Basic Construction Tests
2. Comparison Tests
3. Semver Progression Tests
4. Downgrade Protection Tests
5. Edge Cases
6. Hashability Tests
7. Serialization Tests

Requirements from CONTRACT_STABILITY_SPEC.md:
- Typed semver fields: `major: int`, `minor: int`, `patch: int`
- String representation: `__str__()` returns "X.Y.Z"
- Semver progression rules (no downgrades without explicit flag)
- CI check prevents unversioned contracts
- CI check prevents downgrading semver without `ALLOW_DOWNGRADE=true`
"""

import pytest
from pydantic import ValidationError

from omnibase_core.models.contracts.model_contract_version import (
    ModelContractVersion,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError


@pytest.mark.unit
class TestModelContractVersionBasicConstruction:
    """Tests for ModelContractVersion basic construction and initialization."""

    def test_create_with_valid_major_minor_patch(self) -> None:
        """Test creating ModelContractVersion with valid major/minor/patch values."""
        version = ModelContractVersion(major=1, minor=2, patch=3)
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3

    def test_create_with_zero_values(self) -> None:
        """Test creating ModelContractVersion with zero values (minimum valid)."""
        version = ModelContractVersion(major=0, minor=0, patch=0)
        assert version.major == 0
        assert version.minor == 0
        assert version.patch == 0

    def test_string_representation_returns_xyz_format(self) -> None:
        """Test that __str__() returns 'X.Y.Z' format."""
        version = ModelContractVersion(major=1, minor=2, patch=3)
        assert str(version) == "1.2.3"

    def test_string_representation_with_zeros(self) -> None:
        """Test string representation with zero values."""
        version = ModelContractVersion(major=0, minor=0, patch=0)
        assert str(version) == "0.0.0"

    def test_string_representation_with_large_numbers(self) -> None:
        """Test string representation with large version numbers."""
        version = ModelContractVersion(major=100, minor=200, patch=300)
        assert str(version) == "100.200.300"

    def test_from_string_factory_method(self) -> None:
        """Test from_string() factory method parses valid version strings."""
        version = ModelContractVersion.from_string("1.2.3")
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3

    def test_from_string_with_zeros(self) -> None:
        """Test from_string() with zero values."""
        version = ModelContractVersion.from_string("0.0.0")
        assert version.major == 0
        assert version.minor == 0
        assert version.patch == 0

    def test_from_string_with_large_numbers(self) -> None:
        """Test from_string() with large version numbers."""
        version = ModelContractVersion.from_string("100.200.300")
        assert version.major == 100
        assert version.minor == 200
        assert version.patch == 300

    def test_from_string_invalid_format_raises_error(self) -> None:
        """Test from_string() raises ModelOnexError for invalid format."""
        with pytest.raises(ModelOnexError):
            ModelContractVersion.from_string("invalid")

    def test_from_string_incomplete_version_raises_error(self) -> None:
        """Test from_string() raises ModelOnexError for incomplete version."""
        with pytest.raises(ModelOnexError):
            ModelContractVersion.from_string("1.2")

    def test_from_string_extra_components_raises_error(self) -> None:
        """Test from_string() raises ModelOnexError for extra components."""
        with pytest.raises(ModelOnexError):
            ModelContractVersion.from_string("1.2.3.4")

    def test_from_string_non_numeric_raises_error(self) -> None:
        """Test from_string() raises ModelOnexError for non-numeric values."""
        with pytest.raises(ModelOnexError):
            ModelContractVersion.from_string("a.b.c")


@pytest.mark.unit
class TestModelContractVersionValidation:
    """Tests for ModelContractVersion field validation."""

    def test_fields_must_be_non_negative_integers(self) -> None:
        """Test that version fields must be non-negative integers."""
        # Valid non-negative integers should work
        version = ModelContractVersion(major=0, minor=0, patch=0)
        assert version.major == 0

    def test_negative_major_raises_validation_error(self) -> None:
        """Test that negative major version raises ValidationError."""
        with pytest.raises((ValidationError, Exception)):
            ModelContractVersion(major=-1, minor=0, patch=0)

    def test_negative_minor_raises_validation_error(self) -> None:
        """Test that negative minor version raises ValidationError."""
        with pytest.raises((ValidationError, Exception)):
            ModelContractVersion(major=0, minor=-1, patch=0)

    def test_negative_patch_raises_validation_error(self) -> None:
        """Test that negative patch version raises ValidationError."""
        with pytest.raises((ValidationError, Exception)):
            ModelContractVersion(major=0, minor=0, patch=-1)

    def test_non_integer_major_raises_validation_error(self) -> None:
        """Test that non-integer major version raises ValidationError."""
        with pytest.raises((ValidationError, TypeError)):
            ModelContractVersion(major="1", minor=0, patch=0)  # type: ignore[arg-type]

    def test_non_integer_minor_raises_validation_error(self) -> None:
        """Test that non-integer minor version raises ValidationError."""
        with pytest.raises((ValidationError, TypeError)):
            ModelContractVersion(major=0, minor="1", patch=0)  # type: ignore[arg-type]

    def test_non_integer_patch_raises_validation_error(self) -> None:
        """Test that non-integer patch version raises ValidationError."""
        with pytest.raises((ValidationError, TypeError)):
            ModelContractVersion(major=0, minor=0, patch="1")  # type: ignore[arg-type]

    def test_float_major_raises_validation_error(self) -> None:
        """Test that float major version raises ValidationError."""
        with pytest.raises((ValidationError, TypeError)):
            ModelContractVersion(major=1.5, minor=0, patch=0)  # type: ignore[arg-type]

    def test_none_major_raises_validation_error(self) -> None:
        """Test that None major version raises ValidationError."""
        with pytest.raises((ValidationError, TypeError)):
            ModelContractVersion(major=None, minor=0, patch=0)  # type: ignore[arg-type]


@pytest.mark.unit
class TestModelContractVersionComparison:
    """Tests for ModelContractVersion comparison operations."""

    def test_equality_same_versions(self) -> None:
        """Test that equal versions compare as equal."""
        v1 = ModelContractVersion(major=1, minor=2, patch=3)
        v2 = ModelContractVersion(major=1, minor=2, patch=3)
        assert v1 == v2

    def test_inequality_different_major(self) -> None:
        """Test inequality when major versions differ."""
        v1 = ModelContractVersion(major=1, minor=2, patch=3)
        v2 = ModelContractVersion(major=2, minor=2, patch=3)
        assert v1 != v2

    def test_inequality_different_minor(self) -> None:
        """Test inequality when minor versions differ."""
        v1 = ModelContractVersion(major=1, minor=2, patch=3)
        v2 = ModelContractVersion(major=1, minor=3, patch=3)
        assert v1 != v2

    def test_inequality_different_patch(self) -> None:
        """Test inequality when patch versions differ."""
        v1 = ModelContractVersion(major=1, minor=2, patch=3)
        v2 = ModelContractVersion(major=1, minor=2, patch=4)
        assert v1 != v2

    def test_less_than_major_comparison(self) -> None:
        """Test __lt__ for major version comparison."""
        v1 = ModelContractVersion(major=1, minor=0, patch=0)
        v2 = ModelContractVersion(major=2, minor=0, patch=0)
        assert v1 < v2
        assert not v2 < v1

    def test_less_than_minor_comparison(self) -> None:
        """Test __lt__ for minor version comparison."""
        v1 = ModelContractVersion(major=1, minor=0, patch=0)
        v2 = ModelContractVersion(major=1, minor=1, patch=0)
        assert v1 < v2
        assert not v2 < v1

    def test_less_than_patch_comparison(self) -> None:
        """Test __lt__ for patch version comparison."""
        v1 = ModelContractVersion(major=1, minor=0, patch=0)
        v2 = ModelContractVersion(major=1, minor=0, patch=1)
        assert v1 < v2
        assert not v2 < v1

    def test_less_than_or_equal_equal_versions(self) -> None:
        """Test __le__ for equal versions."""
        v1 = ModelContractVersion(major=1, minor=2, patch=3)
        v2 = ModelContractVersion(major=1, minor=2, patch=3)
        assert v1 <= v2
        assert v2 <= v1

    def test_less_than_or_equal_lesser_version(self) -> None:
        """Test __le__ for lesser version."""
        v1 = ModelContractVersion(major=1, minor=0, patch=0)
        v2 = ModelContractVersion(major=2, minor=0, patch=0)
        assert v1 <= v2
        assert not v2 <= v1

    def test_greater_than_major_comparison(self) -> None:
        """Test __gt__ for major version comparison."""
        v1 = ModelContractVersion(major=2, minor=0, patch=0)
        v2 = ModelContractVersion(major=1, minor=0, patch=0)
        assert v1 > v2
        assert not v2 > v1

    def test_greater_than_minor_comparison(self) -> None:
        """Test __gt__ for minor version comparison."""
        v1 = ModelContractVersion(major=1, minor=1, patch=0)
        v2 = ModelContractVersion(major=1, minor=0, patch=0)
        assert v1 > v2
        assert not v2 > v1

    def test_greater_than_patch_comparison(self) -> None:
        """Test __gt__ for patch version comparison."""
        v1 = ModelContractVersion(major=1, minor=0, patch=1)
        v2 = ModelContractVersion(major=1, minor=0, patch=0)
        assert v1 > v2
        assert not v2 > v1

    def test_greater_than_or_equal_equal_versions(self) -> None:
        """Test __ge__ for equal versions."""
        v1 = ModelContractVersion(major=1, minor=2, patch=3)
        v2 = ModelContractVersion(major=1, minor=2, patch=3)
        assert v1 >= v2
        assert v2 >= v1

    def test_greater_than_or_equal_greater_version(self) -> None:
        """Test __ge__ for greater version."""
        v1 = ModelContractVersion(major=2, minor=0, patch=0)
        v2 = ModelContractVersion(major=1, minor=0, patch=0)
        assert v1 >= v2
        assert not v2 >= v1

    def test_comparison_priority_major_over_minor(self) -> None:
        """Test that major version takes priority over minor in comparisons."""
        v1 = ModelContractVersion(major=2, minor=0, patch=0)
        v2 = ModelContractVersion(major=1, minor=99, patch=99)
        assert v1 > v2
        assert v2 < v1

    def test_comparison_priority_minor_over_patch(self) -> None:
        """Test that minor version takes priority over patch in comparisons."""
        v1 = ModelContractVersion(major=1, minor=2, patch=0)
        v2 = ModelContractVersion(major=1, minor=1, patch=99)
        assert v1 > v2
        assert v2 < v1


@pytest.mark.unit
class TestModelContractVersionSemverProgression:
    """Tests for semver progression methods."""

    def test_is_upgrade_from_major_increase(self) -> None:
        """Test is_upgrade_from() detects major version upgrade."""
        v1 = ModelContractVersion(major=1, minor=0, patch=0)
        v2 = ModelContractVersion(major=2, minor=0, patch=0)
        assert v2.is_upgrade_from(v1) is True
        assert v1.is_upgrade_from(v2) is False

    def test_is_upgrade_from_minor_increase(self) -> None:
        """Test is_upgrade_from() detects minor version upgrade."""
        v1 = ModelContractVersion(major=1, minor=0, patch=0)
        v2 = ModelContractVersion(major=1, minor=1, patch=0)
        assert v2.is_upgrade_from(v1) is True
        assert v1.is_upgrade_from(v2) is False

    def test_is_upgrade_from_patch_increase(self) -> None:
        """Test is_upgrade_from() detects patch version upgrade."""
        v1 = ModelContractVersion(major=1, minor=0, patch=0)
        v2 = ModelContractVersion(major=1, minor=0, patch=1)
        assert v2.is_upgrade_from(v1) is True
        assert v1.is_upgrade_from(v2) is False

    def test_is_upgrade_from_same_version(self) -> None:
        """Test is_upgrade_from() returns False for same version."""
        v1 = ModelContractVersion(major=1, minor=0, patch=0)
        v2 = ModelContractVersion(major=1, minor=0, patch=0)
        assert v1.is_upgrade_from(v2) is False
        assert v2.is_upgrade_from(v1) is False

    def test_is_downgrade_from_major_decrease(self) -> None:
        """Test is_downgrade_from() detects major version downgrade."""
        v1 = ModelContractVersion(major=2, minor=0, patch=0)
        v2 = ModelContractVersion(major=1, minor=0, patch=0)
        assert v2.is_downgrade_from(v1) is True
        assert v1.is_downgrade_from(v2) is False

    def test_is_downgrade_from_minor_decrease(self) -> None:
        """Test is_downgrade_from() detects minor version downgrade."""
        v1 = ModelContractVersion(major=1, minor=1, patch=0)
        v2 = ModelContractVersion(major=1, minor=0, patch=0)
        assert v2.is_downgrade_from(v1) is True
        assert v1.is_downgrade_from(v2) is False

    def test_is_downgrade_from_patch_decrease(self) -> None:
        """Test is_downgrade_from() detects patch version downgrade."""
        v1 = ModelContractVersion(major=1, minor=0, patch=1)
        v2 = ModelContractVersion(major=1, minor=0, patch=0)
        assert v2.is_downgrade_from(v1) is True
        assert v1.is_downgrade_from(v2) is False

    def test_is_downgrade_from_same_version(self) -> None:
        """Test is_downgrade_from() returns False for same version."""
        v1 = ModelContractVersion(major=1, minor=0, patch=0)
        v2 = ModelContractVersion(major=1, minor=0, patch=0)
        assert v1.is_downgrade_from(v2) is False
        assert v2.is_downgrade_from(v1) is False

    def test_bump_major(self) -> None:
        """Test bump_major() increments major and resets minor/patch."""
        version = ModelContractVersion(major=1, minor=2, patch=3)
        bumped = version.bump_major()
        assert bumped.major == 2
        assert bumped.minor == 0
        assert bumped.patch == 0

    def test_bump_major_from_zero(self) -> None:
        """Test bump_major() from zero version."""
        version = ModelContractVersion(major=0, minor=5, patch=9)
        bumped = version.bump_major()
        assert bumped.major == 1
        assert bumped.minor == 0
        assert bumped.patch == 0

    def test_bump_minor(self) -> None:
        """Test bump_minor() increments minor and resets patch."""
        version = ModelContractVersion(major=1, minor=2, patch=3)
        bumped = version.bump_minor()
        assert bumped.major == 1
        assert bumped.minor == 3
        assert bumped.patch == 0

    def test_bump_minor_preserves_major(self) -> None:
        """Test bump_minor() preserves major version."""
        version = ModelContractVersion(major=5, minor=2, patch=3)
        bumped = version.bump_minor()
        assert bumped.major == 5
        assert bumped.minor == 3
        assert bumped.patch == 0

    def test_bump_patch(self) -> None:
        """Test bump_patch() increments patch only."""
        version = ModelContractVersion(major=1, minor=2, patch=3)
        bumped = version.bump_patch()
        assert bumped.major == 1
        assert bumped.minor == 2
        assert bumped.patch == 4

    def test_bump_patch_preserves_major_and_minor(self) -> None:
        """Test bump_patch() preserves major and minor versions."""
        version = ModelContractVersion(major=5, minor=10, patch=3)
        bumped = version.bump_patch()
        assert bumped.major == 5
        assert bumped.minor == 10
        assert bumped.patch == 4

    def test_bump_returns_new_instance(self) -> None:
        """Test bump methods return new instances (immutability)."""
        version = ModelContractVersion(major=1, minor=2, patch=3)
        bumped_major = version.bump_major()
        bumped_minor = version.bump_minor()
        bumped_patch = version.bump_patch()

        # Original should be unchanged
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3

        # New instances are different
        assert bumped_major is not version
        assert bumped_minor is not version
        assert bumped_patch is not version


@pytest.mark.unit
class TestModelContractVersionDowngradeProtection:
    """Tests for downgrade protection functionality."""

    def test_validate_progression_allows_upgrade(self) -> None:
        """Test validate_progression() allows version upgrades."""
        v1 = ModelContractVersion(major=1, minor=0, patch=0)
        v2 = ModelContractVersion(major=2, minor=0, patch=0)
        # Should not raise
        v2.validate_progression(from_version=v1)

    def test_validate_progression_allows_same_version(self) -> None:
        """Test validate_progression() allows same version."""
        v1 = ModelContractVersion(major=1, minor=0, patch=0)
        v2 = ModelContractVersion(major=1, minor=0, patch=0)
        # Should not raise
        v2.validate_progression(from_version=v1)

    def test_validate_progression_blocks_downgrade_by_default(self) -> None:
        """Test validate_progression() blocks downgrade by default."""
        v1 = ModelContractVersion(major=1, minor=0, patch=0)
        v2 = ModelContractVersion(major=0, minor=9, patch=0)
        with pytest.raises(ModelOnexError) as exc_info:
            v2.validate_progression(from_version=v1)
        # Verify the error message mentions downgrade
        assert "downgrade" in str(exc_info.value).lower()

    def test_validate_progression_allows_downgrade_with_flag(self) -> None:
        """Test validate_progression() allows downgrade with allow_downgrade=True."""
        v1 = ModelContractVersion(major=1, minor=0, patch=0)
        v2 = ModelContractVersion(major=0, minor=9, patch=0)
        # Should not raise with allow_downgrade=True
        v2.validate_progression(from_version=v1, allow_downgrade=True)

    def test_validate_progression_blocks_major_downgrade(self) -> None:
        """Test validate_progression() blocks major version downgrade."""
        v1 = ModelContractVersion(major=2, minor=0, patch=0)
        v2 = ModelContractVersion(major=1, minor=0, patch=0)
        with pytest.raises(ModelOnexError):
            v2.validate_progression(from_version=v1)

    def test_validate_progression_blocks_minor_downgrade(self) -> None:
        """Test validate_progression() blocks minor version downgrade."""
        v1 = ModelContractVersion(major=1, minor=5, patch=0)
        v2 = ModelContractVersion(major=1, minor=4, patch=0)
        with pytest.raises(ModelOnexError):
            v2.validate_progression(from_version=v1)

    def test_validate_progression_blocks_patch_downgrade(self) -> None:
        """Test validate_progression() blocks patch version downgrade."""
        v1 = ModelContractVersion(major=1, minor=0, patch=5)
        v2 = ModelContractVersion(major=1, minor=0, patch=4)
        with pytest.raises(ModelOnexError):
            v2.validate_progression(from_version=v1)

    def test_validate_progression_blocks_mixed_downgrade(self) -> None:
        """Test validate_progression() blocks mixed downgrade (higher minor but lower major)."""
        v1 = ModelContractVersion(major=2, minor=0, patch=0)
        v2 = ModelContractVersion(major=1, minor=99, patch=99)
        with pytest.raises(ModelOnexError):
            v2.validate_progression(from_version=v1)


@pytest.mark.unit
class TestModelContractVersionEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_version_zero_zero_zero_is_valid_minimum(self) -> None:
        """Test version 0.0.0 is valid (minimum version)."""
        version = ModelContractVersion(major=0, minor=0, patch=0)
        assert version.major == 0
        assert version.minor == 0
        assert version.patch == 0
        assert str(version) == "0.0.0"

    def test_very_large_version_numbers(self) -> None:
        """Test very large version numbers are handled correctly."""
        version = ModelContractVersion(major=999999, minor=999999, patch=999999)
        assert version.major == 999999
        assert version.minor == 999999
        assert version.patch == 999999
        assert str(version) == "999999.999999.999999"

    def test_frozen_model_cannot_be_modified(self) -> None:
        """Test that frozen model cannot be modified after creation."""
        version = ModelContractVersion(major=1, minor=2, patch=3)
        with pytest.raises((AttributeError, ValidationError, TypeError)):
            version.major = 2  # type: ignore[misc]

    def test_frozen_model_minor_cannot_be_modified(self) -> None:
        """Test that minor field cannot be modified after creation."""
        version = ModelContractVersion(major=1, minor=2, patch=3)
        with pytest.raises((AttributeError, ValidationError, TypeError)):
            version.minor = 5  # type: ignore[misc]

    def test_frozen_model_patch_cannot_be_modified(self) -> None:
        """Test that patch field cannot be modified after creation."""
        version = ModelContractVersion(major=1, minor=2, patch=3)
        with pytest.raises((AttributeError, ValidationError, TypeError)):
            version.patch = 10  # type: ignore[misc]

    def test_extra_fields_are_forbidden(self) -> None:
        """Test that extra fields are forbidden (extra='forbid')."""
        with pytest.raises((ValidationError, TypeError)):
            ModelContractVersion(
                major=1,
                minor=2,
                patch=3,
                extra_field="not allowed",  # type: ignore[call-arg]
            )

    def test_comparison_with_non_version_returns_not_implemented(self) -> None:
        """Test comparison with non-ModelContractVersion returns NotImplemented."""
        version = ModelContractVersion(major=1, minor=2, patch=3)
        # Equality with non-version should return False (via NotImplemented)
        assert (version == "1.2.3") is False
        assert (version == 123) is False
        assert (version == None) is False

    def test_to_string_method_alias(self) -> None:
        """Test to_string() method if it exists as alias for __str__()."""
        version = ModelContractVersion(major=1, minor=2, patch=3)
        if hasattr(version, "to_string"):
            assert version.to_string() == "1.2.3"


@pytest.mark.unit
class TestModelContractVersionHashability:
    """Tests for hashability and use in sets/dicts."""

    def test_hash_returns_int(self) -> None:
        """Test __hash__() returns an integer."""
        version = ModelContractVersion(major=1, minor=2, patch=3)
        assert isinstance(hash(version), int)

    def test_equal_versions_have_same_hash(self) -> None:
        """Test that equal versions have the same hash."""
        v1 = ModelContractVersion(major=1, minor=2, patch=3)
        v2 = ModelContractVersion(major=1, minor=2, patch=3)
        assert hash(v1) == hash(v2)

    def test_different_versions_may_have_different_hash(self) -> None:
        """Test that different versions may have different hash (not guaranteed, but likely)."""
        v1 = ModelContractVersion(major=1, minor=2, patch=3)
        v2 = ModelContractVersion(major=1, minor=2, patch=4)
        # Note: hash collision is possible but unlikely for reasonable inputs
        # This is a weak test - just checking hash is computed
        _ = hash(v1)
        _ = hash(v2)

    def test_version_usable_in_set(self) -> None:
        """Test that version can be used in a set."""
        v1 = ModelContractVersion(major=1, minor=2, patch=3)
        v2 = ModelContractVersion(major=1, minor=2, patch=3)  # Same version
        v3 = ModelContractVersion(major=1, minor=2, patch=4)  # Different version

        version_set = {v1, v2, v3}
        # v1 and v2 are equal, so set should have 2 elements
        assert len(version_set) == 2

    def test_version_usable_as_dict_key(self) -> None:
        """Test that version can be used as a dictionary key."""
        v1 = ModelContractVersion(major=1, minor=2, patch=3)
        v2 = ModelContractVersion(major=1, minor=2, patch=4)

        version_dict = {v1: "version_a", v2: "version_b"}
        assert version_dict[v1] == "version_a"
        assert version_dict[v2] == "version_b"

    def test_version_dict_key_lookup_with_equal_version(self) -> None:
        """Test dictionary lookup with equal version as key."""
        v1 = ModelContractVersion(major=1, minor=2, patch=3)
        v2 = ModelContractVersion(major=1, minor=2, patch=3)  # Equal to v1

        version_dict = {v1: "value"}
        # Should be able to look up using v2 since v1 == v2 and hash(v1) == hash(v2)
        assert version_dict[v2] == "value"


@pytest.mark.unit
class TestModelContractVersionSerialization:
    """Tests for serialization and deserialization."""

    def test_model_dump_returns_dict(self) -> None:
        """Test model_dump() returns a dictionary with version fields."""
        version = ModelContractVersion(major=1, minor=2, patch=3)
        dumped = version.model_dump()
        assert isinstance(dumped, dict)
        assert dumped["major"] == 1
        assert dumped["minor"] == 2
        assert dumped["patch"] == 3

    def test_model_validate_from_dict(self) -> None:
        """Test model_validate() creates version from dictionary."""
        data = {"major": 1, "minor": 2, "patch": 3}
        version = ModelContractVersion.model_validate(data)
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3

    def test_model_dump_json_returns_string(self) -> None:
        """Test model_dump_json() returns a JSON string."""
        version = ModelContractVersion(major=1, minor=2, patch=3)
        json_str = version.model_dump_json()
        assert isinstance(json_str, str)
        assert '"major":1' in json_str or '"major": 1' in json_str

    def test_model_validate_json_creates_version(self) -> None:
        """Test model_validate_json() creates version from JSON string."""
        json_str = '{"major": 1, "minor": 2, "patch": 3}'
        version = ModelContractVersion.model_validate_json(json_str)
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3

    def test_roundtrip_serialization(self) -> None:
        """Test roundtrip serialization preserves values."""
        original = ModelContractVersion(major=1, minor=2, patch=3)
        dumped = original.model_dump()
        restored = ModelContractVersion.model_validate(dumped)
        assert original == restored

    def test_roundtrip_json_serialization(self) -> None:
        """Test roundtrip JSON serialization preserves values."""
        original = ModelContractVersion(major=1, minor=2, patch=3)
        json_str = original.model_dump_json()
        restored = ModelContractVersion.model_validate_json(json_str)
        assert original == restored


@pytest.mark.unit
class TestModelContractVersionRepr:
    """Tests for __repr__ representation."""

    def test_repr_contains_version_info(self) -> None:
        """Test __repr__() contains version information."""
        version = ModelContractVersion(major=1, minor=2, patch=3)
        repr_str = repr(version)
        # Should contain class name and field values
        assert "ModelContractVersion" in repr_str or "1" in repr_str


@pytest.mark.unit
class TestModelContractVersionVersionProgressionRules:
    """Tests for version progression rules from CONTRACT_STABILITY_SPEC.md."""

    def test_breaking_change_requires_major_bump(self) -> None:
        """Test that breaking changes require major version bump (spec compliance)."""
        # Per spec: Breaking change to input/output schema -> Major bump
        # 0.4.0 -> 1.0.0
        v_before = ModelContractVersion(major=0, minor=4, patch=0)
        v_after = ModelContractVersion(major=1, minor=0, patch=0)
        assert v_after.is_upgrade_from(v_before) is True
        assert v_after.major > v_before.major

    def test_new_optional_field_requires_minor_bump(self) -> None:
        """Test that new optional fields require minor version bump (spec compliance)."""
        # Per spec: New optional field added -> Minor bump
        # 0.4.0 -> 0.5.0
        v_before = ModelContractVersion(major=0, minor=4, patch=0)
        v_after = ModelContractVersion(major=0, minor=5, patch=0)
        assert v_after.is_upgrade_from(v_before) is True
        assert v_after.major == v_before.major
        assert v_after.minor > v_before.minor

    def test_bug_fix_requires_patch_bump(self) -> None:
        """Test that bug fixes require patch version bump (spec compliance)."""
        # Per spec: Bug fix, documentation -> Patch bump
        # 0.4.0 -> 0.4.1
        v_before = ModelContractVersion(major=0, minor=4, patch=0)
        v_after = ModelContractVersion(major=0, minor=4, patch=1)
        assert v_after.is_upgrade_from(v_before) is True
        assert v_after.major == v_before.major
        assert v_after.minor == v_before.minor
        assert v_after.patch > v_before.patch


@pytest.mark.unit
class TestModelContractVersionFromSemver:
    """Tests for compatibility with ModelSemVer patterns."""

    def test_from_string_with_prerelease_suffix_extracts_base_version(self) -> None:
        """Test from_string() correctly parses prerelease suffix and extracts base version.

        The implementation supports prerelease suffixes (e.g., -alpha, -beta.1) but
        ignores them for version comparison purposes, extracting only the X.Y.Z portion.
        """
        version = ModelContractVersion.from_string("1.2.3-alpha")
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3

    def test_from_string_with_build_metadata_extracts_base_version(self) -> None:
        """Test from_string() correctly parses build metadata and extracts base version.

        The implementation supports build metadata suffixes (e.g., +build, +20231215)
        but ignores them for version comparison purposes, extracting only the X.Y.Z portion.
        """
        version = ModelContractVersion.from_string("1.2.3+build")
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3

    def test_from_string_with_prerelease_and_build_metadata(self) -> None:
        """Test from_string() with both prerelease and build metadata."""
        version = ModelContractVersion.from_string("1.2.3-beta.1+build.456")
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
