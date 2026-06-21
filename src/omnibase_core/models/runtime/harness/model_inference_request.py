# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""ModelInferenceRequest: request to a harness inference adapter (OMN-13420)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelInferenceRequest(BaseModel):
    """Request passed to a harness inference adapter."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    prompt: str = Field(..., description="Prompt text to complete.")
    model: str = Field(default="recorded-fixture", description="Model identifier.")
    max_tokens: int = Field(default=512, gt=0, description="Max completion tokens.")


__all__ = ["ModelInferenceRequest"]
