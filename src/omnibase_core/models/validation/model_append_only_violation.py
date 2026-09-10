# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed violation emitted by the OCC append-only validator."""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_append_only_violation_kind import (
    EnumAppendOnlyViolationKind,
)


class ModelAppendOnlyViolation(BaseModel):
    """A single append-only violation with a human-readable detail."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: EnumAppendOnlyViolationKind
    target: str = Field(
        ..., description="dod_evidence item id or receipt file path that violated."
    )
    detail: str = Field(default="")


__all__ = ["ModelAppendOnlyViolation"]
