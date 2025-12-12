"""
Simple Transition Model.

Simple direct state field updates.
"""

from pydantic import BaseModel, Field

from omnibase_core.types.type_serializable_value import SerializedDict


class ModelSimpleTransition(BaseModel):
    """Simple direct state field updates."""

    # Uses SerializedDict for state field updates (JSON-serializable values)
    updates: SerializedDict = Field(
        default=...,
        description="Field path to value mappings (e.g., {'user.name': 'John'})",
    )

    merge_strategy: str | None = Field(
        default="replace",
        description="How to handle existing values: 'replace', 'merge', 'append'",
    )
