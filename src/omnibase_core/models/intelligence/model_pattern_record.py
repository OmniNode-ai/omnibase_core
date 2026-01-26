"""Pattern Record Model.

Represents an individual pattern discovered during extraction.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums import EnumPatternKind
from omnibase_core.types.type_json import JsonType


class ModelPatternRecord(BaseModel):
    """Individual pattern record from extraction.

    Represents a single discovered pattern with its classification,
    confidence score, and supporting evidence.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    pattern_id: UUID = Field(
        ...,
        description="Unique identifier for this pattern instance",
    )

    kind: EnumPatternKind = Field(
        ...,
        description="Category of this pattern",
    )

    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score for this pattern (0.0 to 1.0)",
    )

    occurrences: int = Field(
        ...,
        ge=1,
        description="Number of times this pattern was observed",
    )

    description: str = Field(
        ...,
        min_length=1,
        description="Human-readable description of the pattern",
    )

    evidence: list[str] = Field(
        default_factory=list,
        description="References to supporting data (e.g., session IDs, file paths)",
    )

    metadata: dict[str, JsonType] = Field(
        default_factory=dict,
        description="Additional pattern-specific metadata",
    )


__all__ = ["ModelPatternRecord"]
