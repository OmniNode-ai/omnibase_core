# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelGoalSupervisorExecutionResult contract model."""

from __future__ import annotations

import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.enums.enum_goal_supervisor_outcome import EnumGoalSupervisorOutcome
from omnibase_core.models.validation.model_goal_execution_result import (
    ModelGoalExecutionResult,
)
from omnibase_core.models.validation.model_goal_supervisor_execution_receipt import (
    ModelGoalSupervisorExecutionReceipt,
)
from omnibase_core.models.validation.model_goal_supervisor_execution_request import (
    ModelGoalSupervisorExecutionRequest,
)

_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class ModelGoalSupervisorExecutionResult(BaseModel):
    """Phase-one result, with detached authentic receipt and no final attestation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    outcome: EnumGoalSupervisorOutcome
    request: ModelGoalSupervisorExecutionRequest
    execution_receipt: ModelGoalSupervisorExecutionReceipt
    execution_record_id: UUID
    execution_identity: str = Field(..., min_length=1, max_length=256)
    started_at: datetime
    completed_at: datetime
    result: ModelGoalExecutionResult
    report_sha256: str

    @field_validator("report_sha256")
    @classmethod
    def _report_digest_is_valid(cls, value: str) -> str:
        if not _SHA256_RE.fullmatch(value):
            raise ValueError("report digest must use sha256:<64 lowercase hex>")
        return value

    @model_validator(mode="after")
    def _execution_identity_is_policy_authorized(
        self,
    ) -> ModelGoalSupervisorExecutionResult:
        for name, value in (
            ("started_at", self.started_at),
            ("completed_at", self.completed_at),
        ):
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(f"{name} must include a timezone")
        if self.completed_at <= self.started_at:
            raise ValueError("completed_at must be after started_at")
        if self.result.attempt_id != self.request.attempt_id:
            raise ValueError("canonical result must bind the allocated attempt")
        if self.execution_receipt.policy_sha256 != self.request.policy.content_sha256():
            raise ValueError("execution receipt does not bind protected policy content")
        if (
            self.execution_receipt.execution_request_sha256
            != self.request.execution_plan_sha256()
        ):
            raise ValueError("execution receipt does not bind the execution plan")
        if (
            self.execution_identity
            not in self.request.policy.allowed_execution_identities
        ):
            raise ValueError("execution identity is not authorized by protected policy")
        return self
