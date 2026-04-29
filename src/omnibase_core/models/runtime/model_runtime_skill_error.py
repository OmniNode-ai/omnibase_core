# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Structured runtime skill transport error."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.types import JsonType


class ModelRuntimeSkillError(BaseModel):
    """Structured error returned by the canonical runtime skill path."""

    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    code: Literal[
        "validation_error",
        "unknown_command",
        "runtime_unavailable",
        "dispatch_timeout",
        "dispatch_error",
    ] = Field(..., description="Stable runtime skill error code.")
    message: str = Field(..., min_length=1, description="Human-readable error.")
    retryable: bool = Field(
        default=False,
        description="Whether the caller may retry the same request.",
    )
    details: dict[str, JsonType] | None = Field(
        default=None,
        description="Optional typed diagnostic details.",
    )


__all__ = ["ModelRuntimeSkillError"]
