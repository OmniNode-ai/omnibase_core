# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelDocFreshnessSweepReport — full sweep report across all repositories."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.models.governance.model_doc_freshness_result import (
    ModelDocFreshnessResult,
)
from omnibase_core.models.governance.model_repo_doc_summary import ModelRepoDocSummary

_MAX_LIST_ITEMS = 10000

__all__ = ["ModelDocFreshnessSweepReport", "ModelRepoDocSummary"]


class ModelDocFreshnessSweepReport(BaseModel):
    """Full sweep report across all repositories."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    timestamp: datetime = Field(..., description="When the sweep was run")
    repos_scanned: list[str] = Field(
        default_factory=list, description="List of repository names scanned"
    )
    total_docs: int = Field(..., description="Total documents scanned", ge=0)
    fresh_count: int = Field(..., description="Documents with FRESH verdict", ge=0)
    stale_count: int = Field(..., description="Documents with STALE verdict", ge=0)
    broken_count: int = Field(..., description="Documents with BROKEN verdict", ge=0)
    unknown_count: int = Field(..., description="Documents with UNKNOWN verdict", ge=0)
    total_references: int = Field(..., description="Total references extracted", ge=0)
    broken_reference_count: int = Field(
        ..., description="Total broken references", ge=0
    )
    stale_reference_count: int = Field(..., description="Total stale references", ge=0)
    per_repo: dict[str, ModelRepoDocSummary] = Field(
        default_factory=dict, description="Per-repo summary"
    )
    results: list[ModelDocFreshnessResult] = Field(
        default_factory=list, description="Per-doc results", max_length=_MAX_LIST_ITEMS
    )
    top_stale_docs: list[str] = Field(
        default_factory=list,
        description="Top 10 docs by staleness score",
        max_length=10,
    )

    @model_validator(mode="after")
    def validate_aggregate_counts(self) -> "ModelDocFreshnessSweepReport":
        verdict_total = (
            self.fresh_count + self.stale_count + self.broken_count + self.unknown_count
        )
        if verdict_total != self.total_docs:
            msg = "fresh, stale, broken, and unknown counts must equal total_docs"
            raise ValueError(msg)

        reference_total = self.broken_reference_count + self.stale_reference_count
        if reference_total > self.total_references:
            msg = "broken and stale reference counts cannot exceed total_references"
            raise ValueError(msg)
        return self
