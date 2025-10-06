from typing import Dict

from pydantic import Field

"""
GitHub Label Model

Type-safe GitHub label that replaces Dict[str, Any] usage.
"""

from typing import Any, Dict

from pydantic import BaseModel, Field


class ModelGitHubLabel(BaseModel):
    """
    Type-safe GitHub label.

    Represents a GitHub issue/PR label with structured fields.
    """

    id: int = Field(..., description="Label ID")
    node_id: str = Field(..., description="Label node ID")
    url: str = Field(..., description="Label API URL")
    name: str = Field(..., description="Label name")
    color: str = Field(..., description="Label color (hex without #)")
    default: bool = Field(default=False, description="Whether this is a default label")
    description: str | None = Field(default=None, description="Label description")
