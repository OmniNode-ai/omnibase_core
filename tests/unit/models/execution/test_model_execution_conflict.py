# SPDX-FileCopyrightText: 2025 OmniNode Team
# SPDX-License-Identifier: Apache-2.0
"""
Unit tests for ModelExecutionConflict.

Tests execution conflict model including:
- Conflict type validation (including must_run_conflict)
- Severity levels
- Helper methods
- Immutability

See Also:
    - OMN-1106: Beta Execution Order Resolution Pure Function
    - OMN-1227: ProtocolConstraintValidator for SPI
    - OMN-1292: Core Models for ProtocolConstraintValidator
"""

import pytest
from pydantic import ValidationError

from omnibase_core.models.execution.model_execution_conflict import (
    ModelExecutionConflict,
)


@pytest.mark.unit
class TestModelExecutionConflictCreation:
    """Tests for ModelExecutionConflict creation."""

    def test_minimal_creation(self) -> None:
        """Test creation with minimal required fields."""
        conflict = ModelExecutionConflict(
            conflict_type="must_run_conflict",
            severity="error",
            message="Test conflict",
        )
        assert conflict.conflict_type == "must_run_conflict"
        assert conflict.severity == "error"
        assert conflict.message == "Test conflict"

    def test_full_creation(self) -> None:
        """Test creation with all fields."""
        conflict = ModelExecutionConflict(
            conflict_type="must_run_conflict",
            severity="error",
            message="Conflicting must_run constraints",
            handler_ids=("handler.a", "handler.b"),
            constraint_refs=("must_run:handler.a", "must_run:handler.b"),
            phase="execute",
            suggested_resolution="Remove one must_run constraint",
        )
        assert conflict.handler_ids == ("handler.a", "handler.b")
        assert conflict.constraint_refs == ("must_run:handler.a", "must_run:handler.b")
        assert conflict.phase == "execute"
        assert conflict.suggested_resolution == "Remove one must_run constraint"


@pytest.mark.unit
class TestMustRunConflictType:
    """Tests specific to must_run_conflict type (OMN-1292)."""

    def test_must_run_conflict_type_valid(self) -> None:
        """Test that must_run_conflict is a valid conflict type."""
        conflict = ModelExecutionConflict(
            conflict_type="must_run_conflict",
            severity="error",
            message="Handlers A and B both have must_run but conflict",
        )
        assert conflict.conflict_type == "must_run_conflict"

    def test_must_run_conflict_is_blocking(self) -> None:
        """Test that must_run_conflict with error severity is blocking."""
        conflict = ModelExecutionConflict(
            conflict_type="must_run_conflict",
            severity="error",
            message="Test",
        )
        assert conflict.is_blocking() is True

    def test_must_run_conflict_as_warning(self) -> None:
        """Test that must_run_conflict can be a warning."""
        conflict = ModelExecutionConflict(
            conflict_type="must_run_conflict",
            severity="warning",
            message="Potential must_run conflict detected",
        )
        assert conflict.is_blocking() is False

    def test_must_run_conflict_not_cycle(self) -> None:
        """Test that must_run_conflict is not a cycle type."""
        conflict = ModelExecutionConflict(
            conflict_type="must_run_conflict",
            severity="error",
            message="Test",
        )
        assert conflict.is_cycle() is False

    def test_must_run_conflict_involves_handler(self) -> None:
        """Test involves_handler method with must_run_conflict."""
        conflict = ModelExecutionConflict(
            conflict_type="must_run_conflict",
            severity="error",
            message="Test",
            handler_ids=("handler.a", "handler.b"),
        )
        assert conflict.involves_handler("handler.a") is True
        assert conflict.involves_handler("handler.b") is True
        assert conflict.involves_handler("handler.c") is False


