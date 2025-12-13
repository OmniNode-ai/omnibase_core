"""
GitHub Label Model

Type-safe GitHub label that replaces Dict[str, Any] usage.
"""

from uuid import UUID

from pydantic import BaseModel, Field


class ModelGitHubLabel(BaseModel):
    """
    Type-safe GitHub label.

    Represents a GitHub issue/PR label with structured fields.
    """

    id: int = Field(default=..., description="Label ID")
    node_id: UUID = Field(default=..., description="Label node ID")
    url: str = Field(default=..., description="Label API URL")
    name: str = Field(default=..., description="Label name")
    color: str = Field(default=..., description="Label color (hex without #)")
    default: bool = Field(default=False, description="Whether this is a default label")
    description: str | None = Field(default=None, description="Label description")
