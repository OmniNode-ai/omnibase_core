# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One runtime-identity gate finding (OMN-17308)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_runtime_identity_rule import EnumRuntimeIdentityRule

__all__ = ["ModelRuntimeIdentityViolation"]


class ModelRuntimeIdentityViolation(BaseModel):
    """A receipt that failed the runtime-identity gate, and why."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    path: str = Field(
        ...,
        min_length=1,
        description="Path of the offending receipt file.",
    )
    rule: EnumRuntimeIdentityRule = Field(
        ...,
        description="Which gate rule the receipt violated.",
    )
    detail: str = Field(
        ...,
        min_length=1,
        description="What is missing or wrong, named specifically enough to "
        "repair without opening the file.",
    )