@pytest.mark.unit
class TestAllConflictTypes:
    """Tests for all conflict types including must_run_conflict."""

    @pytest.mark.parametrize(
        "conflict_type",
        [
            "cycle",
            "unsatisfiable",
            "phase_conflict",
            "duplicate_handler",
            "missing_dependency",
            "constraint_violation",
            "must_run_conflict",
        ],
    )
    def test_all_conflict_types_valid(self, conflict_type: str) -> None:
        """Test all valid conflict types."""
        # cycle type requires cycle_path
        if conflict_type == "cycle":
            conflict = ModelExecutionConflict(
                conflict_type=conflict_type,  # type: ignore[arg-type]
                severity="error",
                message=f"Test {conflict_type}",
                cycle_path=("a", "b", "a"),
            )
        else:
            conflict = ModelExecutionConflict(
                conflict_type=conflict_type,  # type: ignore[arg-type]
                severity="error",
                message=f"Test {conflict_type}",
            )
        assert conflict.conflict_type == conflict_type

    def test_invalid_conflict_type_rejected(self) -> None:
        """Test that invalid conflict type is rejected."""
        with pytest.raises(ValidationError, match="Input should be"):
            ModelExecutionConflict(
                conflict_type="invalid_type",  # type: ignore[arg-type]
                severity="error",
                message="Test",
            )


@pytest.mark.unit
class TestCycleConflictRequirements:
    """Tests for cycle conflict specific requirements."""

    def test_cycle_requires_cycle_path(self) -> None:
        """Test that cycle conflict requires cycle_path."""
        with pytest.raises(
            ValidationError, match="cycle_path must be provided when conflict_type"
        ):
            ModelExecutionConflict(
                conflict_type="cycle",
                severity="error",
                message="Circular dependency",
            )

    def test_cycle_with_path_valid(self) -> None:
        """Test that cycle conflict with path is valid."""
        conflict = ModelExecutionConflict(
            conflict_type="cycle",
            severity="error",
            message="Circular dependency: A -> B -> A",
            cycle_path=("handler.a", "handler.b", "handler.a"),
        )
        assert conflict.is_cycle() is True
        assert conflict.get_cycle_length() == 2


@pytest.mark.unit
class TestHelperMethods:
    """Tests for helper methods."""

    def test_is_blocking_error(self) -> None:
        """Test is_blocking returns True for error severity."""
        conflict = ModelExecutionConflict(
            conflict_type="must_run_conflict",
            severity="error",
            message="Test",
        )
        assert conflict.is_blocking() is True

    def test_is_blocking_warning(self) -> None:
        """Test is_blocking returns False for warning severity."""
        conflict = ModelExecutionConflict(
            conflict_type="must_run_conflict",
            severity="warning",
            message="Test",
        )
        assert conflict.is_blocking() is False

    def test_str_representation(self) -> None:
        """Test string representation."""
        conflict = ModelExecutionConflict(
            conflict_type="must_run_conflict",
            severity="error",
            message="Conflicting must_run",
        )
        assert "must_run_conflict" in str(conflict)
        assert "error" in str(conflict)
        assert "Conflicting must_run" in str(conflict)

    def test_repr_representation(self) -> None:
        """Test repr representation."""
        conflict = ModelExecutionConflict(
            conflict_type="must_run_conflict",
            severity="error",
            message="Test",
            handler_ids=("a", "b"),
        )
        repr_str = repr(conflict)
        assert "ModelExecutionConflict" in repr_str
        assert "must_run_conflict" in repr_str


@pytest.mark.unit
class TestImmutability:
    """Tests for model immutability."""

    def test_frozen_model(self) -> None:
        """Test that model is frozen and cannot be modified."""
        conflict = ModelExecutionConflict(
            conflict_type="must_run_conflict",
            severity="error",
            message="Test",
        )
        with pytest.raises(ValidationError):
            conflict.message = "Modified"  # type: ignore[misc]

    def test_handler_ids_frozen(self) -> None:
        """Test that handler_ids cannot be modified."""
        conflict = ModelExecutionConflict(
            conflict_type="must_run_conflict",
            severity="error",
            message="Test",
            handler_ids=("handler.a",),
        )
        with pytest.raises(ValidationError):
            conflict.handler_ids = ("handler.b",)  # type: ignore[misc]


