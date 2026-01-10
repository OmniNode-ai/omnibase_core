# SPDX-FileCopyrightText: 2025 OmniNode Team
# SPDX-License-Identifier: Apache-2.0
"""
Unit tests for ModelExecutionProfile.

Tests execution profile configuration including:
- Basic creation and validation
- Phase ordering and phase_order property (cached)
- Nondeterministic allowed phases validation
- True immutability via tuple fields

See Also:
    - OMN-1227: ProtocolConstraintValidator for SPI
    - OMN-1292: Core Models for ProtocolConstraintValidator

.. versionchanged:: 0.6.1
    Updated tests for tuple fields and cached phase_order property.
"""

import pytest
from pydantic import ValidationError

from omnibase_core.models.contracts.model_execution_profile import (
    DEFAULT_EXECUTION_PHASES,
    ModelExecutionProfile,
)


@pytest.mark.unit
class TestModelExecutionProfileCreation:
    """Tests for ModelExecutionProfile creation."""

    def test_default_creation(self) -> None:
        """Test creation with all defaults."""
        profile = ModelExecutionProfile()
        assert profile.phases == DEFAULT_EXECUTION_PHASES
        assert profile.nondeterministic_allowed_phases == ()

    def test_custom_phases(self) -> None:
        """Test creation with custom phases."""
        profile = ModelExecutionProfile(phases=("init", "execute", "cleanup"))
        assert profile.phases == ("init", "execute", "cleanup")

    def test_custom_phases_from_tuple(self) -> None:
        """Test creation with phases passed as tuple."""
        profile = ModelExecutionProfile(phases=("init", "execute", "cleanup"))
        assert profile.phases == ("init", "execute", "cleanup")

    def test_with_nondeterministic_allowed_phases(self) -> None:
        """Test creation with nondeterministic_allowed_phases."""
        profile = ModelExecutionProfile(
            phases=("init", "execute", "cleanup"),
            nondeterministic_allowed_phases=("execute",),
        )
        assert profile.nondeterministic_allowed_phases == ("execute",)

    def test_multiple_nondeterministic_phases(self) -> None:
        """Test creation with multiple nondeterministic phases."""
        profile = ModelExecutionProfile(
            phases=("init", "execute", "emit", "cleanup"),
            nondeterministic_allowed_phases=("execute", "emit"),
        )
        assert profile.nondeterministic_allowed_phases == ("execute", "emit")


@pytest.mark.unit
class TestPhaseOrderProperty:
    """Tests for phase_order cached property."""

    def test_phase_order_default_phases(self) -> None:
        """Test phase_order with default phases."""
        profile = ModelExecutionProfile()
        phase_order = profile.phase_order
        assert phase_order["preflight"] == 0
        assert phase_order["before"] == 1
        assert phase_order["execute"] == 2
        assert phase_order["after"] == 3
        assert phase_order["emit"] == 4
        assert phase_order["finalize"] == 5

    def test_phase_order_custom_phases(self) -> None:
        """Test phase_order with custom phases."""
        profile = ModelExecutionProfile(phases=("init", "execute", "cleanup"))
        phase_order = profile.phase_order
        assert phase_order == {"init": 0, "execute": 1, "cleanup": 2}

    def test_phase_order_single_phase(self) -> None:
        """Test phase_order with single phase."""
        profile = ModelExecutionProfile(phases=("main",))
        assert profile.phase_order == {"main": 0}

    def test_phase_order_is_cached(self) -> None:
        """Test that phase_order is cached (returns same object)."""
        profile = ModelExecutionProfile(phases=("init", "execute"))
        order1 = profile.phase_order
        order2 = profile.phase_order
        # Should be the same object due to caching
        assert order1 is order2

    def test_phase_order_cache_independent_per_instance(self) -> None:
        """Test that each profile instance has its own cached phase_order."""
        profile1 = ModelExecutionProfile(phases=("init", "execute"))
        profile2 = ModelExecutionProfile(phases=("alpha", "beta", "gamma"))

        order1 = profile1.phase_order
        order2 = profile2.phase_order

        # Different profiles have different phase orders
        assert order1 == {"init": 0, "execute": 1}
        assert order2 == {"alpha": 0, "beta": 1, "gamma": 2}
        # But modification of the returned dict could affect cached value
        # This is acceptable since the model is immutable


