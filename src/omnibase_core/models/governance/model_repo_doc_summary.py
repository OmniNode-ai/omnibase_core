# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelRepoDocSummary — summary of doc freshness results for a single repository."""

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ModelRepoDocSummary(BaseModel):
    """Summary of doc freshness results for a single repository."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    repo: str = Field(..., description="Repository name")
    total_docs: int = Field(..., description="Total docs scanned", ge=0)
    fresh: int = Field(..., description="Count of fresh docs", ge=0)
    stale: int = Field(..., description="Count of stale docs", ge=0)
    broken: int = Field(..., description="Count of broken docs", ge=0)
    broken_references: int = Field(
        ..., description="Total broken references across docs", ge=0
    )

    @model_validator(mode="after")
    def validate_doc_counts(self) -> "ModelRepoDocSummary":
        counted_docs = self.fresh + self.stale + self.broken
        if counted_docs > self.total_docs:
            msg = "fresh, stale, and broken counts cannot exceed total_docs"
            raise ValueError(msg)
        return self
