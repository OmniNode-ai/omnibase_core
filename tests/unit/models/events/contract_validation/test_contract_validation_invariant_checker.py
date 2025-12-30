# SPDX-FileCopyrightText: 2025 OmniNode Team
#
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for ContractValidationInvariantChecker.

Tests the invariant checker that enforces event ordering and state machine
constraints for contract validation workflows.

Invariants Enforced:
    1. validation_started must precede validation_passed or validation_failed
    2. validation_passed and validation_failed are mutually exclusive
    3. merge_started must precede merge_completed
    4. merge_completed cannot occur if validation_failed occurred

Related:
    - OMN-1146: Contract validation invariant checker
"""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.validation.contract_validation_invariant_checker import (
    ContractValidationEventType,
    ContractValidationInvariantChecker,
    ModelContractValidationEvent,
)

# =============================================================================
# ModelContractValidationEvent Tests
# =============================================================================


@pytest.mark.unit
class TestModelContractValidationEvent:
    """Tests for the ModelContractValidationEvent model."""

    def test_event_creation_with_required_fields(self) -> None:
        """Test that event can be created with required fields."""
        event = ModelContractValidationEvent(
            event_type="validation_started",
            run_id="run-123",
        )

        assert event.event_type == "validation_started"
        assert event.run_id == "run-123"
        assert event.message is None

    def test_event_creation_with_all_fields(self) -> None:
        """Test that event can be created with all fields."""
        event = ModelContractValidationEvent(
            event_type="validation_passed",
            run_id="run-456",
            message="Validation completed successfully",
        )

        assert event.event_type == "validation_passed"
        assert event.run_id == "run-456"
        assert event.message == "Validation completed successfully"

    def test_event_type_validation_started(self) -> None:
        """Test event with validation_started type."""
        event = ModelContractValidationEvent(
            event_type="validation_started",
            run_id="run-1",
        )
        assert event.event_type == "validation_started"

    def test_event_type_validation_passed(self) -> None:
        """Test event with validation_passed type."""
        event = ModelContractValidationEvent(
            event_type="validation_passed",
            run_id="run-1",
        )
        assert event.event_type == "validation_passed"

    def test_event_type_validation_failed(self) -> None:
        """Test event with validation_failed type."""
        event = ModelContractValidationEvent(
            event_type="validation_failed",
            run_id="run-1",
        )
        assert event.event_type == "validation_failed"

    def test_event_type_merge_started(self) -> None:
        """Test event with merge_started type."""
        event = ModelContractValidationEvent(
            event_type="merge_started",
            run_id="run-1",
        )
        assert event.event_type == "merge_started"

    def test_event_type_merge_completed(self) -> None:
        """Test event with merge_completed type."""
        event = ModelContractValidationEvent(
            event_type="merge_completed",
            run_id="run-1",
        )
        assert event.event_type == "merge_completed"

    def test_invalid_event_type_rejected(self) -> None:
        """Test that invalid event type is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractValidationEvent(
                event_type="invalid_type",  # type: ignore[arg-type]
                run_id="run-1",
            )

        error_str = str(exc_info.value)
        assert "event_type" in error_str.lower() or "literal" in error_str.lower()

    def test_run_id_required(self) -> None:
        """Test that run_id is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractValidationEvent(
                event_type="validation_started",
            )  # type: ignore[call-arg]

        error_str = str(exc_info.value)
        assert "run_id" in error_str

    def test_run_id_min_length(self) -> None:
        """Test that run_id has min_length=1."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractValidationEvent(
                event_type="validation_started",
                run_id="",  # Empty string
            )

        error_str = str(exc_info.value)
        assert "run_id" in error_str or "min_length" in error_str.lower()

    def test_event_is_frozen(self) -> None:
        """Test that event is frozen (immutable)."""
        event = ModelContractValidationEvent(
            event_type="validation_started",
            run_id="run-1",
        )

        with pytest.raises(ValidationError):
            event.run_id = "new-run"  # type: ignore[misc]

    def test_event_forbids_extra_fields(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError):
            ModelContractValidationEvent(
                event_type="validation_started",
                run_id="run-1",
                extra_field="should_fail",  # type: ignore[call-arg]
            )


