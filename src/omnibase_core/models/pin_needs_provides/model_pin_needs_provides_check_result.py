# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Deterministic result of the pin needs/provides check (OMN-21879)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue


class ModelPinNeedsProvidesCheckResult(BaseModel):
    """Every issue found, in document order, and how many verifier pins were judged."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    issues: tuple[ModelValidationIssue, ...] = Field(
        description="Enabled rule violations, ordered by document line"
    )
    exit_code: int = Field(
        description="One for an error or higher severity, otherwise zero"
    )
    pins_checked: int = Field(description="Verifier pins read from the document")
