# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Validator-requirement gaps found by the requirements consumer."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.validation.model_validator_requirement_gap import (
    ModelValidatorRequirementGap,
)


class ModelRequirementsConsumerCheckOutput(BaseModel):
    """Every missing or silently skipped validator registration for the repo."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    gaps: tuple[ModelValidatorRequirementGap, ...] = ()
