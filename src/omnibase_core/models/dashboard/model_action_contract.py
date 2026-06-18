# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ActionContract — a UI action is a declared command emitter + approval gate.

Phase 0 UI contract primitive (OMN-13130, epic OMN-13129; plan
docs/plans/2026-06-13-contract-driven-ui-platform-unified-plan.md §6).

A button (or any UI action) is a **declared** ``onex.cmd.*`` command emitter
paired with its commit/approval gate. The approval gate is the canonical
``ModelGate`` primitive, **composed** here — this primitive does not redefine
approval semantics. The ADR
(docs/adr/2026-06-17-ui-deterministic-projection-effect-layer.md) records the
Gate-vs-GateSpec resolution: ActionContract composes ``ModelGate`` (approval);
``ModelGateSpec`` stays a distinct objective pass/fail primitive and is not
touched.

The risk/confidence policy the rev-4 plan §6 attributes to the action contract
(``confidence_threshold``, ``requires_user_confirmation``, ``risk_level``,
``reversible``, commit level) is **composed** here as ``ModelActionGatePolicy``
per the ADR D2 plan-vs-code note — those fields are NOT on ``ModelGate`` and are
declared in their canonical home ``ModelActionGatePolicy`` rather than invented
onto the approval gate.
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.models.dashboard.model_action_gate_policy import (
    ModelActionGatePolicy,
)
from omnibase_core.models.ticket.model_gate import ModelGate
from omnibase_core.models.validation.model_topic_suffix_parts import TOPIC_KIND_CMD
from omnibase_core.validation.validator_topic_suffix import validate_topic_suffix

__all__ = ["ModelActionContract"]


class ModelActionContract(BaseModel):
    """Declares the command a UI action emits and its approval gate.

    The action emits exactly one canonical command topic (a valid ONEX topic
    suffix whose kind token is ``cmd``). When ``approval_gate`` is present the
    action requires that gate's approval before it commits; ``ModelGate`` owns
    the approval semantics. ``correlation_required`` enforces that every emission
    carries a correlation ID (Phase 1 bus trace depends on this).
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    action_id: str = Field(  # string-id-ok: semantic action label, not a UUID
        ...,
        description="Stable semantic identifier for this action within a component",
        min_length=1,
    )
    command_topic: str = Field(
        ...,
        description="Canonical onex.cmd.* topic this action emits onto the bus",
        min_length=1,
    )
    label: str = Field(
        ...,
        description="Human-readable label rendered on the action control",
        min_length=1,
    )
    approval_gate: ModelGate | None = Field(
        default=None,
        description="Composed canonical approval gate; None means no approval required",
    )
    gate_policy: ModelActionGatePolicy | None = Field(
        default=None,
        description=(
            "Composed risk/confidence policy (confidence_threshold, "
            "requires_user_confirmation, risk_level, reversible, commit_level); "
            "None means no policy-driven gating beyond the approval gate"
        ),
    )
    correlation_required: bool = Field(
        default=True,
        description="Whether every emission must carry a correlation ID",
    )

    @field_validator("command_topic")
    @classmethod
    def validate_command_topic(cls, value: str) -> str:
        """A UI action may only emit a canonical command topic.

        Reuses the canonical ``validate_topic_suffix`` validator rather than
        embedding a topic literal, and requires the parsed kind token to be a
        command (``TOPIC_KIND_CMD``) — events/intents/snapshots are rejected.
        """
        result = validate_topic_suffix(value)
        if not result.is_valid or result.parsed is None:
            raise ValueError(
                f"command_topic {value!r} is not a valid ONEX topic suffix: "
                f"{result.error}"
            )
        if result.parsed.kind != TOPIC_KIND_CMD:
            raise ValueError(
                f"command_topic {value!r} has kind {result.parsed.kind!r}; "
                f"UI actions emit command topics only (kind={TOPIC_KIND_CMD!r})."
            )
        return value
