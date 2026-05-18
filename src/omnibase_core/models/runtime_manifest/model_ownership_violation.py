# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from pydantic import BaseModel, ConfigDict, Field


class ModelOwnershipViolation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    contract_name: str = Field(..., min_length=1)
    violation_type: str = Field(..., min_length=1)
    detail: str = Field(..., min_length=1)


__all__ = ["ModelOwnershipViolation"]
