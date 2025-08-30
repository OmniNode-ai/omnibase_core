"""
Dependencies model for node introspection.
"""

from typing import List

from pydantic import BaseModel, Field


class ModelDependencies(BaseModel):
    """Model for node dependencies specification."""

    runtime: List[str] = Field(
        default_factory=list, description="Required runtime dependencies"
    )
    optional: List[str] = Field(
        default_factory=list, description="Optional dependencies"
    )
    python_version: str = Field(..., description="Required Python version")
    external_tools: List[str] = Field(
        default_factory=list, description="Required external tools"
    )
