"""
Pydantic model for LangExtract intelligence extraction results.

This module defines the Model*IntelligenceResult class used by the LangExtract
Intelligence Service for ONEX standards compliance.
"""

from datetime import datetime
from typing import List

from pydantic import BaseModel, Field

from .model_langextract_pattern import ModelLangextractPattern
from .model_langextract_semantic_insight import ModelLangextractSemanticInsight


class ModelLangextractIntelligenceResult(BaseModel):
    """Model for intelligence extraction results from LangExtract service."""

    file_path: str = Field(..., description="Path to the analyzed file")
    patterns: List[ModelLangextractPattern] = Field(
        default_factory=list, description="Detected code patterns"
    )
    semantic_insights: List[ModelLangextractSemanticInsight] = Field(
        default_factory=list, description="Semantic analysis insights"
    )
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Overall confidence in the analysis"
    )
    execution_time_ms: float = Field(
        ..., description="Time taken for analysis in milliseconds"
    )
    timestamp: datetime = Field(
        ..., description="Timestamp when analysis was performed"
    )