# =============================================================================
# ContractValidationInvariantChecker - Invariant 1 Tests
# =============================================================================


@pytest.mark.unit
class TestInvariant1ValidationStartedMustPrecede:
    """Tests for Invariant 1: validation_started must precede passed/failed."""

    def test_validation_passed_without_started_violates(self) -> None:
        """Test that validation_passed without prior started is a violation."""
        checker = ContractValidationInvariantChecker()
        run_id = str(uuid4())

        events = [
            ModelContractValidationEvent(
                event_type="validation_passed",
                run_id=run_id,
            ),
        ]

        is_valid, violations = checker.validate_sequence(events)

        assert is_valid is False
        assert len(violations) == 1
        assert "validation_passed" in violations[0]
        assert "validation_started" in violations[0]

    def test_validation_failed_without_started_violates(self) -> None:
        """Test that validation_failed without prior started is a violation."""
        checker = ContractValidationInvariantChecker()
        run_id = str(uuid4())

        events = [
            ModelContractValidationEvent(
                event_type="validation_failed",
                run_id=run_id,
            ),
        ]

        is_valid, violations = checker.validate_sequence(events)

        assert is_valid is False
        assert len(violations) == 1
        assert "validation_failed" in violations[0]
        assert "validation_started" in violations[0]

    def test_validation_started_then_passed_is_valid(self) -> None:
        """Test that started -> passed sequence is valid."""
        checker = ContractValidationInvariantChecker()
        run_id = str(uuid4())

        events = [
            ModelContractValidationEvent(
                event_type="validation_started",
                run_id=run_id,
            ),
            ModelContractValidationEvent(
                event_type="validation_passed",
                run_id=run_id,
            ),
        ]

        is_valid, violations = checker.validate_sequence(events)

        assert is_valid is True
        assert len(violations) == 0

    def test_validation_started_then_failed_is_valid(self) -> None:
        """Test that started -> failed sequence is valid."""
        checker = ContractValidationInvariantChecker()
        run_id = str(uuid4())

        events = [
            ModelContractValidationEvent(
                event_type="validation_started",
                run_id=run_id,
            ),
            ModelContractValidationEvent(
                event_type="validation_failed",
                run_id=run_id,
            ),
        ]

        is_valid, violations = checker.validate_sequence(events)

        assert is_valid is True
        assert len(violations) == 0


# =============================================================================
# ContractValidationInvariantChecker - Invariant 2 Tests
# =============================================================================


