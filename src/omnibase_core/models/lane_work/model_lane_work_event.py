# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The typed event a lane work fold takes in (OMN-26699, plan section 3.3).

One model, discriminated by ``kind``: the single-class-per-file gate allows one
model per file, so the per-kind rules are a table checked by one validator, not
twenty-nine subclasses. An unknown ``kind`` fails enum validation; a known kind
missing a field it owes fails the validator. The model holds no handler, no I/O
and no topic name.
"""

from __future__ import annotations

from typing import Final

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_lane_work_blocked_reason import (
    EnumLaneWorkBlockedReason,
)
from omnibase_core.enums.enum_lane_work_event import EnumLaneWorkEvent
from omnibase_core.enums.enum_lane_work_state import EnumLaneWorkState
from omnibase_core.models.lane_work.model_lane_work_action import (
    LaneWorkActionId,
    LaneWorkRecordId,
    LaneWorkWorkflowId,
)
from omnibase_core.models.lane_work.model_lane_work_change import ModelLaneWorkChange

_E = EnumLaneWorkEvent

# Closed class values of the kinds that carry one ("classes are a field").
EVENT_CLASSES: Final[dict[EnumLaneWorkEvent, frozenset[str]]] = {
    _E.COMMIT_REFUSED: frozenset({"release_identity", "hook"}),
    _E.PUSH_REFUSED: frozenset(
        {
            "guard_ledger_cell",
            "missing_remote",
            "check_failed",
            "protected_branch",
            "push_rejected",
        }
    ),
    _E.PROOF_FAILED: frozenset({"tests", "infra"}),
}

# Kinds that answer a node action and so must name its action id.
_NEEDS_ACTION_ID: Final[frozenset[EnumLaneWorkEvent]] = frozenset(
    {
        _E.PROOF_PASSED,
        _E.PROOF_FAILED,
        _E.PROOF_POSTED,
        _E.PROOF_POST_FAILED,
        _E.HANDOFF_WRITTEN,
        _E.HANDOFF_FAILED,
        _E.HELP_CAUSE_FOUND,
        _E.HELP_RETRY,
        _E.HELP_STOP,
        _E.HELP_FAILED,
    }
)
_NEEDS_HEAD: Final[frozenset[EnumLaneWorkEvent]] = frozenset(
    {
        _E.CHECK_RED,
        _E.CHECK_PENDING,
        _E.CHECK_GREEN,
        _E.HEAD_MOVED,
        _E.PROOF_PASSED,
        _E.HANDOFF_WRITTEN,
        _E.HANDOFF_FAILED,
    }
)
_NEEDS_OBSERVATION: Final[frozenset[EnumLaneWorkEvent]] = frozenset(
    {_E.CHECK_RED, _E.CHECK_PENDING, _E.CHECK_GREEN}
)


class ModelLaneWorkEvent(BaseModel):
    """One input to the lane work fold; ``input_id`` is its dedup key."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    kind: EnumLaneWorkEvent
    workflow_id: LaneWorkWorkflowId | None = Field(
        default=None, description="Absent only on start, which is answered with one."
    )
    input_id: LaneWorkRecordId
    change: ModelLaneWorkChange
    head_sha: str | None = Field(default=None, pattern=r"^[0-9a-f]{7,40}$")
    evidence: tuple[str, ...] = ()
    event_class: str | None = Field(
        default=None, description="commit_refused, push_refused and proof_failed only."
    )
    action_id: LaneWorkActionId | None = None
    observed_at: AwareDatetime | None = None
    ci_read_at: AwareDatetime | None = None
    worker_tier: str | None = Field(default=None, min_length=1)
    lane_name: str | None = Field(default=None, min_length=1)
    body_ticket_ids: tuple[str, ...] = ()
    red_kind: str | None = Field(default=None, min_length=1)
    deadline_id: LaneWorkRecordId | None = None
    deadline_attempt: int | None = Field(default=None, ge=1)
    request_id: str | None = Field(default=None, min_length=1)
    help_origin: EnumLaneWorkState | None = None
    reason: EnumLaneWorkBlockedReason | None = None
    decision_needed: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def _kind_fields(self) -> ModelLaneWorkEvent:
        kind = self.kind
        missing: list[str] = []

        def need(name: str) -> None:
            if getattr(self, name) is None:
                missing.append(name)

        if kind is not _E.START:
            need("workflow_id")
        if kind in _NEEDS_ACTION_ID:
            need("action_id")
        if kind in _NEEDS_HEAD:
            need("head_sha")
        if kind in _NEEDS_OBSERVATION:
            need("observed_at")
            need("ci_read_at")
        if kind is _E.START:
            need("worker_tier")
        elif kind is _E.WORKER_STARTED:
            need("lane_name")
        elif kind is _E.LOG_READ:
            need("red_kind")
        elif kind is _E.DEADLINE_PASSED:
            need("deadline_id")
            need("deadline_attempt")
        elif kind in (_E.HANDOFF_WRITTEN, _E.HANDOFF_FAILED):
            need("request_id")
        elif kind is _E.HELP_RETRY:
            need("help_origin")
        elif kind is _E.HELP_STOP:
            need("reason")
            need("decision_needed")
        if missing:
            raise ValueError(f"{kind.value} requires {', '.join(missing)}")

        allowed = EVENT_CLASSES.get(kind)
        if allowed is None:
            if self.event_class is not None:
                raise ValueError(f"{kind.value} carries no event_class")
        elif self.event_class not in allowed:
            raise ValueError(
                f"{kind.value} requires event_class in {sorted(allowed)}, "
                f"got {self.event_class!r}"
            )
        return self


__all__ = ["EVENT_CLASSES", "ModelLaneWorkEvent"]
