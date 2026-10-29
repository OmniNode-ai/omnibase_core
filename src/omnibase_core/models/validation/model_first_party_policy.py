# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from pydantic import BaseModel, ConfigDict, Field


class ModelFirstPartyPolicy(BaseModel):
    """All policy is supplied by the validation subcontract."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)
    file_globs: list[str] = Field(min_length=1)
    remediation: str = Field(min_length=1)