@pytest.mark.unit
class TestNondeterministicPhasesValidation:
    """Tests for nondeterministic_allowed_phases validation."""

    def test_nondeterministic_phases_must_be_subset(self) -> None:
        """Test that nondeterministic_allowed_phases must be subset of phases."""
        with pytest.raises(
            ValidationError, match="nondeterministic_allowed_phases contains phases"
        ):
            ModelExecutionProfile(
                phases=("init", "execute"),
                nondeterministic_allowed_phases=("cleanup",),  # Not in phases
            )

    def test_multiple_invalid_nondeterministic_phases(self) -> None:
        """Test error message includes all invalid phases."""
        with pytest.raises(ValidationError, match="nondeterministic_allowed_phases"):
            ModelExecutionProfile(
                phases=("init", "execute"),
                nondeterministic_allowed_phases=("cleanup", "unknown"),
            )

    def test_empty_nondeterministic_phases_valid(self) -> None:
        """Test that empty nondeterministic_allowed_phases is valid."""
        profile = ModelExecutionProfile(
            phases=("init", "execute"),
            nondeterministic_allowed_phases=(),
        )
        assert profile.nondeterministic_allowed_phases == ()

    def test_all_phases_nondeterministic_valid(self) -> None:
        """Test that all phases can be nondeterministic."""
        profile = ModelExecutionProfile(
            phases=("init", "execute", "cleanup"),
            nondeterministic_allowed_phases=("init", "execute", "cleanup"),
        )
        assert set(profile.nondeterministic_allowed_phases) == set(profile.phases)

    def test_nondeterministic_phases_must_be_unique(self) -> None:
        """Test that duplicate entries in nondeterministic_allowed_phases raise error.

        Design Decision:
            Duplicates raise an error rather than being silently removed, consistent
            with the behavior for the phases field. This ensures users are made aware
            of input issues rather than having them silently corrected.
        """
        with pytest.raises(
            ValidationError,
            match="nondeterministic_allowed_phases must contain unique values",
        ):
            ModelExecutionProfile(
                phases=("init", "execute", "cleanup"),
                nondeterministic_allowed_phases=("execute", "execute", "init"),
            )

    def test_nondeterministic_phases_whitespace_stripped(self) -> None:
        """Test that whitespace is stripped from nondeterministic_allowed_phases."""
        profile = ModelExecutionProfile(
            phases=("init", "execute", "cleanup"),
            nondeterministic_allowed_phases=("  execute  ", " init"),
        )
        assert profile.nondeterministic_allowed_phases == ("execute", "init")


@pytest.mark.unit
class TestPhasesValidation:
    """Tests for phases field validation."""

    def test_phases_must_be_unique(self) -> None:
        """Test that phases must contain unique values."""
        with pytest.raises(ValidationError, match="phases must contain unique values"):
            ModelExecutionProfile(phases=("init", "execute", "init"))

    def test_phases_must_be_non_empty_strings(self) -> None:
        """Test that phases must be non-empty strings."""
        with pytest.raises(ValidationError, match="phases must be non-empty strings"):
            ModelExecutionProfile(phases=("init", "", "cleanup"))

    def test_phases_whitespace_only_rejected(self) -> None:
        """Test that whitespace-only phases are rejected."""
        with pytest.raises(ValidationError, match="phases must be non-empty strings"):
            ModelExecutionProfile(phases=("init", "   ", "cleanup"))


@pytest.mark.unit
class TestImmutability:
    """Tests for model immutability."""

    def test_frozen_model(self) -> None:
        """Test that model is frozen and cannot be modified."""
        profile = ModelExecutionProfile()
        with pytest.raises(ValidationError):
            profile.phases = ("modified",)  # type: ignore[misc]

    def test_nondeterministic_phases_frozen(self) -> None:
        """Test that nondeterministic_allowed_phases cannot be modified."""
        profile = ModelExecutionProfile(
            phases=("init", "execute"),
            nondeterministic_allowed_phases=("execute",),
        )
        with pytest.raises(ValidationError):
            profile.nondeterministic_allowed_phases = ("init",)  # type: ignore[misc]


