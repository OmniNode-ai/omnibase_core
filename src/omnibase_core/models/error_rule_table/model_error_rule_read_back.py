# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Registered failure read-back and its time allowance."""

from pydantic import BaseModel, ConfigDict, Field


class ModelErrorRuleReadBack(BaseModel):
    """Read-back state check; no expression or command can be supplied."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    state_check: str = Field(min_length=1)
    timeout_s: int = Field(gt=0, strict=True)
