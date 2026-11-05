# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Reducer state update a chain scenario expects (OMN-22478)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelChainScenarioStateUpdate(BaseModel):
    """A write the reducer must make: through which binding, to which target and key."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    binding: str = Field(
        ..., min_length=1, description="Reducer-state binding that records the write."
    )
    target: str = Field(
        ..., min_length=1, description="Table or store the write lands in."
    )
    key: str = Field(..., min_length=1, description="Entity key the write is for.")


__all__ = ["ModelChainScenarioStateUpdate"]
