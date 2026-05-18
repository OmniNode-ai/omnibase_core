# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelAislopRuleOverride — per-repo override for an aislop rule (OMN-11132)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ModelAislopRuleOverride(BaseModel):
    """A per-repo override for an existing rule or a new custom rule."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(description="Rule name to override or new rule name")
    severity: Literal["ERROR", "WARNING", "INFO"] | None = Field(
        default=None, description="Override severity (None = keep default)"
    )
    enabled: bool | None = Field(
        default=None, description="Override enabled flag (None = keep default)"
    )
    file_globs: list[str] | None = Field(
        default=None, description="Override file globs (None = keep default)"
    )
    allow_new: bool = Field(
        default=False,
        description="If True, treat as a new custom rule rather than an override",
    )


__all__ = ["ModelAislopRuleOverride"]
