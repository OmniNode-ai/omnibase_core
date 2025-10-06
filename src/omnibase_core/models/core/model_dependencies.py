from typing import Any, Optional

from pydantic import Field

"""
Dependencies model for node introspection.
"""

from pydantic import BaseModel, Field


class ModelDependencies(BaseModel):
    """Model for node dependencies specification."""

    runtime: list[str] = Field(
        default_factory=list,
        description="Required runtime dependencies",
    )
    optional: list[str] = Field(
        default_factory=list,
        description="Optional dependencies",
    )
    python_version: str = Field(default=..., description="Required Python version")
    external_tools: list[str] = Field(
        default_factory=list,
        description="Required external tools",
    )
