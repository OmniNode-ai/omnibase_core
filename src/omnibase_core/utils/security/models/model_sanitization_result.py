"""Sanitization result model for sensitive data filtering."""

from typing import List

from pydantic import BaseModel, ConfigDict, Field


class ModelSanitizationResult(BaseModel):
    """Result of sanitization operation."""

    model_config = ConfigDict()

    original_length: int = Field(..., description="Original text length")
    sanitized_length: int = Field(..., description="Sanitized text length")
    sensitive_patterns_found: List[str] = Field(
        default_factory=list, description="Types of sensitive patterns found"
    )
    replacements_made: int = Field(0, description="Number of replacements made")
    sanitized_text: str = Field(..., description="The sanitized text")
