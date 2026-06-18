# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Canonical risk/confidence policy for UI action gates (OMN-13131, ADR D2).

This module is the single canonical home in ``omnibase_core`` for the
action-gate risk/confidence fields the rev-4 Contract-Driven UI Platform plan
(§6) attributes to the action contract: ``confidence_threshold``,
``requires_user_confirmation``, ``risk_level``, ``reversible``, and a commit
level.

The ADR ``docs/adr/2026-06-17-ui-deterministic-projection-effect-layer.md``
(decision D2 and its plan-vs-code note) establishes that:

* these fields do **not** exist on ``ModelGate`` (approval/commit checkpoint:
  ``id/kind/description/required/status/approver/decided_at``) and must not be
  silently invented onto it; the implementing ticket must declare them in a real
  canonical source. ``ModelActionGatePolicy`` is that source.
* ``ModelGateSpec`` (objective-scoring hard gates, OMN-2537) is a **distinct**
  concept and is neither merged, aliased, renamed, nor extended here.

``ActionContract`` (a later wave) composes this policy as a strongly-typed
member; the capability dispatcher, disabled-state derivation, confirmation
requirements, UI affordances, and evidence requirements all read these fields
from this one model rather than from a frontend-only convention.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.ui.enum_commit_level import EnumCommitLevel
from omnibase_core.enums.ui.enum_risk_level import EnumRiskLevel

__all__ = ["ModelActionGatePolicy"]


class ModelActionGatePolicy(BaseModel):
    """Risk/confidence policy a UI action gate enforces before committing.

    A UI action is a declared ``onex.cmd.*`` command emitter (a button). Before
    that command is emitted, the action gate consults this policy to decide
    whether to require user confirmation, how to render affordances/disabled
    states, and what evidence the action must carry. The policy is declarative
    and platform-neutral; renderers derive behavior from it rather than encoding
    risk semantics in frontend code.

    Attributes:
        confidence_threshold: Minimum upstream confidence (0.0-1.0) required for
            the action to proceed without escalation. Below this, the gate
            escalates (e.g. forces confirmation regardless of other fields).
        requires_user_confirmation: Whether the action gate must obtain explicit
            user confirmation before the command is emitted.
        risk_level: Typed user-facing risk of executing the action.
        reversible: Whether the committed effect can be undone. This is the
            boolean fast-path; ``commit_level`` carries the full typed ordinal.
        commit_level: Typed durability of the effect the action commits
            (read-only, reversible, or irreversible).
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    confidence_threshold: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description=(
            "Minimum upstream confidence (0.0-1.0) for the action to proceed "
            "without escalation"
        ),
    )
    requires_user_confirmation: bool = Field(
        ...,
        description="Whether explicit user confirmation is required before emit",
    )
    risk_level: EnumRiskLevel = Field(
        ...,
        description="Typed user-facing risk of executing the action",
    )
    reversible: bool = Field(
        ...,
        description="Whether the committed effect can be undone",
    )
    commit_level: EnumCommitLevel = Field(
        ...,
        description="Typed durability of the effect the action commits",
    )