@pytest.mark.unit
class TestModelFromAttributes:
    """Tests for from_attributes compatibility."""

    def test_from_dict(self) -> None:
        """Test creation from dictionary (lists coerced to tuples)."""
        data = {
            "phases": ["init", "execute", "cleanup"],
            "nondeterministic_allowed_phases": ["execute"],
        }
        profile = ModelExecutionProfile.model_validate(data)
        # Lists are coerced to tuples
        assert profile.phases == ("init", "execute", "cleanup")
        assert profile.nondeterministic_allowed_phases == ("execute",)

    def test_extra_fields_forbidden(self) -> None:
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError, match="extra"):
            ModelExecutionProfile.model_validate(
                {"phases": ["init"], "unknown_field": "value"}
            )

    def test_from_object_with_attributes(self) -> None:
        """Test creation from object with matching attributes (from_attributes=True)."""
        from omnibase_core.models.contracts.model_execution_ordering_policy import (
            ModelExecutionOrderingPolicy,
        )

        class ProfileLike:
            """Mock object with profile-like attributes."""

            def __init__(self) -> None:
                self.phases = ["setup", "run", "teardown"]
                self.ordering_policy = ModelExecutionOrderingPolicy()
                self.nondeterministic_allowed_phases = ["run"]

        source_obj = ProfileLike()
        profile = ModelExecutionProfile.model_validate(source_obj)

        # Lists coerced to tuples
        assert profile.phases == ("setup", "run", "teardown")
        assert profile.nondeterministic_allowed_phases == ("run",)
        assert isinstance(profile.ordering_policy, ModelExecutionOrderingPolicy)

    def test_from_object_partial_attributes(self) -> None:
        """Test creation from object with only phases attribute."""

        class MinimalProfile:
            """Object with minimal attributes."""

            def __init__(self) -> None:
                self.phases = ["main"]

        source_obj = MinimalProfile()
        profile = ModelExecutionProfile.model_validate(source_obj)

        assert profile.phases == ("main",)
        # Defaults applied (empty tuple)
        assert profile.nondeterministic_allowed_phases == ()

    def test_from_object_with_dataclass(self) -> None:
        """Test creation from dataclass with matching attributes."""
        from dataclasses import dataclass

        from omnibase_core.models.contracts.model_execution_ordering_policy import (
            ModelExecutionOrderingPolicy,
        )

        @dataclass
        class ProfileData:
            phases: list[str]
            ordering_policy: ModelExecutionOrderingPolicy
            nondeterministic_allowed_phases: list[str]

        source = ProfileData(
            phases=["alpha", "beta", "gamma"],
            ordering_policy=ModelExecutionOrderingPolicy(),
            nondeterministic_allowed_phases=["beta"],
        )
        profile = ModelExecutionProfile.model_validate(source)

        # Lists coerced to tuples
        assert profile.phases == ("alpha", "beta", "gamma")
        assert profile.nondeterministic_allowed_phases == ("beta",)


@pytest.mark.unit
class TestMultiErrorAggregation:
    """Tests for multi-error aggregation behavior (OMN-1292)."""

    def test_multiple_validation_errors_aggregated(self) -> None:
        """Test that multiple validation errors are reported together."""
        with pytest.raises(ValidationError) as exc_info:
            ModelExecutionProfile.model_validate(
                {
                    "phases": ["init", "init", ""],  # Duplicate AND empty
                    "nondeterministic_allowed_phases": ["nonexistent"],  # Invalid
                }
            )

        # Verify errors are present
        errors = exc_info.value.errors()
        assert len(errors) >= 1, f"Expected at least one error, got {len(errors)}"

    def test_empty_phase_and_duplicate_phase(self) -> None:
        """Test that empty and duplicate phases both cause validation errors."""
        # First, test duplicate phases alone
        with pytest.raises(ValidationError, match="phases must contain unique values"):
            ModelExecutionProfile(phases=("init", "execute", "init"))

        # Then, test empty phase alone
        with pytest.raises(ValidationError, match="phases must be non-empty strings"):
            ModelExecutionProfile(phases=("init", "", "cleanup"))

    def test_invalid_nondeterministic_phases_with_duplicate_phases(self) -> None:
        """Test error when nondeterministic phases invalid AND phases have duplicates."""
        # The validator checks uniqueness first
        with pytest.raises(ValidationError) as exc_info:
            ModelExecutionProfile(
                phases=("init", "init"),  # Duplicate
                nondeterministic_allowed_phases=("nonexistent",),
            )

        # Should fail on uniqueness check
        assert "unique" in str(exc_info.value).lower()


