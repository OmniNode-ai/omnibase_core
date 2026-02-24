# SPDX-FileCopyrightText: 2026 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Tests for Invalid Action Rejection at Contract Graph Boundary (OMN-2554).

Covers:
- Valid selection: action in enumerated set -> Valid result
- Invalid selection: action not in set -> Rejected(NotInActionSet)
- Empty action set -> any selection rejected
- RejectionReason is structured and machine-readable
- GraphBoundaryEnforcer is stateless (no exceptions for invalid selections)
- ValidationResult is a discriminated union (Valid | Rejected)
- Rejection includes session_id context for logging

Also tests the discriminated union types:
- NotInActionSet, GuardFailed, PreconditionNotSatisfied
- Valid, Rejected
- ValidationResult round-trips via JSON
"""

import json

import pytest

from omnibase_core.navigation.model_action_set import TypedAction
from omnibase_core.navigation.model_graph_boundary import (
    GraphBoundaryEnforcer,
    GuardFailed,
    NotInActionSet,
    PreconditionNotSatisfied,
    Rejected,
    Valid,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_action(
    transition_id: str,
    source_id: str = "node.a",
    target_id: str = "node.b",
    diff_size: int = 0,
    latency: int = 0,
) -> TypedAction:
    return TypedAction(
        transition_id=transition_id,
        source_state_id=source_id,
        target_state_id=target_id,
        diff_size_estimate=diff_size,
        latency_estimate_ms=latency,
    )


# ---------------------------------------------------------------------------
# RejectionReason type tests
# ---------------------------------------------------------------------------


class TestRejectionReasons:
    def test_not_in_action_set(self) -> None:
        reason = NotInActionSet(transition_id="t1", state_id="node.a")
        assert reason.kind == "not_in_action_set"
        assert reason.transition_id == "t1"
        assert reason.state_id == "node.a"

    def test_guard_failed(self) -> None:
        reason = GuardFailed(
            transition_id="t1",
            guard_name="capability",
            detail="Missing llm.gen",
        )
        assert reason.kind == "guard_failed"
        assert reason.guard_name == "capability"

    def test_precondition_not_satisfied(self) -> None:
        reason = PreconditionNotSatisfied(
            transition_id="t1",
            precondition="datasource_ready",
        )
        assert reason.kind == "precondition_not_satisfied"
        assert reason.precondition == "datasource_ready"

    def test_not_in_action_set_frozen(self) -> None:
        reason = NotInActionSet(transition_id="t1", state_id="node.a")
        with pytest.raises(Exception):
            reason.transition_id = "t2"  # type: ignore[misc]

    def test_rejection_reason_json_serializable(self) -> None:
        reason = NotInActionSet(transition_id="t1", state_id="node.a")
        data = json.loads(reason.model_dump_json())
        assert data["kind"] == "not_in_action_set"
        assert data["transition_id"] == "t1"


# ---------------------------------------------------------------------------
# ValidationResult type tests
# ---------------------------------------------------------------------------


class TestValidationResultTypes:
    def test_valid_result(self) -> None:
        result = Valid(transition_id="t1")
        assert result.kind == "valid"
        assert result.transition_id == "t1"

    def test_rejected_result(self) -> None:
        reason = NotInActionSet(transition_id="t1", state_id="node.a")
        result = Rejected(reason=reason)
        assert result.kind == "rejected"
        assert isinstance(result.reason, NotInActionSet)

    def test_valid_json_roundtrip(self) -> None:
        result = Valid(transition_id="t42")
        data = json.loads(result.model_dump_json())
        assert data["kind"] == "valid"
        assert data["transition_id"] == "t42"

    def test_rejected_json_roundtrip(self) -> None:
        reason = GuardFailed(
            transition_id="t1",
            guard_name="policy_tier",
            detail="Tier 5 exceeds max 2",
        )
        result = Rejected(reason=reason)
        data = json.loads(result.model_dump_json())
        assert data["kind"] == "rejected"
        assert data["reason"]["kind"] == "guard_failed"


# ---------------------------------------------------------------------------
# GraphBoundaryEnforcer tests
# ---------------------------------------------------------------------------


class TestGraphBoundaryEnforcer:
    def setup_method(self) -> None:
        self.enforcer = GraphBoundaryEnforcer()

    def test_valid_selection(self) -> None:
        action = make_action("t1")
        action_set = [action]
        result = self.enforcer.validate(
            current_state_id="node.a",
            selected_action=action,
            action_set=action_set,
            session_id="session-001",
        )
        assert isinstance(result, Valid)
        assert result.transition_id == "t1"

    def test_valid_selection_from_multiple(self) -> None:
        a1 = make_action("t1")
        a2 = make_action("t2")
        a3 = make_action("t3")
        result = self.enforcer.validate(
            current_state_id="node.a",
            selected_action=a2,
            action_set=[a1, a2, a3],
        )
        assert isinstance(result, Valid)
        assert result.transition_id == "t2"

    def test_selection_not_in_action_set(self) -> None:
        valid_action = make_action("t1")
        bad_action = make_action("t.invalid")
        result = self.enforcer.validate(
            current_state_id="node.a",
            selected_action=bad_action,
            action_set=[valid_action],
            session_id="session-002",
        )
        assert isinstance(result, Rejected)
        assert isinstance(result.reason, NotInActionSet)
        assert result.reason.transition_id == "t.invalid"
        assert result.reason.state_id == "node.a"

    def test_empty_action_set_rejects_any_selection(self) -> None:
        action = make_action("t1")
        result = self.enforcer.validate(
            current_state_id="node.a",
            selected_action=action,
            action_set=[],
            session_id="session-003",
        )
        assert isinstance(result, Rejected)
        assert isinstance(result.reason, NotInActionSet)

    def test_no_exception_for_invalid_selection(self) -> None:
        """Enforcer must not raise for model-generated invalid selections."""
        bad_action = make_action("t.hallucinated")
        # Must return Rejected, not raise
        result = self.enforcer.validate(
            current_state_id="node.a",
            selected_action=bad_action,
            action_set=[],
        )
        assert isinstance(result, Rejected)

    def test_enforcer_is_stateless(self) -> None:
        """Multiple calls return independent results (no shared state)."""
        valid_action = make_action("t1")
        bad_action = make_action("t.bad")
        action_set = [valid_action]

        r1 = self.enforcer.validate("node.a", valid_action, action_set)
        r2 = self.enforcer.validate("node.a", bad_action, action_set)
        r3 = self.enforcer.validate("node.a", valid_action, action_set)

        assert isinstance(r1, Valid)
        assert isinstance(r2, Rejected)
        assert isinstance(r3, Valid)

    def test_session_id_optional(self) -> None:
        """Session ID is optional; omitting it does not cause errors."""
        action = make_action("t1")
        result = self.enforcer.validate(
            current_state_id="node.a",
            selected_action=action,
            action_set=[action],
        )
        assert isinstance(result, Valid)

    def test_rejection_reason_is_machine_readable(self) -> None:
        """RejectionReason must be structured (not free-form string)."""
        bad_action = make_action("t.bad")
        result = self.enforcer.validate(
            current_state_id="node.a",
            selected_action=bad_action,
            action_set=[],
        )
        assert isinstance(result, Rejected)
        reason = result.reason
        # Reason must have a machine-readable 'kind' field
        assert hasattr(reason, "kind")
        assert isinstance(reason.kind, str)
        # Reason must be JSON serializable
        data = json.loads(reason.model_dump_json())
        assert "kind" in data

    def test_result_kind_discriminator(self) -> None:
        """ValidationResult must be identifiable by 'kind' field."""
        action = make_action("t1")
        valid_result = self.enforcer.validate("node.a", action, [action])
        rejected_result = self.enforcer.validate("node.a", action, [])

        assert valid_result.kind == "valid"
        assert rejected_result.kind == "rejected"
