"""
CLI introspection data model for ONEX CLI operations.

Author: ONEX Framework Team
"""

from pydantic import BaseModel, Field


class ModelCliIntrospectionData(BaseModel):
    """Strongly typed introspection data."""

    actions: list[str] = Field(default_factory=list)
    protocols: list[str] = Field(default_factory=list)
    metadata: dict[str, str] = Field(default_factory=dict)
