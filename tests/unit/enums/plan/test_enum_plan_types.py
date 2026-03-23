# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import pytest

from omnibase_core.enums.plan import PlanAction, PlanPhase
from omnibase_core.enums.plan.enum_plan_types import (
    PLAN_PHASE_ALLOWED_ACTIONS,
    PLAN_VALID_TRANSITIONS,
    EnumPlanAction,
    EnumPlanPhase,
)


@pytest.mark.unit
class TestEnumPlanPhase:
    def test_all_members_exist_with_correct_values(self) -> None:
        assert EnumPlanPhase.DRAFT.value == "draft"
        assert EnumPlanPhase.REVIEWED.value == "reviewed"
        assert EnumPlanPhase.TICKETED.value == "ticketed"
        assert EnumPlanPhase.EXECUTING.value == "executing"
        assert EnumPlanPhase.CLOSED.value == "closed"

    def test_str_value_helper(self) -> None:
        assert str(EnumPlanPhase.DRAFT) == "draft"
        assert str(EnumPlanPhase.REVIEWED) == "reviewed"
        assert str(EnumPlanPhase.TICKETED) == "ticketed"
        assert str(EnumPlanPhase.EXECUTING) == "executing"
        assert str(EnumPlanPhase.CLOSED) == "closed"

    def test_member_count(self) -> None:
        assert len(EnumPlanPhase) == 5


@pytest.mark.unit
class TestEnumPlanAction:
    def test_all_members_exist_with_correct_values(self) -> None:
        assert EnumPlanAction.EDIT_PLAN.value == "edit_plan"
        assert EnumPlanAction.SUBMIT_REVIEW.value == "submit_review"
        assert EnumPlanAction.RECORD_REVIEW.value == "record_review"
        assert EnumPlanAction.LINK_TICKET.value == "link_ticket"
        assert EnumPlanAction.START_EXECUTION.value == "start_execution"
        assert EnumPlanAction.CLOSE_PLAN.value == "close_plan"

    def test_str_value_helper(self) -> None:
        assert str(EnumPlanAction.EDIT_PLAN) == "edit_plan"
        assert str(EnumPlanAction.SUBMIT_REVIEW) == "submit_review"
        assert str(EnumPlanAction.RECORD_REVIEW) == "record_review"
        assert str(EnumPlanAction.LINK_TICKET) == "link_ticket"
        assert str(EnumPlanAction.START_EXECUTION) == "start_execution"
        assert str(EnumPlanAction.CLOSE_PLAN) == "close_plan"

    def test_member_count(self) -> None:
        assert len(EnumPlanAction) == 6


@pytest.mark.unit
class TestPlanPhaseAllowedActions:
    def test_covers_all_phases(self) -> None:
        for phase in EnumPlanPhase:
            assert phase in PLAN_PHASE_ALLOWED_ACTIONS

    def test_closed_has_empty_frozenset(self) -> None:
        assert PLAN_PHASE_ALLOWED_ACTIONS[EnumPlanPhase.CLOSED] == frozenset()

    def test_every_action_appears_in_at_least_one_phase(self) -> None:
        all_allowed = frozenset().union(*PLAN_PHASE_ALLOWED_ACTIONS.values())
        for action in EnumPlanAction:
            assert action in all_allowed, f"{action} not allowed in any phase"

    def test_draft_allows_expected_actions(self) -> None:
        allowed = PLAN_PHASE_ALLOWED_ACTIONS[EnumPlanPhase.DRAFT]
        assert allowed == frozenset(
            {
                EnumPlanAction.EDIT_PLAN,
                EnumPlanAction.SUBMIT_REVIEW,
                EnumPlanAction.RECORD_REVIEW,
            }
        )

    def test_executing_allows_expected_actions(self) -> None:
        allowed = PLAN_PHASE_ALLOWED_ACTIONS[EnumPlanPhase.EXECUTING]
        assert allowed == frozenset(
            {
                EnumPlanAction.CLOSE_PLAN,
                EnumPlanAction.LINK_TICKET,
            }
        )

    def test_values_are_frozensets(self) -> None:
        for phase, actions in PLAN_PHASE_ALLOWED_ACTIONS.items():
            assert isinstance(actions, frozenset), f"{phase} value is not a frozenset"


@pytest.mark.unit
class TestPlanValidTransitions:
    def test_covers_all_phases(self) -> None:
        for phase in EnumPlanPhase:
            assert phase in PLAN_VALID_TRANSITIONS

    def test_closed_is_terminal(self) -> None:
        assert PLAN_VALID_TRANSITIONS[EnumPlanPhase.CLOSED] == frozenset()

    def test_draft_can_only_transition_to_reviewed(self) -> None:
        assert PLAN_VALID_TRANSITIONS[EnumPlanPhase.DRAFT] == frozenset(
            {EnumPlanPhase.REVIEWED}
        )

    def test_reviewed_can_transition_to_draft_or_ticketed(self) -> None:
        assert PLAN_VALID_TRANSITIONS[EnumPlanPhase.REVIEWED] == frozenset(
            {EnumPlanPhase.DRAFT, EnumPlanPhase.TICKETED}
        )

    def test_every_non_closed_phase_has_at_least_one_target(self) -> None:
        for phase in EnumPlanPhase:
            if phase is EnumPlanPhase.CLOSED:
                continue
            assert len(PLAN_VALID_TRANSITIONS[phase]) >= 1, (
                f"{phase} has no valid transitions"
            )

    def test_values_are_frozensets(self) -> None:
        for phase, targets in PLAN_VALID_TRANSITIONS.items():
            assert isinstance(targets, frozenset), f"{phase} value is not a frozenset"


@pytest.mark.unit
class TestAliases:
    def test_plan_phase_alias(self) -> None:
        assert PlanPhase is EnumPlanPhase

    def test_plan_action_alias(self) -> None:
        assert PlanAction is EnumPlanAction
