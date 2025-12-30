"""
Protocol definition for contract validation invariant checking.

This module provides the ProtocolContractValidationInvariantChecker protocol which
validates event ordering invariants and state machine constraints for contract
validation workflows.

Design Principles:
- Protocol-first: Use typing.Protocol for interface definitions
- Minimal interfaces: Only define what Core actually needs
- Runtime checkable: Use @runtime_checkable for duck typing support
- Complete type hints: Full mypy strict mode compliance

Invariants Enforced:
- validation_started must precede validation_passed or validation_failed (same run_id)
- validation_passed and validation_failed are mutually exclusive per run_id
- merge_started must precede merge_completed (same run_id)
- merge_completed cannot occur if validation_failed occurred (same run_id)

Related:
    - OMN-1146: Contract Validation Invariant Checker

.. versionadded:: 0.4.0
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from omnibase_core.validation.contract_validation_invariant_checker import (
        ModelContractValidationEvent,
    )

__all__ = ["ProtocolContractValidationInvariantChecker"]


@runtime_checkable
class ProtocolContractValidationInvariantChecker(Protocol):
    """
    Protocol for contract validation invariant checking.

    Validates event ordering invariants and state machine constraints
    for contract validation workflows. This ensures that validation
    events follow the correct lifecycle sequence.

    Lifecycle States:
        - validation_started: Beginning of validation run
        - validation_passed: Validation completed successfully
        - validation_failed: Validation completed with failures
        - merge_started: Beginning of merge operation
        - merge_completed: Merge operation completed

    Thread Safety:
        WARNING: Thread safety is implementation-specific. Callers should verify
        the thread safety guarantees of their chosen implementation.

    Example:
        .. code-block:: python

            from omnibase_core.protocols import ProtocolContractValidationInvariantChecker

            def validate_event_sequence(
                checker: ProtocolContractValidationInvariantChecker,
                events: list[ModelContractValidationEvent],
            ) -> bool:
                '''Validate a sequence of contract validation events.'''
                is_valid, violations = checker.validate_sequence(events)
                if not is_valid:
                    for violation in violations:
                        print(f"Invariant violation: {violation}")
                return is_valid

    .. versionadded:: 0.4.0
    """

    def validate_sequence(
        self, events: list[ModelContractValidationEvent]
    ) -> tuple[bool, list[str]]:
        """
        Validate event ordering invariants for a sequence of events.

        Checks all invariants across the event sequence:
        - validation_started must precede validation_passed/validation_failed
        - validation_passed and validation_failed are mutually exclusive
        - merge_started must precede merge_completed
        - merge_completed cannot occur after validation_failed

        Args:
            events: List of contract validation events to validate.
                Events should be ordered chronologically.

        Returns:
            A tuple of (is_valid, violations) where:
            - is_valid: True if all invariants are satisfied, False otherwise
            - violations: List of violation error strings describing each failed
              invariant. Empty if is_valid is True.

        Example:
            .. code-block:: python

                events = [
                    ModelContractValidationEvent(
                        event_type="validation_started",
                        run_id="run-123",
                    ),
                    ModelContractValidationEvent(
                        event_type="validation_passed",
                        run_id="run-123",
                    ),
                ]
                is_valid, violations = checker.validate_sequence(events)
                assert is_valid is True
                assert violations == []
        """
        ...

    def check_invariant(
        self,
        event: ModelContractValidationEvent,
        history: list[ModelContractValidationEvent],
    ) -> tuple[bool, str | None]:
        """
        Check a single event against historical event sequence.

        Validates that adding this event to the history would not violate
        any invariants. This is useful for incremental validation as events
        are received.

        Args:
            event: The new event to validate.
            history: List of previously received events for this run_id.
                Should be ordered chronologically.

        Returns:
            A tuple of (is_valid, violation) where:
            - is_valid: True if the event can be added without violating invariants
            - violation: Error string describing the violated invariant if
              is_valid is False, None otherwise.

        Example:
            .. code-block:: python

                history = [
                    ModelContractValidationEvent(
                        event_type="validation_failed",
                        run_id="run-123",
                    ),
                ]
                new_event = ModelContractValidationEvent(
                    event_type="merge_completed",
                    run_id="run-123",
                )
                is_valid, violation = checker.check_invariant(new_event, history)
                assert is_valid is False
                assert "merge_completed cannot occur" in violation
        """
        ...
