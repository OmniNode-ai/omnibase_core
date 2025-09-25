"""
Example metadata model for examples collection.

This module provides the ModelExampleMetadata class for metadata
about example collections with enhanced structure.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_difficulty_level import EnumDifficultyLevel
from omnibase_core.enums.enum_example_category import EnumExampleCategory


class ModelExampleMetadata(BaseModel):
    """
    Metadata for example collections with enhanced structure.
    """

    title: str = Field(
        default="",
        description="Title for the examples collection",
    )

    description: str | None = Field(
        None,
        description="Description of the examples collection",
    )

    tags: list[str] = Field(
        default_factory=list,
        description="Tags for the entire collection",
    )

    difficulty: EnumDifficultyLevel = Field(
        default=EnumDifficultyLevel.BEGINNER,
        description="Difficulty level for the examples collection",
    )

    category: EnumExampleCategory | None = Field(
        None,
        description="Category this collection belongs to",
    )