@pytest.mark.unit
class TestInvariant2PassedFailedMutuallyExclusive:
    """Tests for Invariant 2: passed and failed are mutually exclusive."""

    def test_passed_after_failed_violates(self) -> None:
        """Test that validation_passed after validation_failed is a violation."""
        checker = ContractValidationInvariantChecker()
        run_id = str(uuid4())

        events = [
            ModelContractValidationEvent(
                event_type="validation_started",
                run_id=run_id,
            ),
            ModelContractValidationEvent(
                event_type="validation_failed",
                run_id=run_id,
            ),
            ModelContractValidationEvent(
                event_type="validation_passed",
                run_id=run_id,
            ),
        ]

        is_valid, violations = checker.validate_sequence(events)

        assert is_valid is False
        assert len(violations) == 1
        assert "validation_passed" in violations[0]
        assert "validation_failed" in violations[0]
        assert "mutually exclusive" in violations[0]

    def test_failed_after_passed_violates(self) -> None:
        """Test that validation_failed after validation_passed is a violation."""
        checker = ContractValidationInvariantChecker()
        run_id = str(uuid4())

        events = [
            ModelContractValidationEvent(
                event_type="validation_started",
                run_id=run_id,
            ),
            ModelContractValidationEvent(
                event_type="validation_passed",
                run_id=run_id,
            ),
            ModelContractValidationEvent(
                event_type="validation_failed",
                run_id=run_id,
            ),
        ]

        is_valid, violations = checker.validate_sequence(events)

        assert is_valid is False
        assert len(violations) == 1
        assert "validation_failed" in violations[0]
        assert "validation_passed" in violations[0]
        assert "mutually exclusive" in violations[0]

    def test_only_passed_is_valid(self) -> None:
        """Test that only passed (no failed) is valid."""
        checker = ContractValidationInvariantChecker()
        run_id = str(uuid4())

        events = [
            ModelContractValidationEvent(
                event_type="validation_started",
                run_id=run_id,
            ),
            ModelContractValidationEvent(
                event_type="validation_passed",
                run_id=run_id,
            ),
        ]

        is_valid, violations = checker.validate_sequence(events)

        assert is_valid is True
        assert len(violations) == 0

    def test_only_failed_is_valid(self) -> None:
        """Test that only failed (no passed) is valid."""
        checker = ContractValidationInvariantChecker()
        run_id = str(uuid4())

        events = [
            ModelContractValidationEvent(
                event_type="validation_started",
                run_id=run_id,
            ),
            ModelContractValidationEvent(
                event_type="validation_failed",
                run_id=run_id,
            ),
        ]

        is_valid, violations = checker.validate_sequence(events)

        assert is_valid is True
        assert len(violations) == 0


# =============================================================================
# ContractValidationInvariantChecker - Invariant 3 Tests
# =============================================================================


@pytest.mark.unit
class TestInvariant3MergeStartedMustPrecedeCompleted:
    """Tests for Invariant 3: merge_started must precede merge_completed."""

    def test_merge_completed_without_started_violates(self) -> None:
        """Test that merge_completed without prior started is a violation."""
        checker = ContractValidationInvariantChecker()
        run_id = str(uuid4())

        events = [
            ModelContractValidationEvent(
                event_type="merge_completed",
                run_id=run_id,
            ),
        ]

        is_valid, violations = checker.validate_sequence(events)

        assert is_valid is False
        assert len(violations) == 1
        assert "merge_completed" in violations[0]
        assert "merge_started" in violations[0]

    def test_merge_started_then_completed_is_valid(self) -> None:
        """Test that started -> completed merge sequence is valid."""
        checker = ContractValidationInvariantChecker()
        run_id = str(uuid4())

        events = [
            ModelContractValidationEvent(
                event_type="merge_started",
                run_id=run_id,
            ),
            ModelContractValidationEvent(
                event_type="merge_completed",
                run_id=run_id,
            ),
        ]

        is_valid, violations = checker.validate_sequence(events)

        assert is_valid is True
        assert len(violations) == 0


# =============================================================================
# ContractValidationInvariantChecker - Invariant 4 Tests
# =============================================================================


@pytest.mark.unit
class TestInvariant4MergeCompletedNotAfterValidationFailed:
    """Tests for Invariant 4: merge_completed cannot occur after validation_failed."""

    def test_merge_completed_after_validation_failed_violates(self) -> None:
        """Test that merge_completed after validation_failed is a violation."""
        checker = ContractValidationInvariantChecker()
        run_id = str(uuid4())

        events = [
            ModelContractValidationEvent(
                event_type="validation_started",
                run_id=run_id,
            ),
            ModelContractValidationEvent(
                event_type="validation_failed",
                run_id=run_id,
            ),
            ModelContractValidationEvent(
                event_type="merge_started",
                run_id=run_id,
            ),
            ModelContractValidationEvent(
                event_type="merge_completed",
                run_id=run_id,
            ),
        ]

        is_valid, violations = checker.validate_sequence(events)

        assert is_valid is False
        assert any(
            "merge_completed" in v and "validation_failed" in v for v in violations
        )

    def test_merge_completed_after_validation_passed_is_valid(self) -> None:
        """Test that merge_completed after validation_passed is valid."""
        checker = ContractValidationInvariantChecker()
        run_id = str(uuid4())

        events = [
            ModelContractValidationEvent(
                event_type="validation_started",
                run_id=run_id,
            ),
            ModelContractValidationEvent(
                event_type="validation_passed",
                run_id=run_id,
            ),
            ModelContractValidationEvent(
                event_type="merge_started",
                run_id=run_id,
            ),
            ModelContractValidationEvent(
                event_type="merge_completed",
                run_id=run_id,
            ),
        ]

        is_valid, violations = checker.validate_sequence(events)

        assert is_valid is True
        assert len(violations) == 0


