from pydantic import Field

"""
State field model for state model specification.
"""

from typing import Any

from pydantic import BaseModel, Field


class ModelStateField(BaseModel):
    """Model for state model field specification."""

    name: str = Field(..., description="Field name")
    type: str = Field(..., description="Field type")
    required: bool = Field(..., description="Whether field is required")
    description: str = Field(..., description="Field description")
    default: Any | None = Field(None, description="Default value if optional")
