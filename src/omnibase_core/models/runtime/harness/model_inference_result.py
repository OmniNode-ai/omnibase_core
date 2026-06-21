# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""ModelInferenceResult: result from a harness inference adapter (OMN-13420)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelInferenceResult(BaseModel):
    """Result returned from a harness inference adapter."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    completion: str = Field(..., description="Completion text.")
    model: str = Field(..., description="Model that produced the completion.")
    adapter: str = Field(
        ..., description="Adapter identifier (fixture | curl) for provenance."
    )


__all__ = ["ModelInferenceResult"]