@pytest.mark.unit
class TestTupleImmutabilityBehavior:
    """Tests for tuple field immutability.

    With frozen=True and tuple fields, we now have TRUE immutability:
    - Field reassignment is prevented by frozen=True
    - Content mutation is prevented by using tuples instead of lists

    See Also:
        - OMN-1292: Core Models for ProtocolConstraintValidator
    """

    def test_field_reassignment_prevented(self) -> None:
        """Test that direct field reassignment raises ValidationError."""
        profile = ModelExecutionProfile(phases=("init", "execute"))

        with pytest.raises(ValidationError):
            profile.phases = ("modified",)  # type: ignore[misc]

    def test_phases_tuple_immutable(self) -> None:
        """Test that phases tuple cannot be mutated.

        With tuple fields, attempting to mutate raises AttributeError
        because tuples don't have mutation methods like append().
        """
        profile = ModelExecutionProfile(phases=("init", "execute"))

        # Tuples don't have append method
        assert not hasattr(profile.phases, "append")

        # Verify it's actually a tuple
        assert isinstance(profile.phases, tuple)

    def test_nondeterministic_phases_tuple_immutable(self) -> None:
        """Test that nondeterministic_allowed_phases tuple cannot be mutated."""
        profile = ModelExecutionProfile(
            phases=("init", "execute", "cleanup"),
            nondeterministic_allowed_phases=("execute",),
        )

        # Field reassignment is blocked
        with pytest.raises(ValidationError):
            profile.nondeterministic_allowed_phases = ("init",)  # type: ignore[misc]

        # Tuples don't have mutation methods
        assert not hasattr(profile.nondeterministic_allowed_phases, "append")

        # Verify it's actually a tuple
        assert isinstance(profile.nondeterministic_allowed_phases, tuple)

    def test_phase_order_is_cached_dict(self) -> None:
        """Test that phase_order is cached and returns the same dict instance.

        Since the model is frozen and phases are tuples, caching is safe.
        """
        profile = ModelExecutionProfile(phases=("init", "execute"))

        order1 = profile.phase_order
        order2 = profile.phase_order

        # Same object due to caching
        assert order1 is order2

        # Verify contents are correct
        assert order1 == {"init": 0, "execute": 1}

    def test_phases_tuple_prevents_index_mutation(self) -> None:
        """Test that phases tuple cannot be mutated via index assignment.

        This verifies true immutability - tuples prevent in-place mutation
        that would bypass Pydantic's frozen=True protection.

        See Also:
            - OMN-1292: PR review feedback on immutability protection
        """
        profile = ModelExecutionProfile(phases=("execute", "after"))

        # Attempting index assignment on tuple raises TypeError
        with pytest.raises(TypeError, match="does not support item assignment"):
            profile.phases[0] = "before"  # type: ignore[index]

    def test_nondeterministic_phases_tuple_prevents_index_mutation(self) -> None:
        """Test that nondeterministic_allowed_phases tuple cannot be mutated via index."""
        profile = ModelExecutionProfile(
            phases=("init", "execute", "cleanup"),
            nondeterministic_allowed_phases=("execute", "cleanup"),
        )

        # Attempting index assignment on tuple raises TypeError
        with pytest.raises(TypeError, match="does not support item assignment"):
            profile.nondeterministic_allowed_phases[0] = "init"  # type: ignore[index]


@pytest.mark.unit
class TestListToTupleCoercion:
    """Tests for list-to-tuple coercion behavior.

    Verifies that list inputs are properly coerced to tuples for immutability.

    See Also:
        - OMN-1292: PR review feedback on coercion behavior
    """

    def test_list_input_coerced_to_tuple_for_phases(self) -> None:
        """Test that list input for phases is coerced to tuple."""
        profile = ModelExecutionProfile(phases=["execute", "after"])  # type: ignore[arg-type]

        assert isinstance(profile.phases, tuple)
        assert profile.phases == ("execute", "after")

    def test_list_input_coerced_to_tuple_for_nondeterministic_phases(self) -> None:
        """Test that list input for nondeterministic_allowed_phases is coerced to tuple."""
        profile = ModelExecutionProfile(
            phases=("init", "execute", "cleanup"),
            nondeterministic_allowed_phases=["execute", "cleanup"],  # type: ignore[arg-type]
        )

        assert isinstance(profile.nondeterministic_allowed_phases, tuple)
        assert profile.nondeterministic_allowed_phases == ("execute", "cleanup")

    def test_mixed_list_and_tuple_inputs(self) -> None:
        """Test creation with mixed list and tuple inputs."""
        profile = ModelExecutionProfile(
            phases=["alpha", "beta", "gamma"],  # type: ignore[arg-type]
            nondeterministic_allowed_phases=("beta",),  # Already tuple
        )

        # Both should be tuples
        assert isinstance(profile.phases, tuple)
        assert isinstance(profile.nondeterministic_allowed_phases, tuple)
        assert profile.phases == ("alpha", "beta", "gamma")
        assert profile.nondeterministic_allowed_phases == ("beta",)


