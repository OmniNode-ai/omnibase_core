#!/usr/bin/env python3
"""
ModelCrossSessionPersistenceData - Data structure for cross-session persistence.

This model represents data structures for cross-session persistence
in the ONEX platform's workflow 6 system integration.
"""

from pydantic import BaseModel, Field

# Type aliases for strong typing
IntelligenceData = dict[
    str,
    str | int | float | bool | list[str] | dict[str, str | int | float],
]


class ModelCrossSessionPersistenceData(BaseModel):
    """Data structure for cross-session persistence."""

    session_id: str = Field(..., description="Source session identifier")
    learning_data: IntelligenceData = Field(..., description="Learning data to persist")
    context_patterns: list[str] = Field(
        default_factory=list,
        description="Context patterns identified",
    )
    correlation_mappings: dict[str, str] = Field(
        default_factory=dict,
        description="Cross-session correlations",
    )
    retention_priority: str = Field(
        default="medium",
        description="Data retention priority",
    )
