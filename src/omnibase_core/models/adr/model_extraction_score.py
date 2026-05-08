# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Extraction quality score for a single model run (OMN-10691)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelExtractionScore(BaseModel):
    """Quality scores for one model's ADR extraction attempt."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    # string-id-ok: LLM model name, not a UUID
    model_id: str = Field(description="LLM model identifier")
    recall: float = Field(
        ge=0.0, le=1.0, description="Fraction of ground-truth decisions found"
    )
    precision: float = Field(
        ge=0.0, le=1.0, description="Fraction of extractions that are correct"
    )
    fidelity: float = Field(ge=0.0, le=1.0, description="Faithfulness to source text")
    format_compliance: float = Field(
        ge=0.0, le=1.0, description="ADR format compliance score"
    )
    consensus_agreement: float = Field(
        ge=0.0, le=1.0, description="Agreement with other model outputs"
    )
    overall_score: float = Field(ge=0.0, le=1.0, description="Weighted composite score")
    success: bool = Field(
        description="Whether extraction completed without fatal error"
    )
    error_code: str | None = Field(
        default=None, description="Error code if not successful"
    )
    error_message: str | None = Field(
        default=None, description="Error message if not successful"
    )


__all__ = ["ModelExtractionScore"]