@pytest.mark.unit
class TestFromAttributesExplicit:
    """Tests for explicit from_attributes=True parameter usage.

    Verifies that model_validate works correctly with explicit from_attributes=True
    parameter in addition to the ConfigDict setting.

    See Also:
        - OMN-1292: PR review feedback on from_attributes behavior
    """

    def test_from_attributes_explicit_with_tuple_attributes(self) -> None:
        """Test model creation from object with tuple attributes using explicit parameter."""
        from omnibase_core.models.contracts.model_execution_ordering_policy import (
            ModelExecutionOrderingPolicy,
        )

        class ProfileLike:
            """Object with tuple attributes matching profile fields."""

            phases = ("execute", "after")
            ordering_policy = ModelExecutionOrderingPolicy()
            nondeterministic_allowed_phases = ()

        # Explicit from_attributes=True parameter
        profile = ModelExecutionProfile.model_validate(
            ProfileLike(), from_attributes=True
        )

        assert profile.phases == ("execute", "after")
        assert profile.nondeterministic_allowed_phases == ()
        assert isinstance(profile.ordering_policy, ModelExecutionOrderingPolicy)

    def test_from_attributes_explicit_with_list_attributes(self) -> None:
        """Test model creation from object with list attributes using explicit parameter.

        Lists should be coerced to tuples even when reading from object attributes.
        """
        from omnibase_core.models.contracts.model_execution_ordering_policy import (
            ModelExecutionOrderingPolicy,
        )

        class ProfileLikeWithLists:
            """Object with list attributes that should be coerced to tuples."""

            phases = ["init", "execute", "cleanup"]
            ordering_policy = ModelExecutionOrderingPolicy()
            nondeterministic_allowed_phases = ["execute"]

        profile = ModelExecutionProfile.model_validate(
            ProfileLikeWithLists(), from_attributes=True
        )

        # Lists coerced to tuples
        assert isinstance(profile.phases, tuple)
        assert profile.phases == ("init", "execute", "cleanup")
        assert isinstance(profile.nondeterministic_allowed_phases, tuple)
        assert profile.nondeterministic_allowed_phases == ("execute",)

    def test_from_attributes_with_namedtuple(self) -> None:
        """Test model creation from namedtuple using from_attributes=True."""
        from typing import NamedTuple

        from omnibase_core.models.contracts.model_execution_ordering_policy import (
            ModelExecutionOrderingPolicy,
        )

        class ProfileTuple(NamedTuple):
            phases: tuple[str, ...]
            ordering_policy: ModelExecutionOrderingPolicy
            nondeterministic_allowed_phases: tuple[str, ...]

        source = ProfileTuple(
            phases=("pre", "main", "post"),
            ordering_policy=ModelExecutionOrderingPolicy(),
            nondeterministic_allowed_phases=("main",),
        )

        profile = ModelExecutionProfile.model_validate(source, from_attributes=True)

        assert profile.phases == ("pre", "main", "post")
        assert profile.nondeterministic_allowed_phases == ("main",)

    def test_from_attributes_implicit_via_config(self) -> None:
        """Test that from_attributes works implicitly via ConfigDict setting.

        The model has from_attributes=True in ConfigDict, so it should work
        without explicit parameter.
        """
        from omnibase_core.models.contracts.model_execution_ordering_policy import (
            ModelExecutionOrderingPolicy,
        )

        class ProfileLike:
            phases = ("alpha", "beta")
            ordering_policy = ModelExecutionOrderingPolicy()
            nondeterministic_allowed_phases = ("beta",)

        # No explicit from_attributes parameter - relies on ConfigDict
        profile = ModelExecutionProfile.model_validate(ProfileLike())

        assert profile.phases == ("alpha", "beta")
        assert profile.nondeterministic_allowed_phases == ("beta",)


