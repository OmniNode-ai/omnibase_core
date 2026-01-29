"""Stored intent classification record model.

Represents a persisted intent classification for querying and analysis.
Part of the intent storage subsystem (OMN-1645).
"""

from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.intelligence.enum_intent_category import EnumIntentCategory

__all__ = ["ModelIntentRecord"]


class ModelIntentRecord(BaseModel):
    """A stored intent classification record.

    Represents a persisted intent classification with all metadata needed
    for querying, analysis, and correlation tracking.

    Attributes:
        intent_id: Unique identifier for this intent record.
        session_id: Session in which the intent was classified.
        intent_category: The classified intent category.
        confidence: Classification confidence score (0.0 to 1.0).
        keywords: Keywords extracted from the classification.
        created_at: When this record was created (UTC).
        correlation_id: Optional correlation ID for request tracing.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        from_attributes=True,
    )

    intent_id: UUID = Field(
        description="Unique identifier for this intent record",
    )
    # string-id-ok: External session ID (Claude Code, CLI, etc.), not ONEX-internal UUID
    session_id: str = Field(
        description="Session in which the intent was classified",
    )
    intent_category: EnumIntentCategory = Field(
        description="The classified intent category",
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Classification confidence score (0.0 to 1.0)",
    )
    keywords: list[str] = Field(
        default_factory=list,
        description="Keywords extracted from the classification",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When this record was created (UTC)",
    )
    correlation_id: UUID | None = Field(
        default=None,
        description="Optional correlation ID for request tracing",
    )
