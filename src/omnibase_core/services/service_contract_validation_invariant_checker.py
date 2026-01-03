"""
Contract validation invariant checker service implementation.

This module provides the concrete implementation of contract validation
invariant checking, enforcing event ordering and state machine constraints
for contract validation workflows.

Invariants Enforced:
    1. validation_started must precede validation_passed or validation_failed
       for the same run_ref
    2. validation_passed and validation_failed are mutually exclusive per run_ref
    3. merge_started must precede merge_completed for the same run_ref
    4. merge_completed cannot occur if validation_failed occurred for the same run_ref

Related:
    - OMN-1146: Contract Validation Invariant Checker
    - ProtocolContractValidationInvariantChecker: Protocol definition

.. versionadded:: 0.4.0
"""

from omnibase_core.models.validation.model_contract_validation_event import (
    ContractValidationEventType,
    ModelContractValidationEvent,
)

__all__ = [
    "ServiceContractValidationInvariantChecker",
]


class ServiceContractValidationInvariantChecker:
    """
    Concrete implementation of contract validation invariant checking.

    Enforces the following invariants:
    1. validation_started must precede validation_passed or validation_failed
       for the same run_ref
    2. validation_passed and validation_failed are mutually exclusive per run_ref
    3. merge_started must precede merge_completed for the same run_ref
    4. merge_completed cannot occur if validation_failed occurred for the same run_ref

    Thread Safety:
        This implementation is thread-safe (stateless). Each method operates only
        on its input parameters without maintaining or mutating any shared state.
        All data structures (dictionaries, sets, lists) are created locally within
        each method call, ensuring thread isolation.

    Example:
        .. code-block:: python

            from omnibase_core.services.service_contract_validation_invariant_checker import (
                ServiceContractValidationInvariantChecker,
            )
            from omnibase_core.models.validation import ModelContractValidationEvent

            checker = ServiceContractValidationInvariantChecker()
            events = [
                ModelContractValidationEvent(
                    event_type="validation_started",
                    run_ref="run-123",
                ),
                ModelContractValidationEvent(
                    event_type="validation_passed",
                    run_ref="run-123",
                ),
            ]
            is_valid, violations = checker.validate_sequence(events)
            assert is_valid is True

    .. versionadded:: 0.4.0
    """

    def validate_sequence(
        self, events: list[ModelContractValidationEvent]
    ) -> tuple[bool, list[str]]:
        """
        Validate event ordering invariants for a sequence of events.

        Checks all invariants across the event sequence for all run_refs.

        Args:
            events: List of contract validation events to validate.
                Events should be ordered chronologically.

        Returns:
            A tuple of (is_valid, violations) where:
            - is_valid: True if all invariants are satisfied
            - violations: List of violation error strings
        """
        violations: list[str] = []

        # Group events by run_ref for efficient validation
        events_by_run: dict[str, list[ModelContractValidationEvent]] = {}
        for event in events:
            if event.run_ref not in events_by_run:
                events_by_run[event.run_ref] = []
            events_by_run[event.run_ref].append(event)

        # Validate invariants for each run_ref
        for run_ref, run_events in events_by_run.items():
            run_violations = self._validate_run_events(run_ref, run_events)
            violations.extend(run_violations)

        is_valid = len(violations) == 0
        return is_valid, violations

    def check_invariant(
        self,
        event: ModelContractValidationEvent,
        history: list[ModelContractValidationEvent],
    ) -> tuple[bool, str | None]:
        """
        Check a single event against historical event sequence.

        Args:
            event: The new event to validate.
            history: List of previously received events.

        Returns:
            A tuple of (is_valid, violation) where:
            - is_valid: True if event can be added without violation
            - violation: Error string if invalid, None otherwise
        """
        # Filter history to same run_ref
        run_history = [e for e in history if e.run_ref == event.run_ref]
        event_types_seen = {e.event_type for e in run_history}

        # Check each invariant
        violation = self._check_event_invariants(
            event.run_ref, event.event_type, event_types_seen
        )

        if violation:
            return False, violation
        return True, None

    def _validate_run_events(
        self, run_ref: str, events: list[ModelContractValidationEvent]
    ) -> list[str]:
        """
        Validate all events for a single run_ref.

        Args:
            run_ref: The run reference
            events: Events for this run, in chronological order

        Returns:
            List of violation error strings
        """
        violations: list[str] = []
        event_types_seen: set[ContractValidationEventType] = set()

        for event in events:
            violation = self._check_event_invariants(
                run_ref, event.event_type, event_types_seen
            )
            if violation:
                violations.append(violation)
            event_types_seen.add(event.event_type)

        return violations

    def _check_event_invariants(
        self,
        run_ref: str,
        event_type: ContractValidationEventType,
        event_types_seen: set[ContractValidationEventType],
    ) -> str | None:
        """
        Check invariants for a single event against what's been seen.

        Args:
            run_ref: The run reference
            event_type: The event type to check
            event_types_seen: Set of event types already seen for this run

        Returns:
            Violation error string if invariant violated, None otherwise
        """
        # Invariant 1: validation_started must precede validation_passed
        if (
            event_type == "validation_passed"
            and "validation_started" not in event_types_seen
        ):
            return (
                f"[run_ref={run_ref}] validation_passed received without prior "
                f"validation_started"
            )

        # Invariant 1: validation_started must precede validation_failed
        if (
            event_type == "validation_failed"
            and "validation_started" not in event_types_seen
        ):
            return (
                f"[run_ref={run_ref}] validation_failed received without prior "
                f"validation_started"
            )

        # Invariant 2: validation_passed and validation_failed are mutually exclusive
        if (
            event_type == "validation_passed"
            and "validation_failed" in event_types_seen
        ):
            return (
                f"[run_ref={run_ref}] validation_passed received but validation_failed "
                f"already occurred (mutually exclusive)"
            )

        if (
            event_type == "validation_failed"
            and "validation_passed" in event_types_seen
        ):
            return (
                f"[run_ref={run_ref}] validation_failed received but validation_passed "
                f"already occurred (mutually exclusive)"
            )

        # Invariant 3: merge_started must precede merge_completed
        if event_type == "merge_completed" and "merge_started" not in event_types_seen:
            return (
                f"[run_ref={run_ref}] merge_completed received without prior "
                f"merge_started"
            )

        # Invariant 4: merge_completed cannot occur if validation_failed occurred
        if event_type == "merge_completed" and "validation_failed" in event_types_seen:
            return (
                f"[run_ref={run_ref}] merge_completed cannot occur after "
                f"validation_failed"
            )

        return None
