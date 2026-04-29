# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelOvernightHaltCondition — halt condition for overnight pipeline sessions (OMN-10251)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from omnibase_core.utils.util_decorators import allow_string_id


@allow_string_id(
    reason=(
        "condition_id is a named halt condition identifier (e.g., 'cost_ceiling'), "
        "not a system UUID."
    )
)
class ModelOvernightHaltCondition(BaseModel):
    """Condition that triggers an action when its trigger clause matches.

    On-halt actions:
      - ``dispatch_skill``: fire the named skill as a foreground recovery and continue.
      - ``halt_and_notify``: stop the pipeline and emit a tick event.
      - ``hard_halt``: stop the pipeline immediately.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    condition_id: str  # string-id-ok: named halt condition identifier, not a UUID
    description: str
    check_type: Literal[
        "cost_ceiling",
        "phase_failure_count",
        "time_elapsed",
        "pr_blocked_too_long",
        "required_outcome_missing",
        "custom",
    ]
    threshold: float = 0.0
    on_halt: Literal["hard_halt", "dispatch_skill", "halt_and_notify"] = "hard_halt"
    skill: str | None = None
    pr: int | None = None
    threshold_minutes: float | None = None
    outcome: str | None = None

    @model_validator(mode="after")
    def _enforce_conditional_fields(self) -> ModelOvernightHaltCondition:
        if self.on_halt == "dispatch_skill" and not self.skill:
            msg = "skill is required when on_halt='dispatch_skill'"
            raise ValueError(
                msg
            )  # error-ok: Pydantic model_validator requires ValueError
        if self.check_type == "pr_blocked_too_long":
            if self.pr is None:
                msg = "pr is required when check_type='pr_blocked_too_long'"
                raise ValueError(
                    msg
                )  # error-ok: Pydantic model_validator requires ValueError
            if self.threshold_minutes is None:
                msg = (
                    "threshold_minutes is required"
                    " when check_type='pr_blocked_too_long'"
                )
                raise ValueError(
                    msg
                )  # error-ok: Pydantic model_validator requires ValueError
        if self.check_type == "required_outcome_missing" and not self.outcome:
            msg = "outcome is required when check_type='required_outcome_missing'"
            raise ValueError(
                msg
            )  # error-ok: Pydantic model_validator requires ValueError
        return self


__all__ = ["ModelOvernightHaltCondition"]