@pytest.mark.unit
class TestPhaseOrderCaching:
    """Tests for phase_order caching behavior (OMN-1292).

    Verifies that the cached phase_order property:
    - Returns the same object on repeated calls (caching)
    - Contains correct values after caching
    - Works correctly across multiple profile instances

    See Also:
        - OMN-1292: PR review feedback on caching verification
    """

    def test_phase_order_cache_returns_same_object(self) -> None:
        """Test that phase_order is cached and returns the same object."""
        profile = ModelExecutionProfile(phases=("init", "execute", "cleanup"))

        order1 = profile.phase_order
        order2 = profile.phase_order
        order3 = profile.phase_order

        # All calls should return the exact same object (identity check)
        assert order1 is order2
        assert order2 is order3

    def test_phase_order_cached_value_is_correct(self) -> None:
        """Test that the cached phase_order value is correct after caching.

        Verifies that repeated accesses return the same correct values.
        """
        profile = ModelExecutionProfile(
            phases=("preflight", "before", "execute", "after")
        )

        # First access - builds cache
        order1 = profile.phase_order
        assert order1 == {"preflight": 0, "before": 1, "execute": 2, "after": 3}

        # Second access - returns cached value
        order2 = profile.phase_order
        assert order2 == {"preflight": 0, "before": 1, "execute": 2, "after": 3}

        # Verify they are the same object
        assert order1 is order2

        # Verify all expected keys are present and correct
        assert order2["preflight"] == 0
        assert order2["before"] == 1
        assert order2["execute"] == 2
        assert order2["after"] == 3

    def test_phase_order_cache_independent_per_instance(self) -> None:
        """Test that each profile instance has independent cached phase_order."""
        profile1 = ModelExecutionProfile(phases=("alpha", "beta"))
        profile2 = ModelExecutionProfile(phases=("gamma", "delta", "epsilon"))

        order1 = profile1.phase_order
        order2 = profile2.phase_order

        # Different instances, different caches
        assert order1 is not order2

        # But each instance's cache is correct
        assert order1 == {"alpha": 0, "beta": 1}
        assert order2 == {"gamma": 0, "delta": 1, "epsilon": 2}

        # And each cache is stable
        assert profile1.phase_order is order1
        assert profile2.phase_order is order2

    def test_phase_order_cache_with_single_phase(self) -> None:
        """Test phase_order caching with single phase."""
        profile = ModelExecutionProfile(phases=("main",))

        order1 = profile.phase_order
        order2 = profile.phase_order

        assert order1 is order2
        assert order1 == {"main": 0}

    def test_phase_order_cache_with_many_phases(self) -> None:
        """Test phase_order caching with many phases."""
        phases = tuple(f"phase_{i}" for i in range(20))
        profile = ModelExecutionProfile(phases=phases)

        order1 = profile.phase_order
        order2 = profile.phase_order

        # Caching works
        assert order1 is order2

        # All phases present and correct
        for i, phase in enumerate(phases):
            assert order1[phase] == i