@pytest.mark.unit
class TestModelFromAttributes:
    """Tests for from_attributes compatibility."""

    def test_from_dict(self) -> None:
        """Test creation from dictionary.

        Note: Pydantic automatically converts lists to tuples for tuple fields.
        """
        data = {
            "conflict_type": "must_run_conflict",
            "severity": "error",
            "message": "Test conflict",
            "handler_ids": [
                "handler.a",
                "handler.b",
            ],  # List input is converted to tuple
        }
        conflict = ModelExecutionConflict.model_validate(data)
        assert conflict.conflict_type == "must_run_conflict"
        # Pydantic converts list to tuple
        assert conflict.handler_ids == ("handler.a", "handler.b")
        assert isinstance(conflict.handler_ids, tuple)

    def test_extra_fields_forbidden(self) -> None:
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError, match="extra"):
            ModelExecutionConflict.model_validate(
                {
                    "conflict_type": "must_run_conflict",
                    "severity": "error",
                    "message": "Test",
                    "unknown_field": "value",
                }
            )

    def test_from_object_with_attributes(self) -> None:
        """Test creation from object with matching attributes (from_attributes=True).

        Note: Pydantic automatically converts lists to tuples for tuple fields.
        """

        class ConflictLike:
            """Mock object with conflict-like attributes."""

            def __init__(self) -> None:
                self.conflict_type = "must_run_conflict"
                self.severity = "error"
                self.message = "Conflict from object"
                self.handler_ids = [
                    "handler.x",
                    "handler.y",
                ]  # List is converted to tuple
                self.constraint_refs: list[
                    str
                ] = []  # Empty list is converted to empty tuple
                self.cycle_path = None
                self.phase = "execute"
                self.suggested_resolution = "Fix the conflict"

        source_obj = ConflictLike()
        conflict = ModelExecutionConflict.model_validate(source_obj)

        assert conflict.conflict_type == "must_run_conflict"
        assert conflict.severity == "error"
        assert conflict.message == "Conflict from object"
        # Pydantic converts list to tuple
        assert conflict.handler_ids == ("handler.x", "handler.y")
        assert isinstance(conflict.handler_ids, tuple)
        assert conflict.phase == "execute"
        assert conflict.suggested_resolution == "Fix the conflict"

    def test_from_object_partial_attributes(self) -> None:
        """Test creation from object with only required attributes."""

        class MinimalConflict:
            """Object with minimal required attributes."""

            def __init__(self) -> None:
                self.conflict_type = "duplicate_handler"
                self.severity = "warning"
                self.message = "Duplicate detected"

        source_obj = MinimalConflict()
        conflict = ModelExecutionConflict.model_validate(source_obj)

        assert conflict.conflict_type == "duplicate_handler"
        assert conflict.severity == "warning"
        assert conflict.message == "Duplicate detected"
        # Defaults applied as empty tuples
        assert conflict.handler_ids == ()
        assert conflict.constraint_refs == ()
        assert isinstance(conflict.handler_ids, tuple)
        assert isinstance(conflict.constraint_refs, tuple)


@pytest.mark.unit
class TestMultiErrorAggregation:
    """Tests for multi-error aggregation behavior (OMN-1292)."""

    def test_multiple_validation_errors_aggregated(self) -> None:
        """Test that multiple validation errors are reported together."""
        with pytest.raises(ValidationError) as exc_info:
            ModelExecutionConflict.model_validate(
                {
                    "conflict_type": "invalid_type",  # Invalid
                    "severity": "critical",  # Invalid (not error/warning)
                    "message": "",  # Invalid (too short, min_length=1)
                }
            )

        # Verify multiple errors are present in the exception
        errors = exc_info.value.errors()
        assert len(errors) >= 2, f"Expected multiple errors, got {len(errors)}"

        # Check that different fields have errors
        error_locs = {str(e["loc"]) for e in errors}
        assert len(error_locs) >= 2, "Expected errors from multiple fields"

    def test_cycle_without_path_and_invalid_severity(self) -> None:
        """Test multiple errors: missing cycle_path AND invalid severity."""
        with pytest.raises(ValidationError) as exc_info:
            ModelExecutionConflict.model_validate(
                {
                    "conflict_type": "cycle",
                    "severity": "unknown",  # Invalid
                    "message": "Test cycle",
                    # cycle_path missing - will fail model_validator
                }
            )

        errors = exc_info.value.errors()
        # At minimum, severity is invalid
        assert len(errors) >= 1


