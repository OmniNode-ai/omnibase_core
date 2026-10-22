# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Input of the validator-triggered emitter (OMN-21277)."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)

__all__ = ["ModelValidatorTriggeredEmitInput"]


class ModelValidatorTriggeredEmitInput(BaseModel):
    """A validator report and the change it was run on."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    report: ModelValidationReport
    repository: str = Field(min_length=1)
    pull_request: int | None = Field(default=None, ge=1)
    head_sha: str | None = Field(default=None, min_length=7, max_length=64)
    correlation_id: UUID
