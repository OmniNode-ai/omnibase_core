# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Enum type definitions for plan-contract workflow.

Provides phase and action enumerations, transition tables, and
allowed-action mappings for the ModelPlanContract model.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumPlanPhase(StrValueHelper, str, Enum):
    """Lifecycle phases for plan contracts."""

    DRAFT = "draft"
    REVIEWED = "reviewed"
    TICKETED = "ticketed"
    EXECUTING = "executing"
    CLOSED = "closed"


@unique
class EnumPlanAction(StrValueHelper, str, Enum):
    """Actions performable on a plan contract.

    EDIT_PLAN: Replace the plan document (via replace_document()).
    SUBMIT_REVIEW: Trigger adversarial review (caller drives, model records).
    RECORD_REVIEW: Save a ModelPlanReviewResult (used by add_review()).
    LINK_TICKET: Associate a plan entry with a Linear ticket.
    START_EXECUTION: Transition TICKETED -> EXECUTING.
    CLOSE_PLAN: Transition EXECUTING -> CLOSED.
    """

    EDIT_PLAN = "edit_plan"
    SUBMIT_REVIEW = "submit_review"
    RECORD_REVIEW = "record_review"
    LINK_TICKET = "link_ticket"
    START_EXECUTION = "start_execution"
    CLOSE_PLAN = "close_plan"


# Phase to allowed-action mapping
PLAN_PHASE_ALLOWED_ACTIONS: dict[EnumPlanPhase, frozenset[EnumPlanAction]] = {
    EnumPlanPhase.DRAFT: frozenset(
        {
            EnumPlanAction.EDIT_PLAN,
            EnumPlanAction.SUBMIT_REVIEW,
            EnumPlanAction.RECORD_REVIEW,
        }
    ),
    EnumPlanPhase.REVIEWED: frozenset(
        {
            EnumPlanAction.EDIT_PLAN,
            EnumPlanAction.LINK_TICKET,
            EnumPlanAction.RECORD_REVIEW,
        }
    ),
    EnumPlanPhase.TICKETED: frozenset(
        {
            EnumPlanAction.START_EXECUTION,
            EnumPlanAction.LINK_TICKET,
        }
    ),
    EnumPlanPhase.EXECUTING: frozenset(
        {
            EnumPlanAction.CLOSE_PLAN,
            EnumPlanAction.LINK_TICKET,
        }
    ),
    EnumPlanPhase.CLOSED: frozenset(),
}

# Valid phase transitions
PLAN_VALID_TRANSITIONS: dict[EnumPlanPhase, frozenset[EnumPlanPhase]] = {
    EnumPlanPhase.DRAFT: frozenset({EnumPlanPhase.REVIEWED}),
    EnumPlanPhase.REVIEWED: frozenset(
        {
            EnumPlanPhase.DRAFT,
            EnumPlanPhase.TICKETED,
        }
    ),
    EnumPlanPhase.TICKETED: frozenset({EnumPlanPhase.EXECUTING}),
    EnumPlanPhase.EXECUTING: frozenset({EnumPlanPhase.CLOSED}),
    EnumPlanPhase.CLOSED: frozenset(),
}

# Aliases for cleaner imports
PlanPhase = EnumPlanPhase
PlanAction = EnumPlanAction

__all__ = [
    # Enum types (canonical names)
    "EnumPlanPhase",
    "EnumPlanAction",
    # Aliases for cleaner API
    "PlanPhase",
    "PlanAction",
    # Constants
    "PLAN_PHASE_ALLOWED_ACTIONS",
    "PLAN_VALID_TRANSITIONS",
]
