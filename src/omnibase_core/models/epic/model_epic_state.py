# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelEpicState — epic-team execution state contract.

Migration-phase capture model. Status fields use ``str`` instead of enums
to avoid breaking existing state files during initial adoption. A follow-up
task should introduce ``EnumEpicStatus`` and ``EnumEpicWaveStatus`` once the
actual status vocabulary stabilizes from production usage.

Write safety: Producers MUST use atomic write (temp file + ``os.rename()``)
to prevent consumers from reading partial files. Consumers SHOULD retry once
on ``yaml.YAMLError`` (transient partial-read during atomic rename window).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

__all__ = [
    "ModelEpicState",
    "ModelEpicWave",
    "ModelEpicTicketStatus",
    "EpicState",
]

# Migration corpus (observed 2026-03-08):
#
# Epic statuses: done, monitoring, prs_open, wave0_complete,
#   phase3_complete, in_review, complete, awaiting_merge, queued, running
#
# Ticket statuses: merged, pr_open, done, pending, pr_created,
#   completed, in_review, queued, in-review, blocked, pr_open_ci_pending,
#   duplicate, running, resolved_manual, manual, auto-merge-pending,
#   auto_merge_pending, skipped_manual, ready_to_start, pr_review_loop,
#   pr_pending_merge, in_progress, done_skipped, dispatching, deferred,
#   canceled, auto_merge_held, no-op, merged_pending_approval,
#   pr_open_auto_merge_queued, complete, ci_watch, blocked_by_pr407,
#   blocked_by_omn2675, blocked_by_OMN-3410
#
# Wave statuses: done, pending, merged, running, pr_created,
#   dispatching, deferred, completed, blocked_design_decision
#
# Production field name observations:
#   - Waves use ``wave`` (not ``wave_number``) as the field key
#   - Wave numbers start at 0 (zero-indexed)
#   - ticket_status (singular) maps ticket_id -> str (flat), not -> object
#
# This corpus informs future EnumEpicStatus / EnumEpicWaveStatus design.


class ModelEpicTicketStatus(BaseModel):
    """Status of a single ticket within an epic execution.

    The ``status`` field uses ``str`` instead of an enum to accommodate the
    35+ distinct ticket status strings observed in production state files
    (see corpus above). Unknown fields from state files are silently ignored.
    """

    model_config = ConfigDict(extra="ignore", from_attributes=True)

    ticket_id: str = Field(..., min_length=1)
    status: str = Field(..., min_length=1)
    pr_url: str | None = Field(default=None)
    pr_number: int | None = Field(default=None)
    branch: str | None = Field(default=None)
    error: str | None = Field(default=None)
    failure_type: str | None = Field(default=None)


class ModelEpicWave(BaseModel):
    """A wave of parallel ticket execution within an epic.

    The ``status`` field uses ``str`` instead of an enum to accommodate the
    9+ distinct wave status strings observed in production state files.
    Unknown fields from state files are silently ignored.
    """

    model_config = ConfigDict(
        extra="ignore", from_attributes=True, populate_by_name=True
    )

    wave_number: int = Field(..., ge=0, alias="wave")
    ticket_ids: list[str] = Field(default_factory=list, alias="tickets")
    status: str = Field(default="pending")


class ModelEpicState(BaseModel):
    """State of an epic-team execution.

    Written to ``~/.claude/epics/{epic_id}/state.yaml``.
    Read by epic-team (--resume) for checkpoint recovery.

    Migration-phase capture model. Status fields use ``str`` instead of enums
    to avoid breaking existing state files during initial adoption. A follow-up
    task should introduce ``EnumEpicStatus`` and ``EnumEpicWaveStatus`` once the
    actual status vocabulary stabilizes from production usage.

    Mutable: updated as waves complete and tickets progress.

    Write safety: Producers MUST use atomic write (temp file + ``os.rename()``)
    to prevent consumers from reading partial files. Follow the pattern in
    ``_lib/run-state/helpers.md``. Consumers SHOULD retry once on
    ``yaml.YAMLError`` (transient partial-read during atomic rename window).
    """

    model_config = ConfigDict(
        extra="ignore",
        from_attributes=True,
        populate_by_name=True,
    )

    epic_id: str = Field(..., min_length=1)
    run_id: str = Field(..., min_length=1)
    status: str = Field(default="queued")

    waves: list[ModelEpicWave] = Field(default_factory=list)
    ticket_statuses: dict[str, ModelEpicTicketStatus] = Field(
        default_factory=dict, alias="ticket_status"
    )

    # Failure tracking
    failures: dict[str, Any] = Field(default_factory=dict)
    open_prs: dict[str, str] = Field(
        default_factory=dict,
        description="Map of ticket_id -> PR URL for open PRs.",
    )

    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_update_utc: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="before")
    @classmethod
    def _coerce_ticket_status(cls, values: Any) -> Any:
        """Coerce flat ticket_status dict (str -> str) to str -> object.

        Production state files use ``ticket_status: {OMN-3866: pending}``
        (flat str values), not ``{OMN-3866: {ticket_id: OMN-3866, status: pending}}``.
        This validator normalizes the flat form into ModelEpicTicketStatus objects.
        """
        if not isinstance(values, dict):
            return values
        # Handle both alias ("ticket_status") and Python name ("ticket_statuses")
        for key in ("ticket_status", "ticket_statuses"):
            raw = values.get(key)
            if raw is None:
                continue
            if isinstance(raw, dict):
                coerced: dict[str, Any] = {}
                for tid, val in raw.items():
                    if isinstance(val, str):
                        coerced[tid] = {"ticket_id": tid, "status": val}
                    else:
                        coerced[tid] = val
                values[key] = coerced
        return values

    def to_yaml(self) -> str:
        """Serialize to YAML string for file I/O.

        Uses aliases (``wave``, ``tickets``, ``ticket_status``) so the output
        matches the format expected by existing producers and consumers.
        """
        data = self.model_dump(mode="json", by_alias=True)
        return yaml.dump(data, default_flow_style=False, sort_keys=False)

    @classmethod
    def from_yaml(cls, data: str) -> ModelEpicState:
        """Deserialize from YAML string."""
        parsed = yaml.safe_load(data)
        return cls.model_validate(parsed)


EpicState = ModelEpicState
