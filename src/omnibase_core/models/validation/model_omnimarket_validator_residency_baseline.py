# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The shrink-only resident-validator list a consuming repository commits."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelOmnimarketValidatorResidencyBaseline"]


class ModelOmnimarketValidatorResidencyBaseline(BaseModel):
    """Paths of the validators still resident; an entry may be removed, never added."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    schema_version: int = Field(ge=1, description="Baseline schema version")
    resident_validators: tuple[str, ...] = Field(
        description="Repository-relative paths of the resident validators"
    )
