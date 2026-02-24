# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""RAG query configuration model for agent YAML schema validation."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ModelRagQueries(BaseModel):
    """RAG (Retrieval-Augmented Generation) query configuration.

    Specifies RAG query patterns used by the agent for intelligence retrieval,
    including domain and implementation queries with optional retrieval tuning.

    Fields:
        domain_query: Natural-language query for domain-level context retrieval
        implementation_query: Natural-language query for implementation patterns
        context_preference: Preferred context source (e.g. "debugging", "general")
        match_count: Number of results to retrieve; must be between 1 and 20
        confidence_threshold: Minimum confidence score (0.0–1.0) to accept results

    Example (from velocity-tracker.yaml)::

        rag_queries:
          domain_query: "engineering productivity metrics velocity tracking"
          implementation_query: "velocity tracking implementation patterns"
          context_preference: "debugging"
          match_count: 5
          confidence_threshold: 0.6
    """

    model_config = ConfigDict(frozen=True, extra="ignore", from_attributes=True)

    domain_query: str | None = None
    implementation_query: str | None = None
    context_preference: str | None = None
    match_count: int | None = Field(
        default=None,
        description="Number of results to retrieve (1–20)",
    )
    confidence_threshold: float | None = Field(
        default=None,
        description="Minimum confidence score to accept results (0.0–1.0)",
    )

    @field_validator("match_count")
    @classmethod
    def validate_match_count(cls, v: int | None) -> int | None:
        """Validate match_count is between 1 and 20 inclusive."""
        if v is not None and not (1 <= v <= 20):
            raise ValueError(f"match_count must be between 1 and 20, got {v}")
        return v

    @field_validator("confidence_threshold")
    @classmethod
    def validate_confidence_threshold(cls, v: float | None) -> float | None:
        """Validate confidence_threshold is between 0.0 and 1.0 inclusive."""
        if v is not None and not (0.0 <= v <= 1.0):
            raise ValueError(
                f"confidence_threshold must be between 0.0 and 1.0, got {v}"
            )
        return v


__all__ = ["ModelRagQueries"]
