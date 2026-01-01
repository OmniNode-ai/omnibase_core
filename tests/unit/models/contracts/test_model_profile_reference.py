# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Tests for ModelProfileReference."""

import pytest
from pydantic import ValidationError

from omnibase_core.models.contracts.model_profile_reference import ModelProfileReference
from omnibase_core.models.primitives.model_semver import ModelSemVer


@pytest.mark.unit
class TestModelProfileReference:
    """Tests for ModelProfileReference model."""

    @pytest.mark.unit
    def test_valid_profile_reference(self) -> None:
        """Test creating a valid profile reference."""
        ref = ModelProfileReference(
            profile="compute_pure",
            version="1.0.0",
        )
        assert ref.profile == "compute_pure"
        assert ref.version == "1.0.0"

    @pytest.mark.unit
    def test_various_profile_names(self) -> None:
        """Test various valid profile name formats."""
        profiles = [
            "compute_pure",
            "effect_http",
            "orchestrator_safe",
            "reducer_fsm",
            "my_custom_profile",
        ]
        for profile in profiles:
            ref = ModelProfileReference(profile=profile, version="1.0.0")
            assert ref.profile == profile

    @pytest.mark.unit
    def test_various_version_formats(self) -> None:
        """Test various valid version formats."""
        versions = [
            "1.0.0",
            "2.1.3",
            "0.1.0-alpha",
            "^1.0",
            "~1.2.3",
            ">=1.0.0",
        ]
        for version in versions:
            ref = ModelProfileReference(profile="test", version=version)
            assert ref.version == version

    @pytest.mark.unit
    def test_profile_required(self) -> None:
        """Test that profile is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelProfileReference(version="1.0.0")  # type: ignore[call-arg]
        assert "profile" in str(exc_info.value)

    @pytest.mark.unit
    def test_version_required(self) -> None:
        """Test that version is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelProfileReference(profile="test")  # type: ignore[call-arg]
        assert "version" in str(exc_info.value)

    @pytest.mark.unit
    def test_empty_profile_rejected(self) -> None:
        """Test that empty profile is rejected."""
        with pytest.raises(ValidationError):
            ModelProfileReference(profile="", version="1.0.0")

    @pytest.mark.unit
    def test_empty_version_rejected(self) -> None:
        """Test that empty version is rejected."""
        with pytest.raises(ValidationError):
            ModelProfileReference(profile="test", version="")

    @pytest.mark.unit
    def test_extra_fields_rejected(self) -> None:
        """Test that extra fields are rejected (extra='forbid')."""
        with pytest.raises(ValidationError) as exc_info:
            ModelProfileReference(
                profile="test",
                version="1.0.0",
                extra_field="not_allowed",  # type: ignore[call-arg]
            )
        assert "extra_field" in str(exc_info.value).lower()

    @pytest.mark.unit
    def test_frozen_model(self) -> None:
        """Test that the model is immutable (frozen=True)."""
        ref = ModelProfileReference(profile="test", version="1.0.0")
        with pytest.raises(ValidationError):
            ref.profile = "changed"  # type: ignore[misc]

    @pytest.mark.unit
    def test_repr(self) -> None:
        """Test string representation."""
        ref = ModelProfileReference(profile="compute_pure", version="1.0.0")
        repr_str = repr(ref)
        assert "compute_pure" in repr_str
        assert "1.0.0" in repr_str

    @pytest.mark.unit
    def test_equality(self) -> None:
        """Test equality comparison."""
        ref1 = ModelProfileReference(profile="test", version="1.0.0")
        ref2 = ModelProfileReference(profile="test", version="1.0.0")
        ref3 = ModelProfileReference(profile="test", version="2.0.0")
        assert ref1 == ref2
        assert ref1 != ref3

    @pytest.mark.unit
    def test_from_dict(self) -> None:
        """Test creating from dictionary."""
        data = {"profile": "compute_pure", "version": "1.0.0"}
        ref = ModelProfileReference.model_validate(data)
        assert ref.profile == "compute_pure"
        assert ref.version == "1.0.0"

    @pytest.mark.unit
    def test_to_dict(self) -> None:
        """Test serializing to dictionary."""
        ref = ModelProfileReference(profile="test", version="1.0.0")
        data = ref.model_dump()
        assert data == {"profile": "test", "version": "1.0.0"}