@pytest.mark.unit
class TestTupleImmutability:
    """Tests for tuple field true immutability.

    With tuple[str, ...] fields, both field REASSIGNMENT and internal mutation
    are prevented, providing true immutability.

    See Also:
        - OMN-1292: Core Models for ProtocolConstraintValidator
    """

    def test_field_reassignment_prevented(self) -> None:
        """Test that direct field reassignment raises ValidationError."""
        conflict = ModelExecutionConflict(
            conflict_type="must_run_conflict",
            severity="error",
            message="Test",
            handler_ids=("handler.a",),
        )

        with pytest.raises(ValidationError):
            conflict.handler_ids = ("handler.new",)  # type: ignore[misc]

    def test_tuple_is_truly_immutable(self) -> None:
        """Test that tuple fields cannot be mutated internally.

        Unlike lists, tuples do not have append, extend, or other mutation
        methods, making them truly immutable.
        """
        conflict = ModelExecutionConflict(
            conflict_type="must_run_conflict",
            severity="error",
            message="Test",
            handler_ids=("handler.a",),
        )

        # Tuples don't have append method - this would raise AttributeError
        assert not hasattr(conflict.handler_ids, "append")
        assert not hasattr(conflict.handler_ids, "extend")
        assert not hasattr(conflict.handler_ids, "clear")
        assert not hasattr(conflict.handler_ids, "pop")

        # Verify type is tuple
        assert isinstance(conflict.handler_ids, tuple)

    def test_cycle_path_tuple_immutability(self) -> None:
        """Test that cycle_path tuple is truly immutable."""
        conflict = ModelExecutionConflict(
            conflict_type="cycle",
            severity="error",
            message="Cycle detected",
            cycle_path=("a", "b", "a"),
        )

        # Field reassignment is blocked
        with pytest.raises(ValidationError):
            conflict.cycle_path = ("x", "y", "x")  # type: ignore[misc]

        # Tuple has no mutation methods
        assert conflict.cycle_path is not None
        assert not hasattr(conflict.cycle_path, "append")
        assert isinstance(conflict.cycle_path, tuple)

    def test_constraint_refs_tuple_immutability(self) -> None:
        """Test that constraint_refs tuple is truly immutable."""
        conflict = ModelExecutionConflict(
            conflict_type="unsatisfiable",
            severity="warning",
            message="Constraint cannot be satisfied",
            constraint_refs=("capability:auth", "capability:logging"),
        )

        # Field reassignment is blocked
        with pytest.raises(ValidationError):
            conflict.constraint_refs = ("new_ref",)  # type: ignore[misc]

        # Tuple has no mutation methods
        assert not hasattr(conflict.constraint_refs, "append")
        assert isinstance(conflict.constraint_refs, tuple)
        assert len(conflict.constraint_refs) == 2

    def test_handler_ids_tuple_prevents_index_mutation(self) -> None:
        """Test that handler_ids tuple cannot be mutated via index assignment.

        This verifies true immutability - tuples prevent in-place mutation
        that would bypass Pydantic's frozen=True protection.

        See Also:
            - OMN-1292: PR review feedback on immutability protection
        """
        conflict = ModelExecutionConflict(
            conflict_type="must_run_conflict",
            severity="error",
            message="Test",
            handler_ids=("handler.a", "handler.b"),
        )

        # Attempting index assignment on tuple raises TypeError
        with pytest.raises(TypeError, match="does not support item assignment"):
            conflict.handler_ids[0] = "handler.modified"  # type: ignore[index]

    def test_constraint_refs_tuple_prevents_index_mutation(self) -> None:
        """Test that constraint_refs tuple cannot be mutated via index assignment."""
        conflict = ModelExecutionConflict(
            conflict_type="unsatisfiable",
            severity="warning",
            message="Test",
            constraint_refs=("capability:auth", "capability:logging"),
        )

        # Attempting index assignment on tuple raises TypeError
        with pytest.raises(TypeError, match="does not support item assignment"):
            conflict.constraint_refs[0] = "capability:new"  # type: ignore[index]

    def test_cycle_path_tuple_prevents_index_mutation(self) -> None:
        """Test that cycle_path tuple cannot be mutated via index assignment."""
        conflict = ModelExecutionConflict(
            conflict_type="cycle",
            severity="error",
            message="Cycle detected",
            cycle_path=("a", "b", "c", "a"),
        )

        # Attempting index assignment on tuple raises TypeError
        with pytest.raises(TypeError, match="does not support item assignment"):
            conflict.cycle_path[1] = "modified"  # type: ignore[index]


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

        class ConflictLike:
            """Object with tuple attributes matching conflict fields."""

            conflict_type = "duplicate_handler"
            severity = "warning"
            message = "Handler already exists"
            handler_ids = ("handler.a",)
            constraint_refs = ()
            cycle_path = None
            phase = None
            suggested_resolution = None

        # Explicit from_attributes=True parameter
        conflict = ModelExecutionConflict.model_validate(
            ConflictLike(), from_attributes=True
        )

        assert conflict.conflict_type == "duplicate_handler"
        assert conflict.severity == "warning"
        assert conflict.handler_ids == ("handler.a",)
        assert isinstance(conflict.handler_ids, tuple)

    def test_from_attributes_explicit_with_list_attributes(self) -> None:
        """Test model creation from object with list attributes using explicit parameter.

        Lists should be coerced to tuples even when reading from object attributes.
        """

        class ConflictLikeWithLists:
            """Object with list attributes that should be coerced to tuples."""

            conflict_type = "phase_conflict"
            severity = "error"
            message = "Phase conflict detected"
            handler_ids = ["handler.x", "handler.y"]  # List, not tuple
            constraint_refs = ["phase:execute"]  # List, not tuple
            cycle_path = None
            phase = "execute"
            suggested_resolution = None

        conflict = ModelExecutionConflict.model_validate(
            ConflictLikeWithLists(), from_attributes=True
        )

        # Lists coerced to tuples
        assert isinstance(conflict.handler_ids, tuple)
        assert conflict.handler_ids == ("handler.x", "handler.y")
        assert isinstance(conflict.constraint_refs, tuple)
        assert conflict.constraint_refs == ("phase:execute",)

    def test_from_attributes_with_namedtuple(self) -> None:
        """Test model creation from namedtuple using from_attributes=True."""
        from typing import NamedTuple

        class ConflictTuple(NamedTuple):
            conflict_type: str
            severity: str
            message: str
            handler_ids: tuple[str, ...]
            constraint_refs: tuple[str, ...]
            cycle_path: tuple[str, ...] | None
            phase: str | None
            suggested_resolution: str | None

        source = ConflictTuple(
            conflict_type="missing_dependency",
            severity="error",
            message="Required handler not found",
            handler_ids=("handler.dependent",),
            constraint_refs=("requires:handler.missing",),
            cycle_path=None,
            phase="preflight",
            suggested_resolution="Add the missing handler",
        )

        conflict = ModelExecutionConflict.model_validate(source, from_attributes=True)

        assert conflict.conflict_type == "missing_dependency"
        assert conflict.handler_ids == ("handler.dependent",)
        assert conflict.phase == "preflight"
        assert conflict.suggested_resolution == "Add the missing handler"

    def test_from_attributes_with_dataclass(self) -> None:
        """Test model creation from dataclass using from_attributes=True."""
        from dataclasses import dataclass

        @dataclass
        class ConflictData:
            conflict_type: str
            severity: str
            message: str
            handler_ids: list[str]  # Dataclass with list
            constraint_refs: list[str]
            cycle_path: tuple[str, ...] | None = None
            phase: str | None = None
            suggested_resolution: str | None = None

        source = ConflictData(
            conflict_type="constraint_violation",
            severity="error",
            message="Constraint violated",
            handler_ids=["handler.a", "handler.b"],  # Lists should be converted
            constraint_refs=["constraint:ordering"],
            phase="execute",
        )

        conflict = ModelExecutionConflict.model_validate(source, from_attributes=True)

        # Lists should be coerced to tuples
        assert isinstance(conflict.handler_ids, tuple)
        assert conflict.handler_ids == ("handler.a", "handler.b")
        assert isinstance(conflict.constraint_refs, tuple)
        assert conflict.constraint_refs == ("constraint:ordering",)

    def test_from_attributes_implicit_via_config(self) -> None:
        """Test that from_attributes works implicitly via ConfigDict setting.

        The model has from_attributes=True in ConfigDict, so it should work
        without explicit parameter.
        """

        class ConflictLike:
            conflict_type = "must_run_conflict"
            severity = "warning"
            message = "Potential conflict"
            handler_ids = ("handler.x",)
            constraint_refs = ()
            cycle_path = None
            phase = None
            suggested_resolution = None

        # No explicit from_attributes parameter - relies on ConfigDict
        conflict = ModelExecutionConflict.model_validate(ConflictLike())

        assert conflict.conflict_type == "must_run_conflict"
        assert conflict.handler_ids == ("handler.x",)
