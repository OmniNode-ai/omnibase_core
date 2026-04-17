# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Validator-requirement compliance gap model.

Represents a single gap between the validator-requirements.yaml spec and a
repo's live ``.pre-commit-config.yaml`` + ``.github/workflows/`` state.

Related ticket: OMN-9115 (consumer), OMN-9051 (spec), parent OMN-9048.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_validator_requirement_gap_kind import (
    EnumValidatorRequirementGapKind,
)

__all__ = ["ModelValidatorRequirementGap"]


class ModelValidatorRequirementGap(BaseModel):
    """A single validator-requirement compliance gap."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    repo: str = Field(description="Target repo whose configuration is being scanned")
    validator: str = Field(
        description="Validator logical name (top-level key in validator-requirements.yaml)"
    )
    kind: EnumValidatorRequirementGapKind = Field(
        description="Classification of the compliance gap"
    )
    detail: str = Field(description="Human-readable detail describing the gap")
