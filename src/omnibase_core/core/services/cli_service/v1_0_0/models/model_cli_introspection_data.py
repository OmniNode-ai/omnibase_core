"""
CLI introspection data model for ONEX CLI operations.

Author: ONEX Framework Team
"""

from typing import List

from pydantic import BaseModel, Field


class ModelCliIntrospectionData(BaseModel):
    """Strongly typed introspection data."""

    actions: List[str] = Field(default_factory=list)
    protocols: List[str] = Field(default_factory=list)
    metadata: dict[str, str] = Field(default_factory=dict)
