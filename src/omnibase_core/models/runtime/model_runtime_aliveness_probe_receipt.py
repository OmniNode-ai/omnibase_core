# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Aliveness probe receipt: outcome of a single ``ModelRuntimeAlivenessProbeCommand`` run.

Wave 3 of the runtime-lifecycle-hardening plan. Emitted by the probe runner
(Task 9, in omnibase_infra) and consumed by the OCC receipt-gate, replay, and
projection paths.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.models.runtime.model_runtime_aliveness_probe import FailureState

__all__ = ["ModelRuntimeAlivenessProbeReceipt"]


class ModelRuntimeAlivenessProbeReceipt(BaseModel):
    """Outcome of a single probe run, emitted by the probe runner.

    PASS receipts MUST have an empty ``failure_states`` tuple; FAIL receipts MUST
    have at least one entry. Lag sampling is the final step of the probe lifecycle
    and is only executed after the terminal event and projection row are observed
    — ``lag_at_sample`` is None when sampling was skipped (e.g. probe timed out
    before reaching the lag step).
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    correlation_id: str = Field(..., min_length=1)
    status: Literal["PASS", "FAIL"]
    failure_states: tuple[FailureState, ...] = Field(default=())
    terminal_event_observed: bool
    projection_row_observed: bool
    lag_at_sample: int | None = Field(
        default=None,
        ge=0,
        description="Consumer-group lag at the post-projection sampling point; None when sampling was skipped",
    )
    timeout_seconds: int = Field(
        ..., gt=0, description="Echoed from the command for receipt independence"
    )
    started_at: datetime
    completed_at: datetime

    @model_validator(mode="after")
    def _validate_status_failure_states(self) -> Self:
        if self.status == "PASS" and self.failure_states:
            raise ValueError(
                "PASS receipts must have an empty failure_states tuple; "
                f"got {self.failure_states!r}"
            )
        if self.status == "FAIL" and not self.failure_states:
            raise ValueError(
                "FAIL receipts must list at least one failure_state from "
                "(timeout, terminal_failure_emitted, projection_write_failed, lag_above_threshold)"
            )
        return self
