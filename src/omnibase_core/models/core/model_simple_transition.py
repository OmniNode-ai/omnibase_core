"""
Simple Transition Model.

Simple direct state field updates.
"""

from typing import Any

from pydantic import BaseModel, Field


class ModelSimpleTransition(BaseModel):
    """Simple direct state field updates."""

    updates: dict[str, Any] = Field(
        default=...,
        description="Field path to value mappings (e.g., {'user.name': 'John'})",
    )

    merge_strategy: str | None = Field(
        default="replace",
        description="How to handle existing values: 'replace', 'merge', 'append'",
    )
