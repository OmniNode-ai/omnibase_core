"""
ModelSecureMaskConfig: Configuration for secure credential masking.

This model represents the configuration for secure credential masking operations.
"""

from typing import Set

from pydantic import BaseModel, Field


class ModelSecureMaskConfig(BaseModel):
    """Configuration for secure credential masking."""

    mask_char: str = Field(
        "*", description="Character to use for masking", min_length=1, max_length=1
    )

    visible_chars: int = Field(
        2, description="Number of visible characters at start/end", ge=0, le=10
    )

    sensitive_patterns: Set[str] = Field(
        default_factory=set, description="Set of sensitive field patterns"
    )

    min_mask_length: int = Field(
        8, description="Minimum length of masked section", ge=1, le=20
    )

    recursive: bool = Field(
        True, description="Whether to recursively mask nested structures"
    )
