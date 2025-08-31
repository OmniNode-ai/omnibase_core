"""
Pydantic model for LangExtract semantic insights.

This module defines the Model*SemanticInsight class used by the LangExtract
Intelligence Service for ONEX standards compliance.
"""

from pydantic import BaseModel, Field


class ModelLangextractSemanticInsight(BaseModel):
    """Model for semantic insights extracted by LangExtract."""

    entity_type: str = Field(
        ...,
        description="Type of semantic entity (e.g., module, function, class)",
    )
    entity_name: str = Field(..., description="Name of the semantic entity")
    purpose: str = Field(..., description="Detected purpose or role of the entity")
    complexity_score: int = Field(
        ...,
        ge=1,
        le=10,
        description="Complexity score from 1-10",
    )
    maintainability_score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Maintainability score from 0-100",
    )
