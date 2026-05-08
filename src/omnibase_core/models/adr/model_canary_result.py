# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Canary run result aggregating per-model scores (OMN-10691)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.adr.model_extraction_score import ModelExtractionScore


class ModelCanaryResult(BaseModel):
    """Aggregated result from a canary extraction run over one ground-truth ADR."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    ground_truth_adr_path: str = Field(
        description="Path to the ground-truth ADR document"
    )
    source_doc_paths: list[str] = Field(
        default_factory=list, description="Source documents used as input"
    )
    model_scores: dict[str, ModelExtractionScore] = Field(
        default_factory=dict,
        description="Per-model extraction scores keyed by model_id",
    )
    best_model_id: str | None = Field(  # string-id-ok: LLM model name, not a UUID
        default=None, description="Model ID with the highest overall_score"
    )
    cost_summary: dict[str, object] = Field(
        default_factory=dict, description="Cost breakdown by model and total"
    )


__all__ = ["ModelCanaryResult"]
