from pydantic import Field

"""
State field model for state model specification.
"""

from typing import Any

from pydantic import BaseModel, Field


class ModelStateField(BaseModel):
    """Model for state model field specification."""

    name: str = Field(default=..., description="Field name")
    type: str = Field(default=..., description="Field type")
    required: bool = Field(default=..., description="Whether field is required")
    description: str = Field(default=..., description="Field description")
    default: Any | None = Field(default=None, description="Default value if optional")