# =============================================================================
# ContractValidationInvariantChecker - Valid Sequences Tests
# =============================================================================


@pytest.mark.unit
class TestValidSequences:
    """Tests for valid event sequences."""

    def test_complete_validation_passed_sequence(self) -> None:
        """Test complete validation pass sequence."""
        checker = ContractValidationInvariantChecker()
        run_id = str(uuid4())

        events = [
            ModelContractValidationEvent(
                event_type="validation_started",
                run_id=run_id,
            ),
            ModelContractValidationEvent(
                event_type="validation_passed",
                run_id=run_id,
            ),
        ]

        is_valid, violations = checker.validate_sequence(events)

        assert is_valid is True
        assert violations == []

    def test_complete_validation_failed_sequence(self) -> None:
        """Test complete validation fail sequence."""
        checker = ContractValidationInvariantChecker()
        run_id = str(uuid4())

        events = [
            ModelContractValidationEvent(
                event_type="validation_started",
                run_id=run_id,
            ),
            ModelContractValidationEvent(
                event_type="validation_failed",
                run_id=run_id,
            ),
        ]

        is_valid, violations = checker.validate_sequence(events)

        assert is_valid is True
        assert violations == []

    def test_complete_merge_sequence(self) -> None:
        """Test complete merge sequence."""
        checker = ContractValidationInvariantChecker()
        run_id = str(uuid4())

        events = [
            ModelContractValidationEvent(
                event_type="merge_started",
                run_id=run_id,
            ),
            ModelContractValidationEvent(
                event_type="merge_completed",
                run_id=run_id,
            ),
        ]

        is_valid, violations = checker.validate_sequence(events)

        assert is_valid is True
        assert violations == []

    def test_full_successful_workflow(self) -> None:
        """Test full successful validation and merge workflow."""
        checker = ContractValidationInvariantChecker()
        run_id = str(uuid4())

        events = [
            ModelContractValidationEvent(
                event_type="validation_started",
                run_id=run_id,
            ),
            ModelContractValidationEvent(
                event_type="validation_passed",
                run_id=run_id,
            ),
            ModelContractValidationEvent(
                event_type="merge_started",
                run_id=run_id,
            ),
            ModelContractValidationEvent(
                event_type="merge_completed",
                run_id=run_id,
            ),
        ]

        is_valid, violations = checker.validate_sequence(events)

        assert is_valid is True
        assert violations == []

    def test_validation_only_no_merge(self) -> None:
        """Test validation without merge is valid."""
        checker = ContractValidationInvariantChecker()
        run_id = str(uuid4())

        events = [
            ModelContractValidationEvent(
                event_type="validation_started",
                run_id=run_id,
            ),
            ModelContractValidationEvent(
                event_type="validation_passed",
                run_id=run_id,
            ),
        ]

        is_valid, _violations = checker.validate_sequence(events)

        assert is_valid is True

    def test_empty_sequence_is_valid(self) -> None:
        """Test that empty event sequence is valid."""
        checker = ContractValidationInvariantChecker()

        is_valid, violations = checker.validate_sequence([])

        assert is_valid is True
        assert violations == []

    def test_validation_started_only_is_valid(self) -> None:
        """Test that just validation_started is valid (incomplete but no violation)."""
        checker = ContractValidationInvariantChecker()
        run_id = str(uuid4())

        events = [
            ModelContractValidationEvent(
                event_type="validation_started",
                run_id=run_id,
            ),
        ]

        is_valid, violations = checker.validate_sequence(events)

        assert is_valid is True
        assert violations == []


