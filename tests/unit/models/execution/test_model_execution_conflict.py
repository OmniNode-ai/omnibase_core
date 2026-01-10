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
            handler_ids=["handler.a", "handler.b"],
            constraint_refs=["must_run:handler.a", "must_run:handler.b"],
            phase="execute",
            suggested_resolution="Remove one must_run constraint",
        )
        assert conflict.handler_ids == ["handler.a", "handler.b"]
        assert conflict.constraint_refs == ["must_run:handler.a", "must_run:handler.b"]
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
            handler_ids=["handler.a", "handler.b"],
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
                conflict_type=conflict_type,
                severity="error",
                message=f"Test {conflict_type}",
                cycle_path=["a", "b", "a"],
            )
        else:
            conflict = ModelExecutionConflict(
                conflict_type=conflict_type,
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
            cycle_path=["handler.a", "handler.b", "handler.a"],
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
            handler_ids=["a", "b"],
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
            handler_ids=["handler.a"],
        )
        with pytest.raises(ValidationError):
            conflict.handler_ids = ["handler.b"]  # type: ignore[misc]


@pytest.mark.unit
class TestModelFromAttributes:
    """Tests for from_attributes compatibility."""

    def test_from_dict(self) -> None:
        """Test creation from dictionary."""
        data = {
            "conflict_type": "must_run_conflict",
            "severity": "error",
            "message": "Test conflict",
            "handler_ids": ["handler.a", "handler.b"],
        }
        conflict = ModelExecutionConflict.model_validate(data)
        assert conflict.conflict_type == "must_run_conflict"
        assert conflict.handler_ids == ["handler.a", "handler.b"]

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
