"""Model for learned/aggregated patterns.

Provides the primary data structure for patterns that have been extracted,
clustered, and promoted through the ONEX pattern learning pipeline.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.pattern_learning import (
    EnumPatternLifecycleState,
    EnumPatternType,
)

from .model_pattern_score_components import ModelPatternScoreComponents
from .model_pattern_signature import ModelPatternSignature


class ModelLearnedPattern(BaseModel):
    """Contract model for a learned/aggregated pattern.

    This is the primary data structure for patterns that have been
    extracted, clustered, and promoted through the learning pipeline.

    Lifecycle State:
        Injectors MUST check lifecycle_state before using patterns.
        Only VALIDATED patterns should be used in production.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    # Identity
    pattern_id: UUID = Field(description="Unique identifier for this pattern")
    pattern_name: str = Field(description="Human-readable name")
    pattern_type: EnumPatternType = Field(
        description="Type classification for the pattern domain"
    )

    # Classification
    category: str = Field(description="Primary category")
    subcategory: str = Field(description="Secondary category for finer classification")
    tags: tuple[str, ...] = Field(description="Searchable tags")
    keywords: tuple[str, ...] = Field(description="Extracted keywords")

    # Decomposed scoring - NEVER make decisions on confidence alone
    score_components: ModelPatternScoreComponents = Field(
        description="Decomposed scoring components - always inspect these, not just confidence",
    )
    signature_info: ModelPatternSignature = Field(
        description="Versioned signature metadata for deduplication",
    )

    # Lifecycle gating - injectors MUST check this
    lifecycle_state: EnumPatternLifecycleState = Field(
        description="Lifecycle state - injectors MUST check this before use. Only VALIDATED patterns are safe for production.",
    )

    # Metadata
    source_count: int = Field(
        ge=1, description="Number of sources that contributed to this pattern"
    )
    first_seen: datetime = Field(description="First observation timestamp (UTC)")
    last_seen: datetime = Field(description="Most recent observation timestamp (UTC)")


__all__ = ["ModelLearnedPattern"]