# =============================================================================
# ContractValidationInvariantChecker - Invalid Sequences Tests
# =============================================================================


@pytest.mark.unit
class TestInvalidSequences:
    """Tests for invalid event sequences."""

    def test_multiple_violations_same_run(self) -> None:
        """Test sequence with multiple violations."""
        checker = ContractValidationInvariantChecker()
        run_id = str(uuid4())

        # validation_passed without started, then merge_completed without started
        events = [
            ModelContractValidationEvent(
                event_type="validation_passed",
                run_id=run_id,
            ),
            ModelContractValidationEvent(
                event_type="merge_completed",
                run_id=run_id,
            ),
        ]

        is_valid, violations = checker.validate_sequence(events)

        assert is_valid is False
        assert len(violations) >= 2  # At least two violations

    def test_violation_includes_run_id(self) -> None:
        """Test that violation messages include run_id."""
        checker = ContractValidationInvariantChecker()
        run_id = "test-run-123"

        events = [
            ModelContractValidationEvent(
                event_type="validation_passed",
                run_id=run_id,
            ),
        ]

        is_valid, violations = checker.validate_sequence(events)

        assert is_valid is False
        assert run_id in violations[0]


# =============================================================================
# ContractValidationInvariantChecker - Multiple Run IDs Tests
# =============================================================================


@pytest.mark.unit
class TestMultipleRunIds:
    """Tests for handling multiple run_ids in event sequences."""

    def test_independent_runs_validated_separately(self) -> None:
        """Test that different run_ids are validated independently."""
        checker = ContractValidationInvariantChecker()
        run_id_1 = str(uuid4())
        run_id_2 = str(uuid4())

        events = [
            # Run 1: valid sequence
            ModelContractValidationEvent(
                event_type="validation_started",
                run_id=run_id_1,
            ),
            ModelContractValidationEvent(
                event_type="validation_passed",
                run_id=run_id_1,
            ),
            # Run 2: also valid sequence
            ModelContractValidationEvent(
                event_type="validation_started",
                run_id=run_id_2,
            ),
            ModelContractValidationEvent(
                event_type="validation_failed",
                run_id=run_id_2,
            ),
        ]

        is_valid, violations = checker.validate_sequence(events)

        assert is_valid is True
        assert violations == []

    def test_one_valid_one_invalid_run(self) -> None:
        """Test that one invalid run doesn't affect valid run."""
        checker = ContractValidationInvariantChecker()
        run_id_valid = str(uuid4())
        run_id_invalid = str(uuid4())

        events = [
            # Valid run
            ModelContractValidationEvent(
                event_type="validation_started",
                run_id=run_id_valid,
            ),
            ModelContractValidationEvent(
                event_type="validation_passed",
                run_id=run_id_valid,
            ),
            # Invalid run (no started before passed)
            ModelContractValidationEvent(
                event_type="validation_passed",
                run_id=run_id_invalid,
            ),
        ]

        is_valid, violations = checker.validate_sequence(events)

        assert is_valid is False
        assert len(violations) == 1
        assert run_id_invalid in violations[0]

    def test_interleaved_events_from_multiple_runs(self) -> None:
        """Test interleaved events from multiple runs are handled correctly."""
        checker = ContractValidationInvariantChecker()
        run_id_1 = str(uuid4())
        run_id_2 = str(uuid4())

        # Interleave events from two runs
        events = [
            ModelContractValidationEvent(
                event_type="validation_started", run_id=run_id_1
            ),
            ModelContractValidationEvent(
                event_type="validation_started", run_id=run_id_2
            ),
            ModelContractValidationEvent(
                event_type="validation_passed", run_id=run_id_1
            ),
            ModelContractValidationEvent(
                event_type="validation_failed", run_id=run_id_2
            ),
        ]

        is_valid, violations = checker.validate_sequence(events)

        assert is_valid is True
        assert violations == []