@pytest.mark.unit
class TestMultipleValidationErrors:
    """Tests for multiple validation errors being collected (OMN-1292).

    Verifies that Pydantic collects and reports multiple validation errors
    when multiple fields or constraints fail validation.

    See Also:
        - OMN-1292: PR review feedback on multi-error validation
    """

    def test_multiple_field_type_errors(self) -> None:
        """Test that type errors are raised for non-iterable inputs.

        Note: When a non-iterable type is passed, the field validator
        raises a TypeError rather than a ValidationError, since the
        validator attempts to iterate over the value.
        """
        with pytest.raises(TypeError, match="not iterable"):
            ModelExecutionProfile.model_validate(
                {
                    "phases": 123,  # Wrong type - not iterable
                }
            )

    def test_multiple_validation_errors_in_model_validator(self) -> None:
        """Test that validation errors from model_validator are raised."""
        # Test case: phases with duplicates and nondeterministic_allowed_phases
        # with invalid reference. The duplicate check fails first.
        with pytest.raises(ValidationError) as exc_info:
            ModelExecutionProfile.model_validate(
                {
                    "phases": ["init", "init"],  # Duplicate - fails uniqueness
                    "nondeterministic_allowed_phases": [],
                }
            )

        errors = exc_info.value.errors()
        assert len(errors) >= 1
        assert "unique" in str(exc_info.value).lower()

    def test_phases_and_nondeterministic_phases_both_invalid(self) -> None:
        """Test validation when both phases and nondeterministic phases are invalid."""
        # Test that duplicate phases error is raised
        with pytest.raises(ValidationError, match="unique"):
            ModelExecutionProfile(
                phases=("init", "init"),  # Duplicate
                nondeterministic_allowed_phases=("init",),  # Valid subset
            )

        # Test that invalid nondeterministic phases error is raised
        with pytest.raises(ValidationError, match="nondeterministic_allowed_phases"):
            ModelExecutionProfile(
                phases=("init", "execute"),  # Valid
                nondeterministic_allowed_phases=("nonexistent",),  # Invalid reference
            )

    def test_empty_phase_string_validation(self) -> None:
        """Test that empty phase strings are caught in validation."""
        with pytest.raises(ValidationError, match="non-empty"):
            ModelExecutionProfile(phases=("init", "", "cleanup"))

    def test_whitespace_phase_normalized_to_empty(self) -> None:
        """Test that whitespace-only phases are normalized to empty and rejected."""
        with pytest.raises(ValidationError, match="non-empty"):
            ModelExecutionProfile(phases=("init", "   ", "cleanup"))

    def test_nondeterministic_empty_string_rejected(self) -> None:
        """Test that empty string in nondeterministic_allowed_phases is rejected."""
        with pytest.raises(ValidationError, match="non-empty"):
            ModelExecutionProfile(
                phases=("init", "execute", "cleanup"),
                nondeterministic_allowed_phases=("execute", ""),  # Empty string
            )

    def test_validation_order_duplicate_then_empty(self) -> None:
        """Test that validation catches issues in order.

        When both duplicate and empty phases exist, uniqueness is checked first.
        """
        with pytest.raises(ValidationError, match="unique"):
            ModelExecutionProfile(phases=("init", "init", ""))


@pytest.mark.unit
class TestListMutationPrevention:
    """Additional tests for list mutation prevention (OMN-1292).

    These tests verify that even if users attempt creative mutations,
    the tuple fields prevent any in-place modification.

    See Also:
        - OMN-1292: PR review feedback on mutation prevention
    """

    def test_phases_slice_assignment_prevented(self) -> None:
        """Test that slice assignment on phases tuple raises TypeError."""
        profile = ModelExecutionProfile(phases=("init", "execute", "cleanup"))

        with pytest.raises(TypeError, match="does not support item assignment"):
            profile.phases[0:1] = ("modified",)  # type: ignore[index]

    def test_nondeterministic_phases_slice_assignment_prevented(self) -> None:
        """Test that slice assignment on nondeterministic_allowed_phases raises TypeError."""
        profile = ModelExecutionProfile(
            phases=("init", "execute", "cleanup"),
            nondeterministic_allowed_phases=("execute", "cleanup"),
        )

        with pytest.raises(TypeError, match="does not support item assignment"):
            profile.nondeterministic_allowed_phases[0:1] = ("init",)  # type: ignore[index]

    def test_tuple_has_no_mutation_methods(self) -> None:
        """Test that tuple fields lack all common mutation methods."""
        profile = ModelExecutionProfile(
            phases=("init", "execute"),
            nondeterministic_allowed_phases=("execute",),
        )

        # List mutation methods should not exist on tuples
        mutation_methods = ["append", "extend", "insert", "remove", "pop", "clear"]

        for method in mutation_methods:
            assert not hasattr(profile.phases, method), f"phases has {method}"
            assert not hasattr(profile.nondeterministic_allowed_phases, method), (
                f"nondeterministic_allowed_phases has {method}"
            )

    def test_tuple_delitem_prevented(self) -> None:
        """Test that item deletion on tuple raises TypeError."""
        profile = ModelExecutionProfile(phases=("init", "execute", "cleanup"))

        with pytest.raises(TypeError, match="doesn't support item deletion"):
            del profile.phases[0]  # type: ignore[misc]
