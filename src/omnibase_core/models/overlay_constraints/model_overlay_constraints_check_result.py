# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Deterministic result of the overlay-constraints check (OMN-22185)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue


class ModelOverlayConstraintsCheckResult(BaseModel):
    """Every issue found, in declaration order, and how many relations were judged."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    issues: tuple[ModelValidationIssue, ...] = Field(
        description="Enabled rule violations, in relation order"
    )
    exit_code: int = Field(
        description="One for an error or higher severity, otherwise zero"
    )
    relations_checked: int = Field(description="Relations evaluated against values")