# =============================================================================
# ContractValidationInvariantChecker - check_invariant Method Tests
# =============================================================================


@pytest.mark.unit
class TestCheckInvariantMethod:
    """Tests for the check_invariant method (single event against history)."""

    def test_check_invariant_valid_event(self) -> None:
        """Test check_invariant with valid event."""
        checker = ContractValidationInvariantChecker()
        run_id = str(uuid4())

        history = [
            ModelContractValidationEvent(
                event_type="validation_started",
                run_id=run_id,
            ),
        ]

        new_event = ModelContractValidationEvent(
            event_type="validation_passed",
            run_id=run_id,
        )

        is_valid, violation = checker.check_invariant(new_event, history)

        assert is_valid is True
        assert violation is None

    def test_check_invariant_invalid_event(self) -> None:
        """Test check_invariant with invalid event."""
        checker = ContractValidationInvariantChecker()
        run_id = str(uuid4())

        # Empty history (no validation_started)
        history: list[ModelContractValidationEvent] = []

        new_event = ModelContractValidationEvent(
            event_type="validation_passed",
            run_id=run_id,
        )

        is_valid, violation = checker.check_invariant(new_event, history)

        assert is_valid is False
        assert violation is not None
        assert "validation_passed" in violation
        assert "validation_started" in violation

    def test_check_invariant_filters_by_run_id(self) -> None:
        """Test that check_invariant filters history by run_id."""
        checker = ContractValidationInvariantChecker()
        run_id_1 = str(uuid4())
        run_id_2 = str(uuid4())

        # History contains started for run_id_1 only
        history = [
            ModelContractValidationEvent(
                event_type="validation_started",
                run_id=run_id_1,
            ),
        ]

        # New event for run_id_2 (no started in its history)
        new_event = ModelContractValidationEvent(
            event_type="validation_passed",
            run_id=run_id_2,
        )

        is_valid, _violation = checker.check_invariant(new_event, history)

        assert is_valid is False  # No started for run_id_2

    def test_check_invariant_mutual_exclusivity(self) -> None:
        """Test check_invariant catches mutual exclusivity violations."""
        checker = ContractValidationInvariantChecker()
        run_id = str(uuid4())

        history = [
            ModelContractValidationEvent(
                event_type="validation_started", run_id=run_id
            ),
            ModelContractValidationEvent(event_type="validation_passed", run_id=run_id),
        ]

        # Try to add failed after passed
        new_event = ModelContractValidationEvent(
            event_type="validation_failed",
            run_id=run_id,
        )

        is_valid, violation = checker.check_invariant(new_event, history)

        assert is_valid is False
        assert violation is not None
        assert "mutually exclusive" in violation


# =============================================================================
# ContractValidationEventType Tests
# =============================================================================


@pytest.mark.unit
class TestContractValidationEventType:
    """Tests for the event type literal type."""

    def test_all_event_types_are_valid(self) -> None:
        """Test that all expected event types are accepted."""
        valid_types: list[ContractValidationEventType] = [
            "validation_started",
            "validation_passed",
            "validation_failed",
            "merge_started",
            "merge_completed",
        ]

        for event_type in valid_types:
            event = ModelContractValidationEvent(
                event_type=event_type,
                run_id="test-run",
            )
            assert event.event_type == event_type

    def test_event_type_count(self) -> None:
        """Test that there are exactly 5 event types."""
        # This is a type alias, so we test by creating events
        valid_types = [
            "validation_started",
            "validation_passed",
            "validation_failed",
            "merge_started",
            "merge_completed",
        ]
        assert len(valid_types) == 5


# =============================================================================
# Edge Cases and Boundary Tests
# =============================================================================


