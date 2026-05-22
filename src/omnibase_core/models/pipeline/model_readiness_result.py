# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Readiness result model for pipeline pre-execution gate checks."""

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelReadinessResult"]


class ModelReadinessResult(BaseModel):
    """Outcome of a readiness gate check before pipeline execution."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    ready: bool
    blocking: tuple[str, ...] = Field(default_factory=tuple)
    conditional: tuple[str, ...] = Field(default_factory=tuple)
    advisory: tuple[str, ...] = Field(default_factory=tuple)
