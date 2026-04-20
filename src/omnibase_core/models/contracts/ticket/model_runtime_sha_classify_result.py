# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelRuntimeShaClassifyResult — result of classifying a runtime_sha_match receipt. OMN-9356"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelRuntimeShaClassifyResult(BaseModel):
    """Result of classifying a runtime_sha_match receipt."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    valid: bool = Field(..., description="True if the receipt structure is parseable")
    blocking: bool = Field(
        ..., description="True if this receipt blocks Done transition"
    )
    reason: str = Field(..., min_length=1, description="Human-readable explanation")


__all__ = ["ModelRuntimeShaClassifyResult"]