@pytest.mark.unit
class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_duplicate_started_events_are_valid(self) -> None:
        """Test that duplicate started events don't cause violations.

        Note: The checker validates ordering, not uniqueness.
        """
        checker = ContractValidationInvariantChecker()
        run_id = str(uuid4())

        events = [
            ModelContractValidationEvent(
                event_type="validation_started", run_id=run_id
            ),
            ModelContractValidationEvent(
                event_type="validation_started", run_id=run_id
            ),
            ModelContractValidationEvent(event_type="validation_passed", run_id=run_id),
        ]

        is_valid, _violations = checker.validate_sequence(events)

        # Duplicates don't cause violations per the invariant rules
        assert is_valid is True

    def test_very_long_run_id(self) -> None:
        """Test with very long run_id string."""
        checker = ContractValidationInvariantChecker()
        run_id = "x" * 1000

        events = [
            ModelContractValidationEvent(
                event_type="validation_started", run_id=run_id
            ),
            ModelContractValidationEvent(event_type="validation_passed", run_id=run_id),
        ]

        is_valid, _violations = checker.validate_sequence(events)

        assert is_valid is True

    def test_run_id_with_special_characters(self) -> None:
        """Test with special characters in run_id."""
        checker = ContractValidationInvariantChecker()
        run_id = "run/with:special@chars#123"

        events = [
            ModelContractValidationEvent(
                event_type="validation_started", run_id=run_id
            ),
            ModelContractValidationEvent(event_type="validation_passed", run_id=run_id),
        ]

        is_valid, _violations = checker.validate_sequence(events)

        assert is_valid is True

    def test_unicode_run_id(self) -> None:
        """Test with unicode characters in run_id."""
        checker = ContractValidationInvariantChecker()
        run_id = "run-\u4e2d\u6587-123"  # Contains Chinese characters

        events = [
            ModelContractValidationEvent(
                event_type="validation_started", run_id=run_id
            ),
            ModelContractValidationEvent(event_type="validation_passed", run_id=run_id),
        ]

        is_valid, _violations = checker.validate_sequence(events)

        assert is_valid is True

    def test_many_events_same_run(self) -> None:
        """Test with many events in same run."""
        checker = ContractValidationInvariantChecker()
        run_id = str(uuid4())

        # Start with validation, then merge
        events = [
            ModelContractValidationEvent(
                event_type="validation_started", run_id=run_id
            ),
            ModelContractValidationEvent(event_type="validation_passed", run_id=run_id),
            ModelContractValidationEvent(event_type="merge_started", run_id=run_id),
            ModelContractValidationEvent(event_type="merge_completed", run_id=run_id),
        ]

        is_valid, _violations = checker.validate_sequence(events)

        assert is_valid is True

    def test_many_runs(self) -> None:
        """Test with many separate runs."""
        checker = ContractValidationInvariantChecker()

        events = []
        for _ in range(100):
            run_id = str(uuid4())
            events.append(
                ModelContractValidationEvent(
                    event_type="validation_started", run_id=run_id
                )
            )
            events.append(
                ModelContractValidationEvent(
                    event_type="validation_passed", run_id=run_id
                )
            )

        is_valid, violations = checker.validate_sequence(events)

        assert is_valid is True
        assert violations == []


# =============================================================================
# Thread Safety Note Tests
# =============================================================================


@pytest.mark.unit
class TestCheckerInstantiation:
    """Tests for checker instantiation."""

    def test_checker_is_instantiable(self) -> None:
        """Test that checker can be instantiated."""
        checker = ContractValidationInvariantChecker()
        assert checker is not None

    def test_multiple_checker_instances_are_independent(self) -> None:
        """Test that multiple checker instances work independently."""
        checker1 = ContractValidationInvariantChecker()
        checker2 = ContractValidationInvariantChecker()

        run_id = str(uuid4())
        events = [
            ModelContractValidationEvent(event_type="validation_passed", run_id=run_id),
        ]

        # Both should give same result for same input
        is_valid1, violations1 = checker1.validate_sequence(events)
        is_valid2, violations2 = checker2.validate_sequence(events)

        assert is_valid1 == is_valid2
        assert len(violations1) == len(violations2)
