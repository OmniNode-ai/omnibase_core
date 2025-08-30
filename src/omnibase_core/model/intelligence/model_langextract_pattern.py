"""
Pydantic model for LangExtract intelligence patterns.

This module defines the Model*Pattern class used by the LangExtract
Intelligence Service for ONEX standards compliance.
"""

from typing import Optional

from pydantic import BaseModel, Field


class ModelLangextractPattern(BaseModel):
    """Model for code patterns detected by LangExtract."""

    pattern_name: str = Field(..., description="Name of the detected pattern")
    pattern_category: str = Field(
        ..., description="Category classification of the pattern"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score for pattern match"
    )
    description: str = Field(
        ..., description="Human-readable description of the pattern"
    )
