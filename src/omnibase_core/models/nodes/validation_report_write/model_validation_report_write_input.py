# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Input model for the validation_report_write EFFECT node."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)

__all__ = ["ModelValidationReportWriteInput"]


class ModelValidationReportWriteInput(BaseModel):
    """A canonical OMN-2362 report and the file path to persist it at."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    report_path: str
    report: ModelValidationReport
    repository: str | None = Field(
        default=None,
        min_length=1,
        description="Repository the report was run on; required to publish triggered events.",
    )
    pull_request: int | None = Field(default=None, ge=1)
    head_sha: str | None = Field(default=None, min_length=7, max_length=64)