@pytest.mark.unit
class TestSatisfiesVersion:
    """Tests for the satisfies_version helper method."""

    @pytest.mark.unit
    def test_exact_version_match(self) -> None:
        """Test exact version constraint matching."""
        ref = ModelProfileReference(profile="test", version="1.0.0")
        assert ref.satisfies_version(ModelSemVer(major=1, minor=0, patch=0)) is True
        assert ref.satisfies_version(ModelSemVer(major=1, minor=0, patch=1)) is False
        assert ref.satisfies_version(ModelSemVer(major=1, minor=1, patch=0)) is False
        assert ref.satisfies_version(ModelSemVer(major=2, minor=0, patch=0)) is False

    @pytest.mark.unit
    def test_compatible_version_caret(self) -> None:
        """Test caret (^) compatible version constraint."""
        ref = ModelProfileReference(profile="test", version="^1.0.0")
        # Same major version should pass
        assert ref.satisfies_version(ModelSemVer(major=1, minor=0, patch=0)) is True
        assert ref.satisfies_version(ModelSemVer(major=1, minor=5, patch=3)) is True
        assert ref.satisfies_version(ModelSemVer(major=1, minor=99, patch=99)) is True
        # Different major version should fail
        assert ref.satisfies_version(ModelSemVer(major=0, minor=9, patch=9)) is False
        assert ref.satisfies_version(ModelSemVer(major=2, minor=0, patch=0)) is False

    @pytest.mark.unit
    def test_minimum_version_tilde(self) -> None:
        """Test tilde (~) minimum version constraint."""
        ref = ModelProfileReference(profile="test", version="~1.2.0")
        # At or above the minimum should pass
        assert ref.satisfies_version(ModelSemVer(major=1, minor=2, patch=0)) is True
        assert ref.satisfies_version(ModelSemVer(major=1, minor=2, patch=5)) is True
        assert ref.satisfies_version(ModelSemVer(major=1, minor=3, patch=0)) is True
        assert ref.satisfies_version(ModelSemVer(major=2, minor=0, patch=0)) is True
        # Below minimum should fail
        assert ref.satisfies_version(ModelSemVer(major=1, minor=1, patch=9)) is False
        assert ref.satisfies_version(ModelSemVer(major=0, minor=9, patch=0)) is False

    @pytest.mark.unit
    def test_greater_than_or_equal(self) -> None:
        """Test >= version constraint."""
        ref = ModelProfileReference(profile="test", version=">=1.5.0")
        # At or above minimum
        assert ref.satisfies_version(ModelSemVer(major=1, minor=5, patch=0)) is True
        assert ref.satisfies_version(ModelSemVer(major=1, minor=5, patch=1)) is True
        assert ref.satisfies_version(ModelSemVer(major=2, minor=0, patch=0)) is True
        # Below minimum
        assert ref.satisfies_version(ModelSemVer(major=1, minor=4, patch=9)) is False
        assert ref.satisfies_version(ModelSemVer(major=0, minor=0, patch=1)) is False

    @pytest.mark.unit
    def test_less_than(self) -> None:
        """Test < version constraint."""
        ref = ModelProfileReference(profile="test", version="<2.0.0")
        # Below maximum
        assert ref.satisfies_version(ModelSemVer(major=1, minor=0, patch=0)) is True
        assert ref.satisfies_version(ModelSemVer(major=1, minor=99, patch=99)) is True
        assert ref.satisfies_version(ModelSemVer(major=0, minor=1, patch=0)) is True
        # At or above maximum
        assert ref.satisfies_version(ModelSemVer(major=2, minor=0, patch=0)) is False
        assert ref.satisfies_version(ModelSemVer(major=2, minor=0, patch=1)) is False

    @pytest.mark.unit
    def test_less_than_or_equal(self) -> None:
        """Test <= version constraint."""
        ref = ModelProfileReference(profile="test", version="<=2.0.0")
        # At or below maximum
        assert ref.satisfies_version(ModelSemVer(major=2, minor=0, patch=0)) is True
        assert ref.satisfies_version(ModelSemVer(major=1, minor=99, patch=99)) is True
        # Above maximum
        assert ref.satisfies_version(ModelSemVer(major=2, minor=0, patch=1)) is False

    @pytest.mark.unit
    def test_range_constraint(self) -> None:
        """Test range version constraint (min,max)."""
        ref = ModelProfileReference(profile="test", version=">=1.0.0,<2.0.0")
        # Within range
        assert ref.satisfies_version(ModelSemVer(major=1, minor=0, patch=0)) is True
        assert ref.satisfies_version(ModelSemVer(major=1, minor=5, patch=3)) is True
        assert ref.satisfies_version(ModelSemVer(major=1, minor=99, patch=99)) is True
        # Outside range
        assert ref.satisfies_version(ModelSemVer(major=0, minor=9, patch=9)) is False
        assert ref.satisfies_version(ModelSemVer(major=2, minor=0, patch=0)) is False
        assert ref.satisfies_version(ModelSemVer(major=2, minor=1, patch=0)) is False

    @pytest.mark.unit
    def test_prerelease_versions_not_allowed_by_default(self) -> None:
        """Test that prerelease versions are rejected by default."""
        ref = ModelProfileReference(profile="test", version="^1.0.0")
        # Prerelease version in valid major range
        prerelease = ModelSemVer(major=1, minor=5, patch=0, prerelease=("alpha",))
        assert ref.satisfies_version(prerelease) is False

    @pytest.mark.unit
    def test_boundary_conditions(self) -> None:
        """Test boundary conditions for version constraints."""
        # Exact boundary for exclusive max
        ref_exclusive = ModelProfileReference(profile="test", version=">=1.0.0,<2.0.0")
        assert (
            ref_exclusive.satisfies_version(ModelSemVer(major=1, minor=0, patch=0))
            is True
        )
        assert (
            ref_exclusive.satisfies_version(ModelSemVer(major=2, minor=0, patch=0))
            is False
        )

        # Exact boundary for inclusive max
        ref_inclusive = ModelProfileReference(profile="test", version=">=1.0.0,<=2.0.0")
        assert (
            ref_inclusive.satisfies_version(ModelSemVer(major=2, minor=0, patch=0))
            is True
        )
        assert (
            ref_inclusive.satisfies_version(ModelSemVer(major=2, minor=0, patch=1))
            is False
        )

    @pytest.mark.unit
    def test_zero_version(self) -> None:
        """Test with zero major version (pre-1.0 releases)."""
        ref = ModelProfileReference(profile="test", version="^0.1.0")
        # Zero major compatible range
        assert ref.satisfies_version(ModelSemVer(major=0, minor=1, patch=0)) is True
        assert ref.satisfies_version(ModelSemVer(major=0, minor=5, patch=0)) is True
        assert ref.satisfies_version(ModelSemVer(major=1, minor=0, patch=0)) is False

    @pytest.mark.unit
    def test_parsed_constraint_caching(self) -> None:
        """Test that parsed constraint is cached for efficiency."""
        ref = ModelProfileReference(profile="test", version="^1.0.0")
        # Access the property twice
        constraint1 = ref._parsed_constraint
        constraint2 = ref._parsed_constraint
        # Should be the same cached instance
        assert constraint1 is constraint2

    @pytest.mark.unit
    def test_various_profile_version_combinations(self) -> None:
        """Test version checking with different profile names."""
        profiles_and_versions = [
            ("compute_pure", "1.0.0"),
            ("effect_http", "^2.0.0"),
            ("orchestrator_safe", ">=1.0.0,<3.0.0"),
            ("reducer_fsm", "~0.5.0"),
        ]
        for profile, version in profiles_and_versions:
            ref = ModelProfileReference(profile=profile, version=version)
            # Just verify the method works with valid input
            result = ref.satisfies_version(ModelSemVer(major=1, minor=0, patch=0))
            assert isinstance(result, bool)

    @pytest.mark.unit
    def test_greater_than_exclusive(self) -> None:
        """Test > (exclusive greater than) constraint."""
        ref = ModelProfileReference(profile="test", version=">1.0.0")
        assert ref.satisfies_version(ModelSemVer(major=1, minor=0, patch=0)) is False
        assert ref.satisfies_version(ModelSemVer(major=1, minor=0, patch=1)) is True
        assert ref.satisfies_version(ModelSemVer(major=1, minor=1, patch=0)) is True
